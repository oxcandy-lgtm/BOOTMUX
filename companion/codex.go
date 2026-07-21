package main

import (
	"context"
	"errors"
	"io"
	"os/exec"
	"strings"
	"sync"
	"syscall"
	"time"
)

var errCodexOutputOverflow = errors.New("codex_output_overflow")

type codexRun struct {
	s         *session
	requestID string
	cmd       *exec.Cmd
	cancel    context.CancelFunc

	watcherDone chan struct{}
	watcherStop chan struct{}
	killDone    chan struct{}
	stopOnce    sync.Once
	reasonMu    sync.Mutex
	reason      string
	terminal    sync.Once
}

func (r *codexRun) setReason(reason string) {
	r.reasonMu.Lock()
	if r.reason == "" {
		r.reason = reason
	}
	r.reasonMu.Unlock()
}

func (r *codexRun) stop(reason string) {
	if reason != "" {
		r.setReason(reason)
	}
	r.stopOnce.Do(func() {
		r.cancel()
		if r.cmd.Process != nil {
			pid := r.cmd.Process.Pid
			_ = syscall.Kill(-pid, syscall.SIGTERM)
			go func() {
				defer close(r.killDone)
				timer := time.NewTimer(250 * time.Millisecond)
				defer timer.Stop()
				<-timer.C
				_ = syscall.Kill(-pid, syscall.SIGKILL)
				_ = r.cmd.Process.Kill()
			}()
			return
		}
		close(r.killDone)
	})
}

func (r *codexRun) stopReason(ctx context.Context) string {
	r.reasonMu.Lock()
	reason := r.reason
	r.reasonMu.Unlock()
	if reason != "" {
		return reason
	}
	if ctx.Err() == context.DeadlineExceeded {
		return "timeout"
	}
	if ctx.Err() != nil {
		return "cancelled"
	}
	return ""
}

type codexOutputWriter struct {
	run   *codexRun
	total int
}

func (w *codexOutputWriter) Write(data []byte) (int, error) {
	if len(data) == 0 {
		return 0, nil
	}
	if w.total+len(data) > defaultCodexOutput {
		w.run.stop("overflow")
		return 0, errCodexOutputOverflow
	}
	w.total += len(data)
	text := strings.ToValidUTF8(string(data), "�")
	if !w.run.s.enqueue(serverMessage{
		Version:   protocolVersion,
		Type:      "codex_output",
		SessionID: w.run.s.id,
		RequestID: w.run.requestID,
		Text:      text,
	}) {
		w.run.stop("session")
		return 0, io.ErrClosedPipe
	}
	return len(data), nil
}

func (s *session) startCodex(prompt, requestID string) bool {
	s.codexMu.Lock()
	if s.codexActive {
		s.codexMu.Unlock()
		return false
	}
	ctx, cancel := context.WithTimeout(context.Background(), defaultCodexTimeout)
	cmd := exec.CommandContext(ctx, s.codex, "exec", prompt)
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	run := &codexRun{
		s:           s,
		requestID:   requestID,
		cmd:         cmd,
		cancel:      cancel,
		watcherDone: make(chan struct{}),
		watcherStop: make(chan struct{}),
		killDone:    make(chan struct{}),
	}
	writer := &codexOutputWriter{run: run}
	cmd.Stdout = writer
	cmd.Stderr = writer
	s.codexCancel = cancel
	s.codexCmd = cmd
	s.codexActive = true
	s.codexRun = run
	s.codexMu.Unlock()

	if err := cmd.Start(); err != nil {
		cancel()
		s.clearCodexRun(run)
		_ = s.enqueueCodexError(requestID, "codex_start_failed", "Codex executable unavailable")
		return true
	}
	_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_started", SessionID: s.id, RequestID: requestID})
	go func() {
		defer close(run.watcherDone)
		select {
		case <-run.watcherStop:
			return
		case <-ctx.Done():
			reason := "cancelled"
			if ctx.Err() == context.DeadlineExceeded {
				reason = "timeout"
			}
			run.stop(reason)
		}
	}()
	go s.waitCodex(ctx, run)
	return true
}

func (s *session) waitCodex(ctx context.Context, run *codexRun) {
	err := run.cmd.Wait()
	if ctx.Err() == context.DeadlineExceeded {
		run.setReason("timeout")
	} else {
		run.setReason("success")
	}
	close(run.watcherStop)
	run.cancel()
	<-run.watcherDone
	if run.stopReason(ctx) != "success" {
		<-run.killDone
	}
	s.clearCodexRun(run)

	run.terminal.Do(func() {
		switch run.stopReason(ctx) {
		case "session", "new_session":
			return
		case "overflow":
			_ = s.enqueueCodexError(run.requestID, "codex_output_overflow", "Codex output limit exceeded")
		case "timeout":
			_ = s.enqueueCodexError(run.requestID, "codex_timeout", "Codex execution timed out")
		case "cancelled":
			_ = s.enqueueCodexError(run.requestID, "codex_cancelled", "Codex execution cancelled")
		default:
			if err != nil {
				if errors.Is(err, errCodexOutputOverflow) {
					_ = s.enqueueCodexError(run.requestID, "codex_output_overflow", "Codex output limit exceeded")
				} else {
					_ = s.enqueueCodexError(run.requestID, "codex_failed", "Codex execution failed")
				}
				return
			}
			code := exitCode(run.cmd)
			_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_exit", SessionID: s.id, RequestID: run.requestID, ExitCode: &code})
		}
	})
}

func (s *session) clearCodexRun(run *codexRun) {
	s.codexMu.Lock()
	if s.codexRun == run {
		s.codexActive = false
		s.codexCancel = nil
		s.codexCmd = nil
		s.codexRun = nil
	}
	s.codexMu.Unlock()
}

func (s *session) cancelCodex(requestID string) {
	s.codexMu.Lock()
	run := s.codexRun
	s.codexMu.Unlock()
	if run == nil {
		return
	}
	if requestID == "" {
		run.stop("session")
		return
	}
	run.stop("cancelled")
}

func (s *session) enqueueCodexError(requestID, code, message string) bool {
	return s.enqueue(serverMessage{
		Version:   protocolVersion,
		Type:      "codex_error",
		SessionID: s.id,
		RequestID: requestID,
		Code:      code,
		Message:   message,
	})
}
