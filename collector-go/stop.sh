#!/bin/bash

# Arco Collector 停止脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="logs/collector.pid"

echo "=================================="
echo "  Arco Collector Stopping..."
echo "=================================="

if [ ! -f "$PID_FILE" ]; then
    echo "[WARN] PID file not found: $PID_FILE"
    echo "[INFO] Collector may not be running"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "[WARN] Process $PID is not running"
    rm -f "$PID_FILE"
    exit 0
fi

echo "[INFO] Stopping Collector (PID: $PID)..."

# 尝试优雅停止
kill -TERM "$PID" 2>/dev/null || true

# 等待进程结束
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "[SUCCESS] Collector stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi
    echo "[INFO] Waiting for shutdown... ($i/10)"
    sleep 1
done

# 强制停止
echo "[WARN] Force killing process..."
kill -KILL "$PID" 2>/dev/null || true
sleep 1

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "[SUCCESS] Collector stopped"
    rm -f "$PID_FILE"
else
    echo "[ERROR] Failed to stop Collector"
    exit 1
fi
