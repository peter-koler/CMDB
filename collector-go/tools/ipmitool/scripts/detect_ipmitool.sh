#!/bin/bash

set -euo pipefail

BASE_DIR="${1:-}"
if [ -z "$BASE_DIR" ]; then
    echo ""
    exit 0
fi

BIN_DIR="$BASE_DIR/tools/ipmitool/bin"
OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"

tagged=""
case "$OS_NAME" in
    Darwin)
        tagged="$BIN_DIR/ipmitool-darwin-$ARCH_NAME"
        ;;
    Linux)
        tagged="$BIN_DIR/ipmitool-linux-$ARCH_NAME"
        ;;
    *)
        tagged=""
        ;;
esac

default_bin="$BIN_DIR/ipmitool"

if [ -n "$tagged" ] && [ -x "$tagged" ]; then
    echo "$tagged"
    exit 0
fi

if [ -x "$default_bin" ]; then
    echo "$default_bin"
    exit 0
fi

echo ""

