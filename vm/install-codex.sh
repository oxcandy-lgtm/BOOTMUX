#!/bin/sh
set -eu
if command -v codex >/dev/null 2>&1; then echo CODEX_ALREADY_PRESENT >&2; exit 65; fi
command -v node >/dev/null 2>&1 || { echo NODE_REQUIRED_FOR_OFFICIAL_NPM_ROUTE >&2; exit 69; }
command -v npm >/dev/null 2>&1 || { echo NPM_REQUIRED_FOR_OFFICIAL_NPM_ROUTE >&2; exit 69; }
version=$(npm view @openai/codex version --registry https://registry.npmjs.org/)
[ -n "$version" ] || { echo OFFICIAL_CODEX_VERSION_UNAVAILABLE >&2; exit 70; }
case "$version" in *[!0-9A-Za-z.@_-]*) echo UNSAFE_VERSION >&2; exit 70;; esac
npm install --global "@openai/codex@$version" --registry https://registry.npmjs.org/ --no-audit --no-fund
command -v codex >/dev/null 2>&1
codex --version
