#!/bin/sh
set -eu
prompt=${1-}
[ -n "$prompt" ] || { echo PROMPT_REQUIRED >&2; exit 64; }
[ "$(printf %s "$prompt" | wc -c | tr -d ' ')" -le 8192 ] || { echo PROMPT_TOO_LARGE >&2; exit 65; }
command -v codex >/dev/null 2>&1 || { echo CODEX_NOT_INSTALLED >&2; exit 69; }
timeout 180 codex exec "$prompt" 2>&1 | head -c 131072
