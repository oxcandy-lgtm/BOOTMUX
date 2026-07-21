# Local Wi-Fi secret contract

BOOTMUX Wi-Fi credentials are supplied from the Mac-only file
`~/.config/bootmux/secrets/wifi.env`. The file is outside the repository, is
owned by the local user, and must have mode `0600`; its parent directories must
have mode `0700`.

The tracked helper `scripts/bootmux-copy-local-wifi-secret.py` accepts only
`ssid` or `password`, sends the selected value to macOS `pbcopy`, and prints
only a public-safe acknowledgement. It never prints the value, passes it as a
process argument, or writes it to repository files. The helper is a bounded
manual fallback for first provisioning; it does not prove that the S3 is
currently online.

Credentials must not be placed in source, fixtures, UserDefaults, logs,
diagnostics, PR text, or commits. The local ignore rules are intentionally
untracked and are not a substitute for the file being stored outside the
repository.
