#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IPMI_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="$IPMI_ROOT/bin"
CHECKSUM_FILE="$IPMI_ROOT/checksums.sha256"

usage() {
    cat <<'EOF'
Usage:
  ./tools/ipmitool/scripts/verify.sh [--require-current]

Options:
  --require-current   Require current OS/ARCH binary to be present and executable.
EOF
}

require_current=0
while [ $# -gt 0 ]; do
    case "$1" in
        --require-current)
            require_current=1
            shift
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

if [ ! -d "$BIN_DIR" ]; then
    echo "ipmitool bin directory missing: $BIN_DIR" >&2
    exit 1
fi

found_any=0
for f in "$BIN_DIR"/*; do
    [ -f "$f" ] || continue
    found_any=1
    if [ ! -x "$f" ]; then
        echo "binary is not executable: $f" >&2
        exit 1
    fi
done

if [ "$found_any" -eq 0 ]; then
    echo "no ipmitool binaries found in: $BIN_DIR" >&2
    exit 1
fi

if [ -f "$CHECKSUM_FILE" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
        (cd "$BIN_DIR" && sha256sum -c "$CHECKSUM_FILE")
    elif command -v shasum >/dev/null 2>&1; then
        (cd "$BIN_DIR" && shasum -a 256 -c "$CHECKSUM_FILE")
    else
        echo "sha256sum/shasum not found, skip checksum validation"
    fi
else
    echo "checksum file not found, skipped: $CHECKSUM_FILE"
fi

if [ "$require_current" -eq 1 ]; then
    os_name="$(uname -s)"
    arch_name="$(uname -m)"
    case "$os_name" in
        Darwin)
            cur="$BIN_DIR/ipmitool-darwin-$arch_name"
            ;;
        Linux)
            cur="$BIN_DIR/ipmitool-linux-$arch_name"
            ;;
        *)
            cur="$BIN_DIR/ipmitool"
            ;;
    esac
    if [ ! -x "$cur" ]; then
        echo "current platform binary missing: $cur" >&2
        exit 1
    fi
fi

echo "[OK] ipmitool bundle verification passed"

