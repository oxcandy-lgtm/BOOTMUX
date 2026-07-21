#!/usr/bin/env python3
"""Bounded relay exposed only on the demo namespace host veth."""
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
            key.data.sendall(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="10.203.0.1")
    parser.add_argument("--listen-port", type=int, default=3128)
    parser.add_argument("--target-host", default="host.lima.internal")
    parser.add_argument("--target-port", type=int, default=33128)
    args = parser.parse_args()
    with socket.create_server((args.listen_host, args.listen_port), backlog=1) as server:
        server.settimeout(IDLE_SECONDS)
        while True:
            try:
                client, _ = server.accept()
            except TimeoutError:
                continue
            with client:
                try:
                    target = socket.create_connection((args.target_host, args.target_port), timeout=15)
                except OSError:
                    continue
                with target:
                    relay(client, target)

if __name__ == "__main__":
    main()
