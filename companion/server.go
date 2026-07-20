package main

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"sync"
	"syscall"
	"time"

	"github.com/creack/pty"
	"github.com/gorilla/websocket"
)

const (
	defaultFlushInterval = 35 * time.Millisecond
	defaultBatchBytes    = 512
	maxBufferedBytes     = 4096
	writeTimeout         = 2 * time.Second
)

type Server struct {
	Shell          string
	ShellArgs      []string
	FlushInterval  time.Duration
	BatchBytes     int
	MaxBufferBytes int
	Upgrader       websocket.Upgrader
}

func NewServer(shell string, args ...string) *Server {
	return &Server{Shell: shell, ShellArgs: args, FlushInterval: defaultFlushInterval, BatchBytes: defaultBatchBytes, MaxBufferBytes: maxBufferedBytes, Upgrader: websocket.Upgrader{CheckOrigin: func(*http.Request) bool { return true }}}
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/v1/terminal", s.handleTerminal)
	return mux
}

func newSessionID() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

func (s *Server) handleTerminal(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/v1/terminal" {
		http.NotFound(w, r)
		return
	}
	conn, err := s.Upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	id, err := newSessionID()
	if err != nil {
		sessionError(conn, "session_creation_failed", "session unavailable")
		return
	}
	cmd := exec.Command(s.Shell, s.ShellArgs...)
	ptmx, err := pty.Start(cmd)
	if err != nil {
		sessionError(conn, "pty_start_failed", "shell unavailable")
		return
	}
	sess := &session{conn: conn, id: id, ptmx: ptmx, cmd: cmd, flush: s.FlushInterval, batch: s.BatchBytes, max: s.MaxBufferBytes}
	sess.run()
}

type session struct {
	conn       *websocket.Conn
	id         string
	ptmx       io.ReadWriteCloser
	cmd        *exec.Cmd
	flush      time.Duration
	batch, max int
	mu         sync.Mutex
	writing    bool
	closed     bool
}

func (s *session) run() {
	defer s.cleanup()
	if !s.send(serverMessage{Version: protocolVersion, Type: "hello", SessionID: s.id}) {
		return
	}
	done := make(chan struct{})
	go func() { s.readPTY(done) }()
	for {
		_, data, err := s.conn.ReadMessage()
		if err != nil {
			return
		}
		msg, err := decodeClientMessage(data)
		if err != nil {
			if !s.sendError(err.Error(), "request rejected") {
				return
			}
			continue
		}
		if msg.SessionID != s.id {
			if !s.sendError("wrong_session", "session rejected") {
				return
			}
			continue
		}
		switch msg.Type {
		case "input_text":
			if _, err = s.ptmx.Write([]byte(msg.Text)); err != nil {
				return
			}
		case "control":
			if err = s.interrupt(); err != nil {
				if !s.sendError("interrupt_failed", "interrupt unavailable") {
					return
				}
			}
		case "close":
			return
		}
		select {
		case <-done:
			return
		default:
		}
	}
}

func (s *session) readPTY(done chan<- struct{}) {
	defer close(done)
	buf := make([]byte, 1024)
	pending := make([]byte, 0, s.max)
	timer := time.NewTimer(s.flush)
	if !timer.Stop() {
		<-timer.C
	}
	defer timer.Stop()
	flush := func() bool {
		if len(pending) == 0 {
			return true
		}
		text := string(pending)
		pending = pending[:0]
		return s.send(serverMessage{Version: protocolVersion, Type: "output", SessionID: s.id, Stream: "pty", Text: text})
	}
	for {
		n, err := s.ptmx.Read(buf)
		if n > 0 {
			pending = append(pending, buf[:n]...)
			if len(pending) > s.max {
				pending = pending[len(pending)-s.max:]
			}
			if containsNewline(pending) || len(pending) >= s.batch {
				if !flush() {
					return
				}
				timer.Stop()
			}
			if len(pending) > 0 && !timer.Stop() {
				select {
				case <-timer.C:
				default:
				}
			}
			if len(pending) > 0 {
				timer.Reset(s.flush)
			}
		}
		if err != nil {
			if !errors.Is(err, io.EOF) && !errors.Is(err, syscall.EIO) {
				_ = s.sendError("pty_read_failed", "terminal unavailable")
			}
			_ = flush()
			_ = s.cmd.Wait()
			code := exitCode(s.cmd)
			_ = s.send(serverMessage{Version: protocolVersion, Type: "exit", SessionID: s.id, ExitCode: &code})
			return
		}
		select {
		case <-timer.C:
			if !flush() {
				return
			}
		default:
		}
	}
}

func containsNewline(b []byte) bool {
	for _, c := range b {
		if c == '\n' {
			return true
		}
	}
	return false
}

func exitCode(cmd *exec.Cmd) int {
	if cmd.ProcessState == nil {
		return -1
	}
	if status, ok := cmd.ProcessState.Sys().(syscall.WaitStatus); ok {
		return status.ExitStatus()
	}
	return -1
}

func (s *session) interrupt() error {
	if s.cmd.Process == nil {
		return fmt.Errorf("no process")
	}
	return s.cmd.Process.Signal(osInterrupt)
}

var osInterrupt = syscall.Signal(syscall.SIGINT)

func (s *session) send(msg serverMessage) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return false
	}
	_ = s.conn.SetWriteDeadline(time.Now().Add(writeTimeout))
	return s.conn.WriteJSON(msg) == nil
}

func (s *session) sendError(code, message string) bool {
	return s.send(serverMessage{Version: protocolVersion, Type: "error", SessionID: s.id, Code: code, Message: message})
}

func sessionError(conn *websocket.Conn, code, message string) {
	_ = conn.SetWriteDeadline(time.Now().Add(writeTimeout))
	_ = conn.WriteJSON(serverMessage{Version: protocolVersion, Type: "error", Code: code, Message: message})
}

func (s *session) cleanup() {
	s.mu.Lock()
	s.closed = true
	s.mu.Unlock()
	_ = s.ptmx.Close()
	if s.cmd.Process != nil {
		_ = s.cmd.Process.Kill()
	}
}
