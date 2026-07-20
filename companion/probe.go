//go:build probe

package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

func runProbe(endpoint string) error {
	u, err := url.Parse(endpoint)
	if err != nil {
		return err
	}
	c, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return err
	}
	defer c.Close()
	_, data, err := c.ReadMessage()
	if err != nil {
		return err
	}
	var hello serverMessage
	if err = json.Unmarshal(data, &hello); err != nil || hello.Type != "hello" || hello.SessionID == "" {
		return fmt.Errorf("invalid hello")
	}
	command := fmt.Sprintf("printf 'BOOTMUX_V0A\\n'; exit 0\n")
	if err = c.WriteJSON(clientMessage{Version: protocolVersion, Type: "input_text", SessionID: hello.SessionID, Text: command}); err != nil {
		return err
	}
	found, exited := false, false
	deadline := time.Now().Add(3 * time.Second)
	_ = c.SetReadDeadline(deadline)
	for !exited {
		_, data, err = c.ReadMessage()
		if err != nil {
			return err
		}
		var msg serverMessage
		if err = json.Unmarshal(data, &msg); err != nil {
			return err
		}
		if msg.Type == "error" {
			return fmt.Errorf("%s", msg.Code)
		}
		if msg.Type == "output" && strings.Contains(msg.Text, "BOOTMUX_V0A") {
			found = true
		}
		if msg.Type == "exit" {
			exited = true
		}
	}
	if !found {
		return fmt.Errorf("marker not observed")
	}
	return nil
}

func main() {
	endpoint := flag.String("endpoint", "ws://127.0.0.1:8765/v1/terminal", "Companion endpoint")
	flag.Parse()
	if err := runProbe(*endpoint); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("BOOTMUX_V0A observed")
}
