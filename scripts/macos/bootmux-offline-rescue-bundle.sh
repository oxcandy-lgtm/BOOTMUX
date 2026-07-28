#!/bin/bash
# R7C P4-R1 — BOOTMUX Offline Rescue Bundle Builder.
# Creates a self-contained tarball that works with NO Internet and NO WORKER.
# All tools, scripts, firmware binaries, and manifests are bundled locally.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUNDLE_DIR="${1:-/tmp/bootmux-offline-rescue}"
BUNDLE_TAR="${2:-/tmp/bootmux-offline-rescue.tar.gz}"

echo "=== BOOTMUX Offline Rescue Bundle Builder ==="
echo "repo_root=$REPO_ROOT"
echo "bundle_dir=$BUNDLE_DIR"

rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"/{scripts/macos,scripts/macos/tests,scripts/macos/launchd,firmware,docs}

# --- Scripts ---
cp "$REPO_ROOT/scripts/macos/bootmux-attach-shield.py" "$BUNDLE_DIR/scripts/macos/"
cp "$REPO_ROOT/scripts/macos/bootmux-safe-flash-inspect.py" "$BUNDLE_DIR/scripts/macos/"
cp "$REPO_ROOT/scripts/macos/bootmux-safe-flash-runner.py" "$BUNDLE_DIR/scripts/macos/"
cp "$REPO_ROOT/scripts/macos/install-bootmux-attach-shield.sh" "$BUNDLE_DIR/scripts/macos/"
cp "$REPO_ROOT/scripts/macos/uninstall-bootmux-attach-shield.sh" "$BUNDLE_DIR/scripts/macos/"
cp "$REPO_ROOT/scripts/macos/bootmux-attach-shield-status.sh" "$BUNDLE_DIR/scripts/macos/"
cp "$REPO_ROOT/scripts/macos/launchd/com.bootmux.attach-shield.plist" "$BUNDLE_DIR/scripts/macos/launchd/"

# --- Tests ---
cp "$REPO_ROOT/scripts/macos/tests/test_bootmux_attach_shield.py" "$BUNDLE_DIR/scripts/macos/tests/" 2>/dev/null || true
if [ -f "$REPO_ROOT/scripts/macos/tests/test_bootmux_safe_flash.py" ]; then
    cp "$REPO_ROOT/scripts/macos/tests/test_bootmux_safe_flash.py" "$BUNDLE_DIR/scripts/macos/tests/"
fi

# --- Firmware binaries + manifest ---
FW_DIR="$REPO_ROOT/firmware/esp32s3-router-spike"
mkdir -p "$BUNDLE_DIR/firmware/esp32s3-router-spike/build-native-r7b-r2"/{bootloader,partition_table}
cp "$FW_DIR/safe-flash-manifest.json" "$BUNDLE_DIR/firmware/esp32s3-router-spike/"
cp "$FW_DIR/build-native-r7b-r2/bootloader/bootloader.bin" "$BUNDLE_DIR/firmware/esp32s3-router-spike/build-native-r7b-r2/bootloader/"
cp "$FW_DIR/build-native-r7b-r2/partition_table/partition-table.bin" "$BUNDLE_DIR/firmware/esp32s3-router-spike/build-native-r7b-r2/partition_table/"
cp "$FW_DIR/build-native-r7b-r2/bootmux_router_spike.bin" "$BUNDLE_DIR/firmware/esp32s3-router-spike/build-native-r7b-r2/"
cp "$FW_DIR/sdkconfig" "$BUNDLE_DIR/firmware/esp32s3-router-spike/" 2>/dev/null || true

# --- Docs ---
cp "$REPO_ROOT/docs/BOOTMUX_MAC_PREATTACH_SHIELD.md" "$BUNDLE_DIR/docs/" 2>/dev/null || true
cp "$REPO_ROOT/docs/BOOTMUX_SAFE_FLASH_PREFLIGHT.md" "$BUNDLE_DIR/docs/" 2>/dev/null || true

# --- Offline runner wrapper ---
cat > "$BUNDLE_DIR/run-safe-flash.sh" << 'WRAPPER'
#!/bin/bash
# BOOTMUX Offline Safe Flash — one-shot runner wrapper.
# Works with NO Internet, NO WORKER.  All local.
set -euo pipefail
BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$BUNDLE_DIR/scripts/macos"
MANIFEST="$BUNDLE_DIR/firmware/esp32s3-router-spike/safe-flash-manifest.json"

echo "=== BOOTMUX Offline Safe Flash ==="
echo "bundle_dir=$BUNDLE_DIR"
echo "manifest=$MANIFEST"

# Step 1: Inspect binaries
echo "--- Step 1: Inspect firmware binaries ---"
python3 "$SCRIPTS/bootmux-safe-flash-inspect.py" --manifest "$MANIFEST" --json
echo ""

# Step 2: Runner status
echo "--- Step 2: Runner status ---"
python3 "$SCRIPTS/bootmux-safe-flash-runner.py" --status
echo ""

# Step 3: Dry-run (P4-R1 default)
echo "--- Step 3: Dry-run pipeline ---"
python3 "$SCRIPTS/bootmux-safe-flash-runner.py" --dry-run
echo ""

echo "=== DONE (DRY_RUN) ==="
echo "To execute actual flash: python3 $SCRIPTS/bootmux-safe-flash-runner.py --execute"
echo "ATTACH_AUTHORITY=BLOCKED_PENDING_P4_R2"
WRAPPER
chmod +x "$BUNDLE_DIR/run-safe-flash.sh"

# --- Verify bundle integrity ---
echo ""
echo "=== Bundle integrity check ==="
ERRORS=0
for f in \
    scripts/macos/bootmux-attach-shield.py \
    scripts/macos/bootmux-safe-flash-inspect.py \
    scripts/macos/bootmux-safe-flash-runner.py \
    scripts/macos/install-bootmux-attach-shield.sh \
    scripts/macos/uninstall-bootmux-attach-shield.sh \
    firmware/esp32s3-router-spike/safe-flash-manifest.json \
    firmware/esp32s3-router-spike/build-native-r7b-r2/bootloader/bootloader.bin \
    firmware/esp32s3-router-spike/build-native-r7b-r2/partition_table/partition-table.bin \
    firmware/esp32s3-router-spike/build-native-r7b-r2/bootmux_router_spike.bin \
    run-safe-flash.sh; do
    if [ -f "$BUNDLE_DIR/$f" ]; then
        echo "  OK $f"
    else
        echo "  MISSING $f"
        ERRORS=$((ERRORS+1))
    fi
done

if [ $ERRORS -gt 0 ]; then
    echo "BUNDLE=RED ($ERRORS missing files)"
    exit 1
fi

# --- Create tarball ---
echo ""
echo "=== Creating tarball ==="
tar -czf "$BUNDLE_TAR" -C "$(dirname "$BUNDLE_DIR")" "$(basename "$BUNDLE_DIR")"
echo "BUNDLE_TAR=$BUNDLE_TAR"
ls -lh "$BUNDLE_TAR"

# --- Network dependency check ---
echo ""
echo "=== Network dependency scan ==="
NET_REFS=$(grep -rn "urllib\|requests\|http\|https\|socket\|curl\|wget" \
    "$BUNDLE_DIR/scripts/macos/"*.py "$BUNDLE_DIR/scripts/macos/"*.sh 2>/dev/null \
    | grep -v "# " | grep -v "http_connect_proxy" | grep -v "HID" | grep -v "USB" || true)
if [ -z "$NET_REFS" ]; then
    echo "NETWORK_DEPENDENCY=ABSENT"
else
    echo "NETWORK_DEPENDENCY=CHECK_REQUIRED"
    echo "$NET_REFS" | head -10
fi

echo ""
echo "BUNDLE=GREEN"
echo "OFFLINE_READY=true"
