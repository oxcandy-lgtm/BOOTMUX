#!/usr/bin/env python3
"""Bounded, payload-opaque TCP forwarder for the VM Companion."""
import argparse
import asyncio
import itertools

MAX_CONNECTIONS = 2
BUFFER_BYTES = 64 * 1024
IDLE_SECONDS = 300


async def relay(reader, writer, target_host, target_port, semaphore, connection_counter):
    connection_id = next(connection_counter)
    print(f"CONNECTION_ACCEPTED id={connection_id}", flush=True)
    async with semaphore:
        try:
            target_reader, target_writer = await asyncio.wait_for(
                asyncio.open_connection(target_host, target_port), timeout=10
            )
            print(f"TARGET_CONNECTED id={connection_id}", flush=True)
        except Exception:
            writer.close()
            await writer.wait_closed()
            print(f"CONNECTION_CLOSED id={connection_id}", flush=True)
            return

        async def pipe(source, destination):
            try:
                while True:
                    data = await asyncio.wait_for(source.read(BUFFER_BYTES), IDLE_SECONDS)
                    if not data:
                        return
                    destination.write(data)
                    await destination.drain()
            finally:
                destination.close()

        await asyncio.gather(pipe(reader, target_writer), pipe(target_reader, writer), return_exceptions=True)
        writer.close()
        target_writer.close()
        await asyncio.gather(writer.wait_closed(), target_writer.wait_closed(), return_exceptions=True)
        print(f"CONNECTION_CLOSED id={connection_id}", flush=True)


async def main(listen_host, listen_port, target_host, target_port):
    semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
    connection_counter = itertools.count(1)
    server = await asyncio.start_server(
        lambda r, w: relay(r, w, target_host, target_port, semaphore, connection_counter),
        listen_host,
        listen_port,
    )
    print("FORWARDER_READY", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    listen_host, listen_port = args.listen.rsplit(":", 1)
    target_host, target_port = args.target.rsplit(":", 1)
    asyncio.run(main(listen_host, int(listen_port), target_host, int(target_port)))
