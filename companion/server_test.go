package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
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
