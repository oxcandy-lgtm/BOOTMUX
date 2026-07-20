package main

import (
	"context"
	"crypto/rand"
	_ "embed"
	"encoding/hex"
	"errors"
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

//go:embed judge/index.html
var judgeHTML []byte

const (
	defaultFlushInterval = 35 * time.Millisecond
	defaultBatchBytes    = 512
	defaultMaxBuffer     = 4096
	defaultChunkBytes    = 256
	defaultChunkQueue    = 8
	defaultOutboundQueue = 8
	defaultInputQueue    = 8
	defaultCodexOutput   = 128 * 1024
	defaultCodexPrompt   = 8 * 1024
	defaultCodexTimeout  = 180 * time.Second
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
	InputQueueCapacity      int
	CodexExecutable         string
	MaxWebSocketMessageSize int64
	MaxJSONMessageBytes     int
	MaxInputTextBytes       int
	PTYStart                func(*exec.Cmd) (io.ReadWriteCloser, error)
	PTYWrite                func(io.ReadWriteCloser, []byte) (int, error)
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
		InputQueueCapacity:      defaultInputQueue,
		CodexExecutable:         "codex",
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
	mux.HandleFunc("/judge", s.handleJudge)
	return mux
}

func (s *Server) handleJudge(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/judge" {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write(judgeHTML)
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
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	startPTY := s.PTYStart
	if startPTY == nil {
		startPTY = func(command *exec.Cmd) (io.ReadWriteCloser, error) {
			return pty.Start(command)
		}
	}
	ptmx, err := startPTY(cmd)
	if err != nil {
		// Some restricted Unix environments reject Setpgid. Keep the PTY contract
		// usable there; normal Unix targets retain process-group cleanup.
		cmd = exec.Command(s.Shell, s.ShellArgs...)
		ptmx, err = pty.Start(cmd)
		if err != nil {
			sessionError(conn, "pty_start_failed", "shell unavailable")
			return
		}
	}
	newSession(s, conn, id, ptmx, cmd).run()
}

type ptyChunk struct{ data []byte }

type processResult struct{ exitCode int }

type readerResult struct {
	kind readerResultKind
	err  error
}

type readerResultKind uint8

const (
	readerEOF readerResultKind = iota
	readerEIO
	readerCanceled
	readerUnexpected
	readerOverflow
)

type clientEvent struct {
	data []byte
	err  error
}

type inputRequest struct {
	text      []byte
	interrupt bool
}

type outboundMessage struct {
	message serverMessage
	written chan error
}

type session struct {
	conn       *websocket.Conn
	id         string
	ptmx       io.ReadWriteCloser
	cmd        *exec.Cmd
	codex      string
	flush      time.Duration
	batch      int
	max        int
	chunkBytes int
	maxJSON    int
	maxInput   int
	ptyWrite   func(io.ReadWriteCloser, []byte) (int, error)

	chunks       chan ptyChunk
	reader       chan readerResult
	readerDone   chan struct{}
	process      chan processResult
	processDone  chan struct{}
	client       chan clientEvent
	input        chan inputRequest
	inputDone    chan struct{}
	inputFailure chan struct{}
	codexMu      sync.Mutex
	codexCancel  context.CancelFunc
	codexCmd     *exec.Cmd
	codexActive  bool
	outbound     chan outboundMessage
	finished     chan struct{}
	writerDone   chan struct{}
	overflow     chan struct{}
	cancel       chan struct{}

	stopOnce       sync.Once
	processOnce    sync.Once
	overflowOnce   sync.Once
	failureOnce    sync.Once
	finishOnce     sync.Once
	mu             sync.Mutex
	closed         bool
	stopped        bool
	outboundMu     sync.Mutex
	outboundClosed bool
}

func newSession(s *Server, conn *websocket.Conn, id string, ptmx io.ReadWriteCloser, cmd *exec.Cmd) *session {
	ptyWrite := s.PTYWrite
	if ptyWrite == nil {
		ptyWrite = func(writer io.ReadWriteCloser, data []byte) (int, error) {
			return writer.Write(data)
		}
	}
	return &session{
		conn:         conn,
		id:           id,
		ptmx:         ptmx,
		cmd:          cmd,
		codex:        s.CodexExecutable,
		flush:        s.FlushInterval,
		batch:        s.BatchBytes,
		max:          s.MaxBufferBytes,
		chunkBytes:   s.ChunkBytes,
		maxJSON:      s.MaxJSONMessageBytes,
		maxInput:     s.MaxInputTextBytes,
		ptyWrite:     ptyWrite,
		chunks:       make(chan ptyChunk, s.ChunkQueueCapacity),
		reader:       make(chan readerResult, 1),
		readerDone:   make(chan struct{}),
		process:      make(chan processResult, 1),
		processDone:  make(chan struct{}),
		client:       make(chan clientEvent, 1),
		input:        make(chan inputRequest, s.InputQueueCapacity),
		inputDone:    make(chan struct{}),
		inputFailure: make(chan struct{}),
		outbound:     make(chan outboundMessage, s.OutboundQueueCapacity),
		finished:     make(chan struct{}),
		writerDone:   make(chan struct{}),
		overflow:     make(chan struct{}),
		cancel:       make(chan struct{}),
	}
}

func (s *session) run() {
	go s.writeMessages()
	go s.readClient()
	go s.readPTY()
	go s.waitProcess()
	go s.writePTY()
	if !s.enqueue(serverMessage{Version: protocolVersion, Type: "hello", SessionID: s.id}) {
		s.stop()
	}
	go s.aggregate()

selectLoop:
	for {
		select {
		case event := <-s.client:
			if event.err != nil {
				s.stop()
				break selectLoop
			}
			terminate, ack := s.handleClientMessage(event.data)
			if terminate {
				if ack != nil {
					s.waitForWriteAck(ack)
				}
				break selectLoop
			}
		case <-s.finished:
			break selectLoop
		}
	}
	s.stop()
	<-s.finished
	<-s.writerDone
	<-s.inputDone
	<-s.readerDone
	<-s.processDone
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

func (s *session) handleClientMessage(data []byte) (bool, <-chan error) {
	if len(data) > s.maxJSONBytes() {
		return s.terminateWithError("json_too_large", "request exceeds JSON message limit")
	}
	msg, err := decodeClientMessage(data)
	if err != nil {
		if !s.enqueueError(err.Error(), "request rejected") {
			s.stopProcess()
			return true, nil
		}
		return false, nil
	}
	if len(msg.Text) > s.maxInputBytes() {
		return s.terminateWithError("input_too_large", "input text exceeds limit")
	}
	if msg.Type == "codex_prompt" && len(msg.Prompt) > defaultCodexPrompt {
		return s.terminateWithError("codex_prompt_too_large", "Codex prompt exceeds limit")
	}
	if msg.SessionID != s.id {
		if !s.enqueueError("wrong_session", "session rejected") {
			s.stopProcess()
			return true, nil
		}
		return false, nil
	}
	if msg.Type == "codex_prompt" {
		if !s.startCodex(msg.Prompt, msg.RequestID) {
			return s.terminateWithError("codex_busy", "only one Codex process is allowed")
		}
		return false, nil
	}
	if msg.Type == "codex_cancel" {
		s.cancelCodex(msg.RequestID)
		return false, nil
	}
	if msg.Type == "codex_new_session" {
		s.cancelCodex("")
		return false, nil
	}
	request := inputRequest{interrupt: msg.Type == "control"}
	if msg.Type == "input_text" {
		request.text = []byte(msg.Text)
	}
	if msg.Type == "close" {
		return true, nil
	}
	select {
	case s.input <- request:
		return false, nil
	default:
		return s.terminateWithError("input_overflow", "terminal input queue limit exceeded")
	}
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
	defer close(s.readerDone)
	buf := make([]byte, s.chunkBytes)
	result := readerResult{kind: readerEOF}
	defer func() {
		s.reader <- result
	}()
	for {
		n, err := s.ptmx.Read(buf)
		if n > 0 {
			chunk := ptyChunk{data: append([]byte(nil), buf[:n]...)}
			select {
			case s.chunks <- chunk:
			case <-s.cancel:
				result.kind = readerCanceled
				return
			default:
				signalOverflow(s.overflow, &s.overflowOnce)
				result.kind = readerOverflow
				return
			}
		}
		if err != nil {
			result.err = err
			if errors.Is(err, syscall.EIO) {
				result.kind = readerEIO
			} else if errors.Is(err, io.EOF) {
				result.kind = readerEOF
			} else {
				result.kind = readerUnexpected
			}
			return
		}
	}
}

func (s *session) waitProcess() {
	defer close(s.processDone)
	err := s.cmd.Wait()
	code := -1
	if err == nil || s.cmd.ProcessState != nil {
		code = exitCode(s.cmd)
	}
	s.process <- processResult{exitCode: code}
}

func (s *session) writePTY() {
	defer close(s.inputDone)
	for {
		select {
		case request := <-s.input:
			var err error
			if request.interrupt {
				_, err = s.ptyWrite(s.ptmx, []byte{3})
			} else {
				_, err = s.ptyWrite(s.ptmx, request.text)
			}
			if err != nil {
				s.failureOnce.Do(func() { close(s.inputFailure) })
				return
			}
		case <-s.cancel:
			return
		}
	}
}

func (s *session) aggregate() {
	timer := time.NewTimer(s.flush)
	if !timer.Stop() {
		<-timer.C
	}
	defer timer.Stop()
	pending := make([]byte, 0, s.max)
	processExited := false
	ptyReaderFinished := false
	canceled := false
	failed := false
	lastExitCode := -1
	var cancelCh <-chan struct{} = s.cancel

	stopTimer := func() {
		if !timer.Stop() {
			select {
			case <-timer.C:
			default:
			}
		}
	}
	armTimer := func() { stopTimer(); timer.Reset(s.flush) }
	flush := func(final bool) bool {
		text, rest := utf8Prefix(pending, final)
		pending = rest
		if text == "" {
			return true
		}
		return s.enqueue(serverMessage{Version: protocolVersion, Type: "output", SessionID: s.id, Stream: "pty", Text: text})
	}
	finish := func() {
		if s.wasStopped() {
			canceled = true
		}
		if !canceled && !failed {
			if !flush(true) {
				failed = true
			} else if !s.enqueue(serverMessage{Version: protocolVersion, Type: "exit", SessionID: s.id, ExitCode: &lastExitCode}) {
				failed = true
			}
		}
		s.closeOutbound()
		<-s.writerDone
		s.finishOnce.Do(func() { close(s.finished) })
	}
	for !(processExited && ptyReaderFinished) {
		select {
		case <-cancelCh:
			canceled = true
			cancelCh = nil
		case <-s.inputFailure:
			s.failTerminal("input_failed", "terminal input unavailable", &failed)
		case <-s.overflow:
			s.failTerminal("output_overflow", "terminal output limit exceeded", &failed)
		case result := <-s.process:
			processExited = true
			lastExitCode = result.exitCode
		case result := <-s.reader:
			ptyReaderFinished = true
			if result.kind == readerUnexpected {
				s.failTerminal("pty_read_failed", "terminal output unavailable", &failed)
			} else if result.kind == readerOverflow {
				s.failTerminal("output_overflow", "terminal output limit exceeded", &failed)
			}
		case chunk := <-s.chunks:
			wasEmpty := len(pending) == 0
			pending = append(pending, chunk.data...)
			if len(pending) > s.max {
				s.failTerminal("output_overflow", "terminal output limit exceeded", &failed)
				continue
			}
			if containsNewline(pending) || len(pending) >= s.batch {
				if !flush(false) {
					failed = true
					s.stopProcess()
					continue
				}
				if len(pending) == 0 {
					stopTimer()
				} else {
					armTimer()
				}
			} else if wasEmpty {
				armTimer()
			}
		case <-timer.C:
			if !flush(false) {
				failed = true
				s.stopProcess()
				continue
			}
			if len(pending) == 0 {
				stopTimer()
			} else {
				armTimer()
			}
		}
	}
	for {
		select {
		case chunk := <-s.chunks:
			pending = append(pending, chunk.data...)
		default:
			if len(pending) > s.max {
				failed = true
			}
			finish()
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

func signalOverflow(ch chan struct{}, once *sync.Once) { once.Do(func() { close(ch) }) }

func (s *session) enqueueMessage(msg outboundMessage) bool {
	s.outboundMu.Lock()
	defer s.outboundMu.Unlock()
	if s.outboundClosed {
		return false
	}
	select {
	case s.outbound <- msg:
		return true
	default:
		return false
	}
}

func (s *session) enqueue(msg serverMessage) bool {
	return s.enqueueMessage(outboundMessage{message: msg})
}

func (s *session) enqueueError(code, message string) bool {
	return s.enqueue(serverMessage{Version: protocolVersion, Type: "error", SessionID: s.id, Code: code, Message: message})
}

func (s *session) enqueueTerminalError(code, message string) (<-chan error, bool) {
	ack := make(chan error, 1)
	if !s.enqueueMessage(outboundMessage{
		message: serverMessage{Version: protocolVersion, Type: "error", SessionID: s.id, Code: code, Message: message},
		written: ack,
	}) {
		return nil, false
	}
	return ack, true
}

func (s *session) waitForWriteAck(ack <-chan error) {
	timer := time.NewTimer(writeTimeout)
	defer timer.Stop()
	select {
	case <-ack:
	case <-s.writerDone:
	case <-s.cancel:
	case <-timer.C:
	}
}

func (s *session) failTerminal(code, message string, failed *bool) {
	if *failed {
		return
	}
	*failed = true
	if ack, ok := s.enqueueTerminalError(code, message); ok {
		s.waitForWriteAck(ack)
	}
	s.stopProcess()
}

func (s *session) closeOutbound() {
	s.outboundMu.Lock()
	defer s.outboundMu.Unlock()
	if !s.outboundClosed {
		s.outboundClosed = true
		close(s.outbound)
	}
}

func (s *session) writeMessages() {
	defer close(s.writerDone)
	for item := range s.outbound {
		err := error(nil)
		if !s.write(item.message) {
			err = io.ErrClosedPipe
		}
		if item.written != nil {
			item.written <- err
		}
		if err != nil {
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
		s.cancelCodex("")
		s.stopProcess()
		_ = s.conn.Close()
		s.mu.Lock()
		s.closed = true
		s.mu.Unlock()
	})
}

func (s *session) stopProcess() {
	s.processOnce.Do(func() {
		s.mu.Lock()
		s.stopped = true
		s.mu.Unlock()
		close(s.cancel)
		_ = s.ptmx.Close()
		if s.cmd.Process != nil {
			_ = syscall.Kill(-s.cmd.Process.Pid, syscall.SIGKILL)
			_ = s.cmd.Process.Kill()
		}
	})
}

func (s *session) wasStopped() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stopped
}

func (s *session) terminateWithError(code, message string) (bool, <-chan error) {
	ack, ok := s.enqueueTerminalError(code, message)
	if !ok {
		s.stop()
		return true, nil
	}
	return true, ack
}

func sessionError(conn *websocket.Conn, code, message string) {
	_ = conn.SetWriteDeadline(time.Now().Add(writeTimeout))
	_ = conn.WriteJSON(serverMessage{Version: protocolVersion, Type: "error", Code: code, Message: message})
}
