#!/bin/sh
set -eu
if command -v codex >/dev/null 2>&1; then echo CODEX_ALREADY_PRESENT >&2; exit 65; fi
node_major=0
if command -v node >/dev/null 2>&1; then
  node_major=$(node --version | sed 's/^v//' | cut -d. -f1)
fi
case "$node_major" in ''|*[!0-9]*) node_major=0;; esac
if [ "$node_major" -lt 16 ]; then
  command -v curl >/dev/null 2>&1 || { echo CURL_REQUIRED_FOR_OFFICIAL_NODE_ROUTE >&2; exit 69; }
  command -v python3 >/dev/null 2>&1 || { echo PYTHON_REQUIRED_FOR_OFFICIAL_NODE_ROUTE >&2; exit 69; }
  node_version=$(curl --fail --silent --show-error --max-time 30 https://nodejs.org/dist/index.json | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(next(row["version"] for row in rows if row["lts"]))')
  case "$node_version" in v[0-9]*.[0-9]*.[0-9]*) ;; *) echo UNSAFE_NODE_VERSION >&2; exit 70;; esac
  node_root="$HOME/.local/node-$node_version"
  if [ ! -x "$node_root/bin/node" ]; then
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM
    archive="$tmp_dir/node-$node_version-linux-arm64.tar.xz"
    curl --fail --silent --show-error --location --max-time 120 -o "$archive" "https://nodejs.org/dist/$node_version/node-$node_version-linux-arm64.tar.xz"
    curl --fail --silent --show-error --location --max-time 30 "https://nodejs.org/dist/$node_version/SHASUMS256.txt" | awk "/node-$node_version-linux-arm64.tar.xz\$/ {print \$1 \"  \" \"$archive\"}" | sha256sum -c -
    mkdir -p "$HOME/.local"
    tar -xJf "$archive" -C "$HOME/.local"
    mv "$HOME/.local/node-$node_version-linux-arm64" "$node_root"
  fi
  ln -sfn "$node_root" "$HOME/.local/node"
  export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"
  profile="$HOME/.profile"
  touch "$profile"
  if ! grep -Fq '$HOME/.local/node/bin:$HOME/.local/bin' "$profile"; then
    printf '\nexport PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"\n' >> "$profile"
  fi
fi
command -v node >/dev/null 2>&1 || { echo NODE_REQUIRED_FOR_OFFICIAL_NPM_ROUTE >&2; exit 69; }
command -v npm >/dev/null 2>&1 || { echo NPM_REQUIRED_FOR_OFFICIAL_NPM_ROUTE >&2; exit 69; }
version=$(npm view @openai/codex version --registry https://registry.npmjs.org/)
[ -n "$version" ] || { echo OFFICIAL_CODEX_VERSION_UNAVAILABLE >&2; exit 70; }
case "$version" in *[!0-9A-Za-z.@_-]*) echo UNSAFE_VERSION >&2; exit 70;; esac
mkdir -p "$HOME/.local/bin"
npm install --global --prefix "$HOME/.local" "@openai/codex@$version" --registry https://registry.npmjs.org/ --no-audit --no-fund
export PATH="$HOME/.local/bin:$PATH"
command -v codex >/dev/null 2>&1
codex --version
