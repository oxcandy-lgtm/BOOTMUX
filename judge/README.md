# BOOTMUX Judge Mode

Open `index.html` directly in a browser for an offline replay. It shows selectable terminal text, `BOOTMUX_READY`, reset, simulated command, and native copy behavior without external dependencies or private endpoints.

When the Companion is running on loopback, open `http://127.0.0.1:8765/judge` and choose **Connect live Companion**. Live mode sends a synthetic command through `/v1/terminal` and displays only observed PTY output.

Judge Mode demonstrates the terminal, session, and native-copy experience. It does not prove the physical BLE or USB HID path.
