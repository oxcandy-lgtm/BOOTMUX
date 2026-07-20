package main

import (
	"encoding/json"
	"errors"
	"fmt"
)

const protocolVersion = 1

var errMirrorReadOnly = errors.New("mirror_read_only")

type clientMessage struct {
	Version   int    `json:"v"`
	Type      string `json:"type"`
	SessionID string `json:"session_id"`
	Text      string `json:"text"`
	Control   string `json:"control"`
	Prompt    string `json:"prompt"`
	RequestID string `json:"request_id"`
}

type serverMessage struct {
	Version   int    `json:"v"`
	Type      string `json:"type"`
	SessionID string `json:"session_id"`
	Stream    string `json:"stream,omitempty"`
	Text      string `json:"text,omitempty"`
	ExitCode  *int   `json:"exit_code,omitempty"`
	Code      string `json:"code,omitempty"`
	Message   string `json:"message,omitempty"`
	RequestID string `json:"request_id,omitempty"`
}

func decodeClientMessage(data []byte) (clientMessage, error) {
	var msg clientMessage
	if err := json.Unmarshal(data, &msg); err != nil {
		return msg, fmt.Errorf("malformed_json")
	}
	if msg.Version != protocolVersion {
		return msg, fmt.Errorf("unsupported_version")
	}
	if msg.Type == "" || msg.SessionID == "" {
		return msg, fmt.Errorf("malformed_message")
	}
	switch msg.Type {
	case "input_text":
		if msg.Text == "" {
			return msg, fmt.Errorf("malformed_message")
		}
	case "control":
		if msg.Control != "interrupt" {
			return msg, fmt.Errorf("unsupported_control")
		}
	case "close":
	case "codex_prompt":
		if msg.Prompt == "" || msg.RequestID == "" {
			return msg, fmt.Errorf("malformed_message")
		}
	case "codex_cancel":
		if msg.RequestID == "" {
			return msg, fmt.Errorf("malformed_message")
		}
	case "codex_new_session":
	default:
		return msg, fmt.Errorf("unsupported_message_type")
	}
	return msg, nil
}
