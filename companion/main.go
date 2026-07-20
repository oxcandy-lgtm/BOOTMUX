//go:build !probe

package main

import (
	"flag"
	"log"
	"net"
	"net/http"
	"strings"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:8765", "listen address; loopback is the default")
	shell := flag.String("shell", "/bin/sh", "explicit shell executable")
	allowRemote := flag.Bool("allow-remote", false, "explicitly allow a non-loopback bind")
	codexExecutable := flag.String("codex", "codex", "Codex executable used by bounded codex_prompt messages")
	flag.Parse()
	if !*allowRemote && !isLoopbackAddress(*addr) {
		log.Fatal("non-loopback bind requires -allow-remote")
	}
	log.Printf("BOOTMUX Companion listening on %s", *addr)
	server := NewServer(*shell, "-i")
	server.CodexExecutable = *codexExecutable
	if err := http.ListenAndServe(*addr, server.Handler()); err != nil {
		log.Fatal(err)
	}
}

func isLoopbackAddress(addr string) bool {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return false
	}
	return host == "localhost" || strings.Trim(host, "[]") == "127.0.0.1" || strings.Trim(host, "[]") == "::1"
}
