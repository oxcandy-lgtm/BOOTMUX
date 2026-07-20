//go:build !probe

package main

import (
	"flag"
	"log"
	"net/http"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:8765", "listen address; loopback is the default")
	shell := flag.String("shell", "/bin/sh", "explicit shell executable")
	flag.Parse()
	log.Printf("BOOTMUX Companion listening on %s", *addr)
	if err := http.ListenAndServe(*addr, NewServer(*shell, "-i").Handler()); err != nil {
		log.Fatal(err)
	}
}
