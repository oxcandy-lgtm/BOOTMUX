package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"
	"unicode/utf8"

	"github.com/gorilla/websocket"
)

func dialTest(t *testing.T, s *Server) (*websocket.Conn, serverMessage) {
	t.Helper()
	h := httptest.NewServer(s.Handler())
	t.Cleanup(h.Close)
	u := "ws" + strings.TrimPrefix(h.URL, "http") + "/v1/terminal"
	c, _, err := websocket.DefaultDialer.Dial(u, nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { c.Close() })
	_, b, err := c.ReadMessage()
	if err != nil {
		t.Fatal(err)
	}
	var hello serverMessage
	if json.Unmarshal(b, &hello) != nil {
		t.Fatal("bad hello")
	}
	return c, hello
}

func readUntil(t *testing.T, c *websocket.Conn, typ string) serverMessage {
	t.Helper()
	_ = c.SetReadDeadline(time.Now().Add(3 * time.Second))
	for {
		_, b, err := c.ReadMessage()
		if err != nil {
			t.Fatal(err)
		}
		var m serverMessage
		if json.Unmarshal(b, &m) != nil {
			t.Fatal("bad message")
		}
		if m.Type == typ {
			return m
		}
	}
}

func TestProtocolAndSessionRejection(t *testing.T) {
	c, h := dialTest(t, NewServer("/bin/sh", "-i"))
	if err := c.WriteJSON(map[string]any{"v": 99, "type": "input_text", "session_id": h.SessionID, "text": "x"}); err != nil {
		t.Fatal(err)
	}
	if got := readUntil(t, c, "error"); got.Code != "unsupported_version" {
		t.Fatalf("code=%s", got.Code)
	}
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: "other", Text: "x"}); err != nil {
		t.Fatal(err)
	}
	if got := readUntil(t, c, "error"); got.Code != "wrong_session" {
		t.Fatalf("code=%s", got.Code)
	}
	if _, err := decodeClientMessage([]byte("{")); err == nil {
		t.Fatal("malformed JSON accepted")
	}
}

func TestCodexMessagesAreBoundedAndSessionScoped(t *testing.T) {
	msg, err := decodeClientMessage([]byte(`{"v":1,"type":"codex_prompt","session_id":"s","request_id":"r1","prompt":"BOOTMUX_READY"}`))
	if err != nil || msg.Prompt != "BOOTMUX_READY" || msg.RequestID != "r1" {
		t.Fatalf("codex prompt decode failed: %+v %v", msg, err)
	}
	if _, err := decodeClientMessage([]byte(`{"v":1,"type":"codex_prompt","session_id":"s","prompt":"x"}`)); err == nil {
		t.Fatal("codex prompt without request id accepted")
	}
}

func TestTerminalErrorUsesItsOwnWriteAck(t *testing.T) {
	s := NewServer("/bin/sh", "-i")
	s.MaxInputTextBytes = 4
	c, h := dialTest(t, s)
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: "wrong", Text: "x"}); err != nil {
		t.Fatal(err)
	}
	if got := readUntil(t, c, "error"); got.Code != "wrong_session" {
		t.Fatalf("first error=%+v", got)
	}
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: "12345"}); err != nil {
		t.Fatal(err)
	}
	if got := readUntil(t, c, "error"); got.Code != "input_too_large" {
		t.Fatalf("terminal error consumed wrong ACK: %+v", got)
	}
	_ = c.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	for {
		if _, _, err := c.ReadMessage(); err != nil {
			return
		}
	}
}

func TestPTYOutputExitAndBatching(t *testing.T) {
	s := NewServer("/bin/sh", "-i")
	s.FlushInterval = time.Millisecond
	s.BatchBytes = 1024
	c, h := dialTest(t, s)
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: "printf 'BOOTMUX_V0A'; exit 7\n"}); err != nil {
		t.Fatal(err)
	}
	out := readUntil(t, c, "output")
	if !strings.Contains(out.Text, "BOOTMUX_V0A") || out.Stream != "pty" {
		t.Fatalf("output=%+v", out)
	}
	exit := readUntil(t, c, "exit")
	if exit.ExitCode == nil || *exit.ExitCode != 7 {
		t.Fatalf("exit=%+v", exit)
	}
}

func TestTimerOnlyFlush(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "printf timer_only; sleep 1")
	s.FlushInterval = 40 * time.Millisecond
	s.BatchBytes = 1024
	started := time.Now()
	c, _ := dialTest(t, s)
	out := readUntil(t, c, "output")
	if elapsed := time.Since(started); elapsed > 500*time.Millisecond {
		t.Fatalf("timer flush waited for PTY read/process: %s", elapsed)
	}
	if out.Text != "timer_only" {
		t.Fatalf("output=%q", out.Text)
	}
}

func TestFlushIntervalIsMaximumLatencyNotDebounce(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "for i in $(seq 1 20); do printf x; sleep .005; done; sleep 1")
	s.FlushInterval = 50 * time.Millisecond
	s.BatchBytes = 1024
	started := time.Now()
	c, _ := dialTest(t, s)
	out := readUntil(t, c, "output")
	if elapsed := time.Since(started); elapsed < 35*time.Millisecond || elapsed > 300*time.Millisecond {
		t.Fatalf("first output arrived outside maximum-latency window: %s", elapsed)
	}
	if out.Text == "" {
		t.Fatal("timer produced empty output")
	}
	// The producer is still sleeping when the first timer-driven frame arrives.
	_ = c.Close()
}

func TestProcessExitClosesSessionAfterSingleExit(t *testing.T) {
	c, h := dialTest(t, NewServer("/bin/sh", "-c", "printf done; exit 3"))
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "close", SessionID: h.SessionID}); err == nil {
		// The command may finish before the close is consumed; either path must terminate.
	}
	// Use a fresh session to observe the production exit lifecycle deterministically.
	c.Close()
	c, _ = dialTest(t, NewServer("/bin/sh", "-c", "printf done; exit 3"))
	_ = readUntil(t, c, "output")
	exit := readUntil(t, c, "exit")
	if exit.ExitCode == nil || *exit.ExitCode != 3 {
		t.Fatalf("exit=%+v", exit)
	}
	_ = c.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	if _, _, err := c.ReadMessage(); err == nil {
		t.Fatal("session remained open after exit")
	}
}

func TestTailOutputIsCompleteBeforeExitRepeated(t *testing.T) {
	const marker = "R2_TAIL_MARKER"
	for iteration := 0; iteration < 100; iteration++ {
		s := NewServer("/bin/sh", "-c", fmt.Sprintf("dd if=/dev/zero bs=65536 count=1 2>/dev/null; printf '%s'", marker))
		s.MaxBufferBytes = 128 * 1024
		s.BatchBytes = 2048
		s.ChunkBytes = 1024
		s.ChunkQueueCapacity = 1024
		s.OutboundQueueCapacity = 128
		c, _ := dialTest(t, s)
		var output strings.Builder
		exits := 0
		_ = c.SetReadDeadline(time.Now().Add(5 * time.Second))
		for {
			_, data, err := c.ReadMessage()
			if err != nil {
				t.Fatalf("iteration %d read: %v", iteration, err)
			}
			var msg serverMessage
			if err := json.Unmarshal(data, &msg); err != nil {
				t.Fatal(err)
			}
			switch msg.Type {
			case "output":
				output.WriteString(msg.Text)
			case "exit":
				exits++
				if msg.ExitCode == nil || *msg.ExitCode != 0 {
					t.Fatalf("iteration %d exit=%+v", iteration, msg)
				}
				goto receivedExit
			case "error":
				t.Fatalf("iteration %d error=%+v", iteration, msg)
			}
		}
	receivedExit:
		if exits != 1 || output.Len() != 65536+len(marker) || !strings.HasSuffix(output.String(), marker) {
			t.Fatalf("iteration %d output_len=%d exits=%d tail=%q", iteration, output.Len(), exits, output.String()[max(0, output.Len()-len(marker)):])
		}
		_ = c.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
		if _, _, err := c.ReadMessage(); err == nil {
			t.Fatalf("iteration %d session remained open", iteration)
		}
	}
}

func TestOutputOverflowIsExplicit(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "printf abc")
	s.ChunkBytes = 1
	s.MaxBufferBytes = 2
	s.BatchBytes = 1024
	c, _ := dialTest(t, s)
	if got := readUntil(t, c, "error"); got.Code != "output_overflow" {
		t.Fatalf("error=%+v", got)
	}
	_ = c.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	if _, _, err := c.ReadMessage(); err == nil {
		t.Fatal("overflow session remained open")
	}
}

func TestInterruptAndUTF8(t *testing.T) {
	c, h := dialTest(t, NewServer("/bin/sh", "-i"))
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: "printf 'あ\n'; sleep 5\n"}); err != nil {
		t.Fatal(err)
	}
	out := readUntil(t, c, "output")
	if !utf8.ValidString(out.Text) || !strings.Contains(out.Text, "あ") {
		t.Fatalf("invalid UTF-8 output: %q", out.Text)
	}
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "control", SessionID: h.SessionID, Control: "interrupt"}); err != nil {
		t.Fatal(err)
	}
	_ = readUntil(t, c, "exit")
}

func TestUTF8SplitAcrossPTYChunks(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "printf 'あ'; sleep 1")
	s.ChunkBytes = 1
	s.FlushInterval = 10 * time.Millisecond
	c, _ := dialTest(t, s)
	out := readUntil(t, c, "output")
	if !utf8.ValidString(out.Text) || out.Text != "あ" {
		t.Fatalf("split UTF-8 output=%q", out.Text)
	}
}

func TestInputLimitsAndOriginPolicy(t *testing.T) {
	s := NewServer("/bin/sh", "-i")
	s.MaxInputTextBytes = 4
	c, h := dialTest(t, s)
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: "12345"}); err != nil {
		t.Fatal(err)
	}
	if got := readUntil(t, c, "error"); got.Code != "input_too_large" {
		t.Fatalf("error=%+v", got)
	}

	httpServer := httptest.NewServer(s.Handler())
	t.Cleanup(httpServer.Close)
	u := "ws" + strings.TrimPrefix(httpServer.URL, "http") + "/v1/terminal"
	dialer := websocket.Dialer{}
	_, response, err := dialer.Dial(u, http.Header{"Origin": []string{"https://foreign.example"}})
	if err == nil {
		t.Fatal("foreign Origin was accepted")
	}
	if response != nil && response.Body != nil {
		response.Body.Close()
	}
}

func TestJSONAndWebSocketMessageLimits(t *testing.T) {
	s := NewServer("/bin/sh", "-i")
	c, h := dialTest(t, s)
	jsonPayload := append([]byte(`{"v":1,"type":"input_text","session_id":"`+h.SessionID+`","text":"`), bytes.Repeat([]byte("x"), 12*1024)...)
	jsonPayload = append(jsonPayload, []byte(`"}`)...)
	if err := c.WriteMessage(websocket.TextMessage, jsonPayload); err != nil {
		t.Fatal(err)
	}
	if got := readUntil(t, c, "error"); got.Code != "json_too_large" {
		t.Fatalf("error=%+v", got)
	}
	_ = c.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	for {
		if _, _, err := c.ReadMessage(); err != nil {
			break
		}
	}

	c, _ = dialTest(t, NewServer("/bin/sh", "-i"))
	if err := c.WriteMessage(websocket.TextMessage, bytes.Repeat([]byte("x"), maxWebSocketMessage+1)); err != nil {
		t.Fatal(err)
	}
	_ = c.SetReadDeadline(time.Now().Add(1 * time.Second))
	if _, _, err := c.ReadMessage(); err == nil {
		t.Fatal("WebSocket message limit did not close connection")
	}
}

func TestNewSessionIsolationAndChildCleanup(t *testing.T) {
	s := NewServer("/bin/sh", "-i")
	first, h1 := dialTest(t, s)
	second, h2 := dialTest(t, s)
	if h1.SessionID == h2.SessionID {
		t.Fatal("sessions reused an identifier")
	}
	if err := first.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h1.SessionID, Text: "sleep 10\n"}); err != nil {
		t.Fatal(err)
	}
	if err := first.Close(); err != nil {
		t.Fatal(err)
	}
	if err := second.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h2.SessionID, Text: "printf isolated; exit\n"}); err != nil {
		t.Fatal(err)
	}
	out := readUntil(t, second, "output")
	if !strings.Contains(out.Text, "isolated") || strings.Contains(out.Text, "sleep") {
		t.Fatalf("session output mixed: %q", out.Text)
	}
}

func TestChildCleanupLeavesNoSentinel(t *testing.T) {
	dir := t.TempDir()
	sentinel := fmt.Sprintf("%s/sentinel", dir)
	s := NewServer("/bin/sh", "-c", fmt.Sprintf("(sleep 2; printf survived > %q) & wait", sentinel))
	c, _ := dialTest(t, s)
	if err := c.Close(); err != nil {
		t.Fatal(err)
	}
	deadline := time.Now().Add(2500 * time.Millisecond)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(sentinel); err == nil {
			t.Fatal("child survived session close and wrote sentinel")
		}
		time.Sleep(10 * time.Millisecond)
	}
}

func TestInputQueueIsBoundedAndClosable(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "sleep 5")
	s.InputQueueCapacity = 1
	s.PTYWrite = func(writer io.ReadWriteCloser, data []byte) (int, error) {
		time.Sleep(100 * time.Millisecond)
		return writer.Write(data)
	}
	c, h := dialTest(t, s)
	payload := strings.Repeat("i", s.MaxInputTextBytes)
	for i := 0; i < 256; i++ {
		if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: payload}); err != nil {
			break
		}
	}
	started := time.Now()
	_ = c.SetReadDeadline(time.Now().Add(1 * time.Second))
	sawOverflow := false
	for {
		_, data, err := c.ReadMessage()
		if err != nil {
			break
		}
		var msg serverMessage
		if json.Unmarshal(data, &msg) == nil && msg.Type == "error" && msg.Code == "input_overflow" {
			sawOverflow = true
		}
	}
	_ = c.Close()
	if !sawOverflow {
		t.Fatal("input queue did not produce input_overflow before close")
	}
	if elapsed := time.Since(started); elapsed > 500*time.Millisecond {
		t.Fatalf("client close blocked behind PTY input writer: %s", elapsed)
	}
}

func TestOutboundCloseRaceWithTerminalAndNonTerminalErrors(t *testing.T) {
	for iteration := 0; iteration < 500; iteration++ {
		s := NewServer("/bin/sh", "-c", "printf race; exit 0")
		c, h := dialTest(t, s)
		for i := 0; i < 3; i++ {
			_ = c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: "wrong", Text: "x"})
			_ = c.WriteMessage(websocket.TextMessage, []byte("{"))
		}
		_ = c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: strings.Repeat("x", maxInputTextBytes+1)})
		_ = c.SetReadDeadline(time.Now().Add(1 * time.Second))
		for {
			if _, _, err := c.ReadMessage(); err != nil {
				break
			}
		}
		_ = c.Close()
	}
}

func TestTerminalErrorDisconnectStress(t *testing.T) {
	for iteration := 0; iteration < 100; iteration++ {
		s := NewServer("/bin/sh", "-i")
		c, h := dialTest(t, s)
		_ = c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: strings.Repeat("x", maxInputTextBytes+1)})
		_ = c.Close()
	}
}

type unexpectedPTY struct{}

func (unexpectedPTY) Read([]byte) (int, error)  { return 0, errors.New("injected reader failure") }
func (unexpectedPTY) Write([]byte) (int, error) { return 0, nil }
func (unexpectedPTY) Close() error              { return nil }

func TestUnexpectedPTYReaderErrorFailsClosed(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "sleep 5")
	s.PTYStart = func(cmd *exec.Cmd) (io.ReadWriteCloser, error) {
		if err := cmd.Start(); err != nil {
			return nil, err
		}
		return unexpectedPTY{}, nil
	}
	c, _ := dialTest(t, s)
	if got := readUntil(t, c, "error"); got.Code != "pty_read_failed" {
		t.Fatalf("error=%+v", got)
	}
	_ = c.SetReadDeadline(time.Now().Add(1 * time.Second))
	for {
		if _, _, err := c.ReadMessage(); err != nil {
			return
		}
	}
}

func TestSlowClientOutputIsBounded(t *testing.T) {
	s := NewServer("/bin/sh", "-c", "dd if=/dev/zero bs=1024 count=1024 2>/dev/null; sleep 1")
	s.BatchBytes = 64
	s.MaxBufferBytes = 128
	s.ChunkBytes = 256
	s.ChunkQueueCapacity = 1
	s.OutboundQueueCapacity = 1
	c, _ := dialTest(t, s)
	// Hold the client read side while production output is being generated.
	time.Sleep(100 * time.Millisecond)
	_ = c.SetReadDeadline(time.Now().Add(2 * time.Second))
	sawOverflow := false
	for {
		_, data, err := c.ReadMessage()
		if err != nil {
			break
		}
		var msg serverMessage
		if json.Unmarshal(data, &msg) == nil && msg.Type == "error" && msg.Code == "output_overflow" {
			sawOverflow = true
		}
	}
	if !sawOverflow {
		t.Fatal("slow client did not receive explicit overflow before session cleanup")
	}
}

func TestBatchingAndBound(t *testing.T) {
	s := NewServer("/bin/sh", "-i")
	s.FlushInterval = time.Millisecond
	s.BatchBytes = 64
	s.MaxBufferBytes = 128
	c, h := dialTest(t, s)
	if err := c.WriteJSON(clientMessage{Version: 1, Type: "input_text", SessionID: h.SessionID, Text: "i=0; while [ $i -lt 200 ]; do printf x; i=$((i+1)); done; exit\n"}); err != nil {
		t.Fatal(err)
	}
	frames := 0
	total := 0
	for {
		m := readUntil(t, c, "output")
		frames++
		total += len(m.Text)
		if len(m.Text) > 128 {
			t.Fatalf("frame bound exceeded: %d", len(m.Text))
		}
		if total >= 200 {
			break
		}
	}
	if frames >= total {
		t.Fatalf("not batched: frames=%d bytes=%d", frames, total)
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
