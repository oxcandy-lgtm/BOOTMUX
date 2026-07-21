#!/usr/bin/env python3
"""Bounded local forwarder for the BOOTMUX demo CONNECT proxy."""
import argparse
import selectors
import socket

BUFFER = 4096
IDLE_SECONDS = 300

def relay(left, right):
    selector = selectors.DefaultSelector()
    selector.register(left, selectors.EVENT_READ, right)
    selector.register(right, selectors.EVENT_READ, left)
    while True:
        events = selector.select(IDLE_SECONDS)
        if not events:
            return
        for key, _ in events:
            data = key.fileobj.recv(BUFFER)
            if not data:
                return
            destination = key.data
            destination.sendall(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=33128)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, default=3128)
    args = parser.parse_args()
    with socket.create_server((args.listen_host, args.listen_port), backlog=1) as server:
        server.settimeout(IDLE_SECONDS)
        while True:
            client, _ = server.accept()
            with client, socket.create_connection((args.target_host, args.target_port), timeout=15) as target:
                relay(client, target)

if __name__ == "__main__":
    main()
