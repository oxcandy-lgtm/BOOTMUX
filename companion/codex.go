package main

import (
	"context"
	"errors"
	"io"
	"os/exec"
	"strings"
	"syscall"
)

var errCodexOutputOverflow = errors.New("codex_output_overflow")

type codexOutputWriter struct {
	s         *session
	requestID string
	total     int
}

func (w *codexOutputWriter) Write(data []byte) (int, error) {
	if len(data) == 0 {
		return 0, nil
	}
	if w.total+len(data) > defaultCodexOutput {
		return 0, errCodexOutputOverflow
	}
	w.total += len(data)
	text := strings.ToValidUTF8(string(data), "�")
	if !w.s.enqueue(serverMessage{
		Version:   protocolVersion,
		Type:      "codex_output",
		SessionID: w.s.id,
		RequestID: w.requestID,
		Text:      text,
	}) {
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
	writer := &codexOutputWriter{s: s, requestID: requestID}
	cmd.Stdout = writer
	cmd.Stderr = writer
	s.codexCancel = cancel
	s.codexCmd = cmd
	s.codexActive = true
	s.codexMu.Unlock()

	if err := cmd.Start(); err != nil {
		cancel()
		s.codexMu.Lock()
		s.codexActive = false
		s.codexCancel = nil
		s.codexCmd = nil
		s.codexMu.Unlock()
		_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_error", SessionID: s.id, RequestID: requestID, Code: "codex_start_failed", Message: "Codex executable unavailable"})
		return true
	}
	_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_started", SessionID: s.id, RequestID: requestID})
	go func() {
		<-ctx.Done()
		if cmd.Process != nil {
			_ = syscall.Kill(-cmd.Process.Pid, syscall.SIGTERM)
		}
	}()
	go s.waitCodex(ctx, cancel, cmd, writer, requestID)
	return true
}


func (s *session) waitCodex(ctx context.Context, cancel context.CancelFunc, cmd *exec.Cmd, writer *codexOutputWriter, requestID string) {
	defer cancel()
	err := cmd.Wait()
	s.codexMu.Lock()
	s.codexActive = false
	s.codexCancel = nil
	s.codexCmd = nil
	s.codexMu.Unlock()

	if ctx.Err() == context.DeadlineExceeded {
		_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_error", SessionID: s.id, RequestID: requestID, Code: "codex_timeout", Message: "Codex execution timed out"})
		return
	}
	if ctx.Err() == context.Canceled {
		return
	}
	if errors.Is(err, errCodexOutputOverflow) {
		_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_error", SessionID: s.id, RequestID: requestID, Code: "codex_output_overflow", Message: "Codex output limit exceeded"})
		return
	}
	if err != nil {
		_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_error", SessionID: s.id, RequestID: requestID, Code: "codex_failed", Message: "Codex execution failed"})
		return
	}
	code := exitCode(cmd)
	_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_exit", SessionID: s.id, RequestID: requestID, ExitCode: &code})
}

func (s *session) cancelCodex(requestID string) {
	s.codexMu.Lock()
	cancel := s.codexCancel
	cmd := s.codexCmd
	s.codexMu.Unlock()
	if cancel == nil {
		return
	}
	cancel()
	if cmd != nil && cmd.Process != nil {
		_ = syscall.Kill(-cmd.Process.Pid, syscall.SIGTERM)
	}
	if requestID != "" {
		_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "codex_error", SessionID: s.id, RequestID: requestID, Code: "codex_cancelled", Message: "Codex execution cancelled"})
	}
}
