package main

import (
	"crypto/rand"
	"encoding/hex"
	"io"
	"net/http"
	"net/url"
	"os/exec"
	"strings"
	"sync"
	"syscall"
	"time"
	"unicode/utf8"

	"github.com/creack/pty"
	"github.com/gorilla/websocket"
)

const (
	defaultFlushInterval = 35 * time.Millisecond
	defaultBatchBytes    = 512
	defaultMaxBuffer     = 4096
	defaultChunkBytes    = 256
	defaultChunkQueue    = 8
	defaultOutboundQueue = 8
	maxWebSocketMessage  = 16 * 1024
	maxJSONMessage       = 12 * 1024
	maxInputTextBytes    = 8 * 1024
	writeTimeout         = 2 * time.Second
)

type Server struct {
	Shell                   string
	ShellArgs               []string
	FlushInterval           time.Duration
	BatchBytes              int
	MaxBufferBytes          int
	ChunkBytes              int
	ChunkQueueCapacity      int
	OutboundQueueCapacity   int
	MaxWebSocketMessageSize int64
	MaxJSONMessageBytes     int
	MaxInputTextBytes       int
	Upgrader                websocket.Upgrader
}

func NewServer(shell string, args ...string) *Server {
	s := &Server{
		Shell:                   shell,
		ShellArgs:               args,
		FlushInterval:           defaultFlushInterval,
		BatchBytes:              defaultBatchBytes,
		MaxBufferBytes:          defaultMaxBuffer,
		ChunkBytes:              defaultChunkBytes,
		ChunkQueueCapacity:      defaultChunkQueue,
		OutboundQueueCapacity:   defaultOutboundQueue,
		MaxWebSocketMessageSize: maxWebSocketMessage,
		MaxJSONMessageBytes:     maxJSONMessage,
		MaxInputTextBytes:       maxInputTextBytes,
	}
	s.Upgrader.CheckOrigin = sameHostOrNativeOrigin
	return s
}

func sameHostOrNativeOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	u, err := url.Parse(origin)
	return err == nil && u.Host == r.Host
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
	conn.SetReadLimit(s.MaxWebSocketMessageSize)

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
	sess := newSession(s, conn, id, ptmx, cmd)
	sess.run()
}

type ptyChunk struct {
	data []byte
}

type processResult struct {
	exitCode int
}

type clientEvent struct {
	data []byte
	err  error
}

type session struct {
	conn       *websocket.Conn
	id         string
	ptmx       io.ReadWriteCloser
	cmd        *exec.Cmd
	flush      time.Duration
	batch      int
	max        int
	chunkBytes int
	maxJSON    int
	maxInput   int

	chunks     chan ptyChunk
	process    chan processResult
	client     chan clientEvent
	outbound   chan serverMessage
	finished   chan struct{}
	writerDone chan struct{}
	overflow   chan struct{}
	cancel     chan struct{}

	stopOnce     sync.Once
	overflowOnce sync.Once
	finishOnce   sync.Once
	mu           sync.Mutex
	closed       bool
}

func newSession(s *Server, conn *websocket.Conn, id string, ptmx io.ReadWriteCloser, cmd *exec.Cmd) *session {
	return &session{
		conn:       conn,
		id:         id,
		ptmx:       ptmx,
		cmd:        cmd,
		flush:      s.FlushInterval,
		batch:      s.BatchBytes,
		max:        s.MaxBufferBytes,
		chunkBytes: s.ChunkBytes,
		maxJSON:    s.MaxJSONMessageBytes,
		maxInput:   s.MaxInputTextBytes,
		chunks:     make(chan ptyChunk, s.ChunkQueueCapacity),
		process:    make(chan processResult, 1),
		client:     make(chan clientEvent, 1),
		outbound:   make(chan serverMessage, s.OutboundQueueCapacity),
		finished:   make(chan struct{}),
		writerDone: make(chan struct{}),
		overflow:   make(chan struct{}),
		cancel:     make(chan struct{}),
	}
}

func (s *session) run() {
	go s.writeMessages()
	go s.readClient()
	go s.readPTY()
	go s.waitProcess()
	if !s.enqueue(serverMessage{Version: protocolVersion, Type: "hello", SessionID: s.id}) {
		s.stop()
	}

	go s.aggregate()
	for {
		select {
		case event := <-s.client:
			if event.err != nil {
				s.stop()
				goto wait
			}
			if s.handleClientMessage(event.data) {
				goto wait
			}
		case <-s.finished:
			goto wait
		}
	}

wait:
	s.stop()
	<-s.finished
	<-s.writerDone
}

func (s *session) readClient() {
	for {
		_, data, err := s.conn.ReadMessage()
		select {
		case s.client <- clientEvent{data: data, err: err}:
		case <-s.cancel:
			return
		}
		if err != nil {
			return
		}
	}
}

func (s *session) handleClientMessage(data []byte) bool {
	if len(data) > s.maxJSONBytes() {
		return !s.enqueueError("json_too_large", "request exceeds JSON message limit")
	}
	msg, err := decodeClientMessage(data)
	if err != nil {
		return !s.enqueueError(err.Error(), "request rejected")
	}
	if len(msg.Text) > s.maxInputBytes() {
		return !s.enqueueError("input_too_large", "input text exceeds limit")
	}
	if msg.SessionID != s.id {
		return !s.enqueueError("wrong_session", "session rejected")
	}
	switch msg.Type {
	case "input_text":
		_, err = s.ptmx.Write([]byte(msg.Text))
	case "control":
		err = s.interrupt()
	case "close":
		return true
	}
	if err != nil {
		return !s.enqueueError("input_failed", "terminal input unavailable")
	}
	return false
}

func (s *session) maxJSONBytes() int {
	if s.maxJSON != 0 {
		return s.maxJSON
	}
	return maxJSONMessage
}

func (s *session) maxInputBytes() int {
	if s.maxInput != 0 {
		return s.maxInput
	}
	return maxInputTextBytes
}

func (s *session) readPTY() {
	buf := make([]byte, s.chunkBytes)
	for {
		n, err := s.ptmx.Read(buf)
		if n > 0 {
			chunk := append([]byte(nil), buf[:n]...)
			select {
			case s.chunks <- ptyChunk{data: chunk}:
			case <-s.cancel:
				return
			default:
				signalOverflow(s.overflow, &s.overflowOnce)
				return
			}
		}
		if err != nil {
			return
		}
	}
}

func (s *session) waitProcess() {
	err := s.cmd.Wait()
	code := -1
	if err == nil || s.cmd.ProcessState != nil {
		code = exitCode(s.cmd)
	}
	select {
	case s.process <- processResult{exitCode: code}:
	case <-s.cancel:
	}
}

func (s *session) aggregate() {
	timer := time.NewTimer(s.flush)
	defer timer.Stop()
	pending := make([]byte, 0, s.max)
	flush := func(final bool) bool {
		text, rest := utf8Prefix(pending, final)
		pending = rest
		if text == "" {
			return true
		}
		return s.enqueue(serverMessage{Version: protocolVersion, Type: "output", SessionID: s.id, Stream: "pty", Text: text})
	}
	resetTimer := func() {
		if !timer.Stop() {
			select {
			case <-timer.C:
			default:
			}
		}
		timer.Reset(s.flush)
	}
	finish := func(code int, sendExit bool) {
		if sendExit {
			_ = flush(true)
			_ = s.enqueue(serverMessage{Version: protocolVersion, Type: "exit", SessionID: s.id, ExitCode: &code})
		}
		close(s.outbound)
		<-s.writerDone
		s.finishOnce.Do(func() { close(s.finished) })
	}
	for {
		select {
		case <-s.overflow:
			_ = s.enqueueError("output_overflow", "terminal output limit exceeded")
			finish(-1, false)
			return
		case result := <-s.process:
			for {
				select {
				case chunk := <-s.chunks:
					pending = append(pending, chunk.data...)
				default:
					goto drained
				}
			}
		drained:
			if len(pending) > s.max {
				_ = s.enqueueError("output_overflow", "terminal output limit exceeded")
				finish(result.exitCode, false)
				return
			}
			finish(result.exitCode, true)
			return
		case chunk := <-s.chunks:
			pending = append(pending, chunk.data...)
			if len(pending) > s.max {
				_ = s.enqueueError("output_overflow", "terminal output limit exceeded")
				finish(-1, false)
				return
			}
			if containsNewline(pending) || len(pending) >= s.batch {
				if !flush(false) {
					finish(-1, false)
					return
				}
				resetTimer()
			} else {
				resetTimer()
			}
		case <-timer.C:
			if !flush(false) {
				finish(-1, false)
				return
			}
			resetTimer()
		case <-s.cancel:
			finish(-1, false)
			return
		}
	}
}

func utf8Prefix(data []byte, final bool) (string, []byte) {
	if len(data) == 0 {
		return "", nil
	}
	valid := 0
	for valid < len(data) {
		r, size := utf8.DecodeRune(data[valid:])
		if r == utf8.RuneError && size == 1 {
			if !final && !utf8.FullRune(data[valid:]) {
				break
			}
			valid++
			continue
		}
		valid += size
	}
	if valid == 0 {
		return "", data
	}
	return strings.ToValidUTF8(string(data[:valid]), "�"), data[valid:]
}

func containsNewline(b []byte) bool { return strings.ContainsRune(string(b), '\n') }

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
	_, err := s.ptmx.Write([]byte{3})
	return err
}

func signalOverflow(ch chan struct{}, once *sync.Once) { once.Do(func() { close(ch) }) }

func (s *session) enqueue(msg serverMessage) bool {
	select {
	case s.outbound <- msg:
		return true
	default:
		return false
	}
}

func (s *session) enqueueError(code, message string) bool {
	return s.enqueue(serverMessage{Version: protocolVersion, Type: "error", SessionID: s.id, Code: code, Message: message})
}

func (s *session) writeMessages() {
	defer close(s.writerDone)
	for msg := range s.outbound {
		if !s.write(msg) {
			s.stop()
			return
		}
	}
}

func (s *session) write(msg serverMessage) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return false
	}
	_ = s.conn.SetWriteDeadline(time.Now().Add(writeTimeout))
	return s.conn.WriteJSON(msg) == nil
}

func (s *session) stop() {
	s.stopOnce.Do(func() {
		close(s.cancel)
		_ = s.ptmx.Close()
		if s.cmd.Process != nil {
			_ = s.cmd.Process.Kill()
		}
		_ = s.conn.Close()
		s.mu.Lock()
		s.closed = true
		s.mu.Unlock()
	})
}

func sessionError(conn *websocket.Conn, code, message string) {
	_ = conn.SetWriteDeadline(time.Now().Add(writeTimeout))
	_ = conn.WriteJSON(serverMessage{Version: protocolVersion, Type: "error", Code: code, Message: message})
}
