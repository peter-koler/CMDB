#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IPMI_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="$IPMI_ROOT/bin"
CHECKSUM_FILE="$IPMI_ROOT/checksums.sha256"

SOURCE_DIR=""

usage() {
    cat <<'EOF'
Usage:
  ./tools/ipmitool/scripts/install.sh --source <artifact_dir>

Expected artifact file names (copy as-is):
  ipmitool-linux-amd64
  ipmitool-linux-arm64
  ipmitool-darwin-amd64
  ipmitool-darwin-arm64
  ipmitool.exe
  ipmitool-windows-amd64.exe
  ipmitool-windows-arm64.exe
EOF
}

detect_sha256_cmd() {
    if command -v sha256sum >/dev/null 2>&1; then
        echo "sha256sum"
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        echo "shasum -a 256"
        return 0
    fi
    return 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --source)
            SOURCE_DIR="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "$SOURCE_DIR" ]; then
    echo "--source is required" >&2
    usage
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "source directory not found: $SOURCE_DIR" >&2
    exit 1
fi

mkdir -p "$BIN_DIR"

copied=0
for name in \
    ipmitool-linux-amd64 \
    ipmitool-linux-arm64 \
    ipmitool-darwin-amd64 \
    ipmitool-darwin-arm64 \
    ipmitool \
    ipmitool.exe \
    ipmitool-windows-amd64.exe \
    ipmitool-windows-arm64.exe
do
    src="$SOURCE_DIR/$name"
    dst="$BIN_DIR/$name"
    if [ -f "$src" ]; then
        cp "$src" "$dst"
        chmod +x "$dst" || true
        copied=$((copied + 1))
        echo "[OK] installed $name"
    fi
done

if [ "$copied" -eq 0 ]; then
    echo "no ipmitool artifacts copied from: $SOURCE_DIR" >&2
    exit 1
fi

sha_cmd="$(detect_sha256_cmd || true)"
if [ -z "$sha_cmd" ]; then
    echo "sha256sum/shasum not found, skip checksum generation"
    exit 0
fi

(
    cd "$BIN_DIR"
    rm -f "$CHECKSUM_FILE"
    for f in *; do
        [ -f "$f" ] || continue
        eval "$sha_cmd \"\$f\"" >> "$CHECKSUM_FILE"
    done
)

echo "[OK] checksum file generated: $CHECKSUM_FILE"

