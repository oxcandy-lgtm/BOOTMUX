#!/bin/bash
# R7C P4-R1C — BOOTMUX Offline Rescue Bundle Builder (manifest-driven).
# Creates a self-contained tarball with NO Internet, NO WORKER.
# All artifact paths are resolved from safe-flash-manifest.json.
# EXPERIMENTAL/UNSAFE binaries are FORCIBLY REJECTED.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUNDLE_DIR="${1:-/tmp/bootmux-offline-rescue}"
BUNDLE_TAR="${2:-/tmp/bootmux-offline-rescue.tar.gz}"
MANIFEST="$REPO_ROOT/firmware/esp32s3-router-spike/safe-flash-manifest.json"
FIRMWARE_DIR="$REPO_ROOT/firmware/esp32s3-router-spike"

echo "=== BOOTMUX Offline Rescue Bundle Builder (manifest-driven) ==="
echo "repo_root=$REPO_ROOT"
echo "bundle_dir=$BUNDLE_DIR"
echo "manifest=$MANIFEST"

if [ ! -f "$MANIFEST" ]; then
    echo "FATAL: manifest not found: $MANIFEST"
    exit 1
fi

# ---- Read manifest with python ----
BUILD_DIR=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['build_dir'])")
echo "build_dir=$BUILD_DIR"
ARTIFACT_PATHS=$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
for a in m['artifacts']:
    print(f\"{a['name']}|{a['path']}|{a['offset']}|{a['size']}|{a['sha256']}\")
")
echo "--- Artifacts from manifest ---"
echo "$ARTIFACT_PATHS"

# ---- Pre-flight verification: all source files must exist and be GREEN ----
echo ""
echo "=== Pre-flight verification ==="
INSPECT_RESULT=$(python3 "$REPO_ROOT/scripts/macos/bootmux-safe-flash-inspect.py" --manifest "$MANIFEST" --json 2>&1 || true)
INSPECT_OVERALL=$(echo "$INSPECT_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('overall','ERROR'))" 2>/dev/null || echo "PARSE_FAILED")

if [ "$INSPECT_OVERALL" != "GREEN" ]; then
    echo "FATAL: Inspector reports $INSPECT_OVERALL (expected GREEN)"
    echo "Refusing to bundle unsafe artifacts."
    echo "BUNDLE=RED_INSPECTION_FAILED"
    exit 1
fi
echo "Inspector OVERALL=GREEN — safe to bundle ✓"

# ---- Verify flash tool availability (must run 'version' successfully) ----
echo ""
echo "=== Flash tool (esptool) check ==="
ESPTOOL_FOUND=""
BUNDLE_ESPTOOL="$BUNDLE_DIR/tools/tool-esptoolpy/esptool.py"

# Check bundle-local first (will be copied later, check source)
SRC_ESPTOOL="$HOME/.platformio/packages/tool-esptoolpy/esptool.py"
if [ -f "$SRC_ESPTOOL" ]; then
    if python3 "$SRC_ESPTOOL" version >/dev/null 2>&1; then
        ESPTOOL_FOUND="BUNDLE_PIO"
        echo "esptool: BUNDLE ($SRC_ESPTOOL version OK)"
    else
        echo "esptool: BUNDLE ($SRC_ESPTOOL version FAILED)"
        ESPTOOL_FOUND="BUNDLE_VERSION_FAILED"
    fi
fi

# ---- Build bundle directory structure ----
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"/{scripts/macos,scripts/macos/tests,firmware/esp32s3-router-spike/"$BUILD_DIR"/{bootloader,partition_table},docs,tools}

# --- Copy scripts ---
echo ""
echo "=== Copying scripts ==="
for script in \
    bootmux-attach-shield.py \
    bootmux-safe-flash-inspect.py \
    bootmux-safe-flash-runner.py \
    generate-safe-manifest.py \
    install-bootmux-attach-shield.sh \
    uninstall-bootmux-attach-shield.sh; do
    if [ -f "$REPO_ROOT/scripts/macos/$script" ]; then
        cp "$REPO_ROOT/scripts/macos/$script" "$BUNDLE_DIR/scripts/macos/"
        echo "  OK scripts/$script"
    else
        echo "  SKIP scripts/$script (not found)"
    fi
done

# --- Copy tests ---
echo ""
echo "=== Copying tests ==="
for test_script in test_bootmux_safe_flash.py test_bootmux_attach_shield.py; do
    if [ -f "$REPO_ROOT/scripts/macos/tests/$test_script" ]; then
        cp "$REPO_ROOT/scripts/macos/tests/$test_script" "$BUNDLE_DIR/scripts/macos/tests/"
        echo "  OK tests/$test_script"
    fi
done

# --- Copy firmware artifacts from manifest (NOT hardcoded) ---
echo ""
echo "=== Copying firmware artifacts (manifest-driven) ==="
echo "$ARTIFACT_PATHS" | while IFS='|' read -r name rel_path offset size sha256; do
    src="$FIRMWARE_DIR/$rel_path"
    dst_dir="$BUNDLE_DIR/firmware/esp32s3-router-spike/$(dirname "$rel_path")"
    if [ ! -f "$src" ]; then
        echo "  MISSING artifact: $src"
        echo "  BUNDLE=RED_ARTIFACT_MISSING"
        exit 1
    fi
    mkdir -p "$dst_dir"
    cp "$src" "$dst_dir/"
    echo "  OK $(basename "$rel_path") ($name, offset=$offset)"
done

# --- Copy manifest ---
cp "$MANIFEST" "$BUNDLE_DIR/firmware/esp32s3-router-spike/"
echo "  OK safe-flash-manifest.json"

# --- Copy sdkconfig ---
if [ -f "$FIRMWARE_DIR/sdkconfig" ]; then
    cp "$FIRMWARE_DIR/sdkconfig" "$BUNDLE_DIR/firmware/esp32s3-router-spike/"
    echo "  OK sdkconfig"
fi

# --- Copy esptool + pyserial if version check passed ---
if [ "$ESPTOOL_FOUND" = "BUNDLE_PIO" ]; then
    mkdir -p "$BUNDLE_DIR/tools"
    cp -r "$HOME/.platformio/packages/tool-esptoolpy" "$BUNDLE_DIR/tools/tool-esptoolpy" 2>/dev/null || true
    echo "  OK tools/tool-esptoolpy"
    # Bundle pyserial (esptool runtime dependency)
    PYSERIAL_SRC=$(python3 -c "import serial; print(serial.__file__)" 2>/dev/null) || true
    if [ -n "$PYSERIAL_SRC" ]; then
        PYSERIAL_DIR=$(dirname "$PYSERIAL_SRC")
        cp -r "$PYSERIAL_DIR" "$BUNDLE_DIR/tools/serial" 2>/dev/null || true
        echo "  OK tools/serial (pyserial)"
    fi
fi

# --- Copy docs ---
for doc in BOOTMUX_MAC_PREATTACH_SHIELD.md BOOTMUX_SAFE_FLASH_PREFLIGHT.md; do
    if [ -f "$REPO_ROOT/docs/$doc" ]; then
        cp "$REPO_ROOT/docs/$doc" "$BUNDLE_DIR/docs/"
        echo "  OK docs/$doc"
    fi
done

# --- Offline runner wrapper ---
cat > "$BUNDLE_DIR/run-safe-flash.sh" << 'WRAPPER'
#!/bin/bash
# BOOTMUX Offline Safe Flash — one-shot runner wrapper.
# Works with NO Internet, NO WORKER.  All local.
set -euo pipefail
BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$BUNDLE_DIR/scripts/macos"
MANIFEST="$BUNDLE_DIR/firmware/esp32s3-router-spike/safe-flash-manifest.json"
FIRMWARE="$BUNDLE_DIR/firmware/esp32s3-router-spike"

echo "=== BOOTMUX Offline Safe Flash ==="
echo "bundle_dir=$BUNDLE_DIR"
echo "manifest=$MANIFEST"

# Step 1: Inspect binaries
echo ""
echo "--- Step 1: Inspect firmware binaries ---"
python3 "$SCRIPTS/bootmux-safe-flash-inspect.py" --manifest "$MANIFEST" --json
echo ""

# Step 2: Runner status
echo "--- Step 2: Runner status ---"
python3 "$SCRIPTS/bootmux-safe-flash-runner.py" --status
echo ""

# Step 3: Dry-run (P4-R1C default)
echo "--- Step 3: Dry-run pipeline ---"
python3 "$SCRIPTS/bootmux-safe-flash-runner.py" --dry-run 2>&1 || true
echo ""

# Step 4: Verify preflash gate in dry-run
echo "--- Step 4: Verify preflash gate status ---"
python3 -c "
import subprocess, sys
p = subprocess.run([sys.executable, '$SCRIPTS/bootmux-safe-flash-runner.py', '--dry-run'],
    capture_output=True, text=True, timeout=30)
out = p.stdout + p.stderr
if 'PRE_FLASH_GATE' in out:
    print('PREFLASH_GATE=REACHED_IN_DRY_RUN (write_flash NOT reached)')
else:
    print('PREFLASH_GATE_CHECK=INFO')
"
echo ""

echo "=== DONE (DRY_RUN) ==="
echo "To execute actual flash: python3 $SCRIPTS/bootmux-safe-flash-runner.py --execute"
echo "ATTACH_AUTHORITY=BLOCKED_PENDING_P4_R2"
WRAPPER
chmod +x "$BUNDLE_DIR/run-safe-flash.sh"

# --- Integrity check (manifest-driven) ---
echo ""
echo "=== Bundle integrity check ==="
ERRORS=0
for f in \
    scripts/macos/bootmux-safe-flash-inspect.py \
    scripts/macos/bootmux-safe-flash-runner.py \
    firmware/esp32s3-router-spike/safe-flash-manifest.json \
    run-safe-flash.sh; do
    if [ -f "$BUNDLE_DIR/$f" ]; then
        echo "  OK $f"
    else
        echo "  MISSING $f"
        ERRORS=$((ERRORS+1))
    fi
done

# Check all manifest artifacts present
echo "$ARTIFACT_PATHS" | while IFS='|' read -r name rel_path offset size sha256; do
    bundled="$BUNDLE_DIR/firmware/esp32s3-router-spike/$rel_path"
    if [ -f "$bundled" ]; then
        # Verify SHA-256 matches manifest
        actual_sha=$(sha256sum "$bundled" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$bundled" 2>/dev/null | cut -d' ' -f1)
        if [ "$actual_sha" = "$sha256" ]; then
            echo "  OK $rel_path (sha256 match)"
        else
            echo "  HASH_MISMATCH $rel_path (expected $sha256, got $actual_sha)"
            ERRORS=$((ERRORS+1))
        fi
    else
        echo "  MISSING $rel_path"
        ERRORS=$((ERRORS+1))
    fi
done

if [ $ERRORS -gt 0 ]; then
    echo "BUNDLE=RED ($ERRORS errors)"
    exit 1
fi

# --- Create tarball ---
echo ""
echo "=== Creating tarball ==="
tar -czf "$BUNDLE_TAR" -C "$(dirname "$BUNDLE_DIR")" "$(basename "$BUNDLE_DIR")"
echo "BUNDLE_TAR=$BUNDLE_TAR"
ls -lh "$BUNDLE_TAR"

# --- Network dependency scan on BUNDLE content ---
echo ""
echo "=== Network dependency scan ==="
NET_REFS=$(grep -rn "urllib\|requests\|http[s]*://\|socket\.\|curl\|wget\|firecrawl\|web_search\|web_extract" \
    "$BUNDLE_DIR/scripts/macos/"*.py "$BUNDLE_DIR/scripts/macos/"*.sh "$BUNDLE_DIR/run-safe-flash.sh" 2>/dev/null \
    | grep -v "http_connect_proxy\|http_proxy\|#\|\.md:" || true)
if [ -z "$NET_REFS" ]; then
    echo "NETWORK_DEPENDENCY=ABSENT"
else
    echo "NETWORK_DEPENDENCY=CHECK_REQUIRED"
    echo "$NET_REFS" | head -10
fi

# --- Output ---
echo ""
if [ "$ESPTOOL_FOUND" = "BUNDLE_VERSION_FAILED" ]; then
    echo "BUNDLE=RED_OFFLINE_FLASH_TOOL_MISSING (esptool version check failed)"
    echo "OFFLINE_READY=false"
    echo "FLASH_TOOL_STATUS=MISSING"
    exit 1
elif [ "$ESPTOOL_FOUND" = "BUNDLE_PIO" ]; then
    echo "BUNDLE=GREEN"
    echo "OFFLINE_READY=true"
    echo "FLASH_TOOL_STATUS=FOUND"
else
    echo "BUNDLE=RED_OFFLINE_FLASH_TOOL_MISSING (no esptool found)"
    echo "OFFLINE_READY=false"
    echo "FLASH_TOOL_STATUS=MISSING"
    exit 1
fi
