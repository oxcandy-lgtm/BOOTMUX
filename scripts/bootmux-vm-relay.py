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
    connection_id = 0
    with socket.create_server((args.listen_host, args.listen_port), backlog=1) as server:
        server.settimeout(IDLE_SECONDS)
        print("VM_RELAY_ACCEPT_READY", flush=True)
        while True:
            try:
                client, _ = server.accept()
            except TimeoutError:
                continue
            connection_id += 1
            current_id = connection_id
            print(f"VM_RELAY_ACCEPT id={current_id}", flush=True)
            with client:
                print(f"VM_RELAY_UPSTREAM_CONNECT_START id={current_id}", flush=True)
                try:
                    target = socket.create_connection((args.target_host, args.target_port), timeout=15)
                except OSError:
                    print(f"VM_RELAY_CLOSE id={current_id} reason=upstream_connect_failed", flush=True)
                    continue
                print(f"VM_RELAY_UPSTREAM_CONNECTED id={current_id}", flush=True)
                with target:
                    try:
                        relay(client, target)
                    finally:
                        print(f"VM_RELAY_CLOSE id={current_id} reason=relay_done", flush=True)

if __name__ == "__main__":
    main()
