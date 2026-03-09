#!/bin/bash

# Arco Manager 停止脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="logs/manager.pid"

echo "=================================="
echo "  Arco Manager Stopping..."
echo "=================================="

# 首先停止所有 manager-go 相关进程
echo "[INFO] Stopping all manager processes..."

# 查找并停止所有 manager-go 进程
MANAGER_PIDS=$(pgrep -f "manager-go" || true)
if [ -n "$MANAGER_PIDS" ]; then
    echo "[INFO] Found manager processes: $MANAGER_PIDS"
    echo "$MANAGER_PIDS" | while read -r pid; do
        if [ -n "$pid" ]; then
            echo "[INFO] Stopping process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done

    # 等待进程结束
    for i in {1..5}; do
        sleep 1
        REMAINING=$(pgrep -f "manager-go" || true)
        if [ -z "$REMAINING" ]; then
            break
        fi
        echo "[INFO] Waiting for processes to stop... ($i/5)"
    done

    # 强制停止剩余的进程
    REMAINING=$(pgrep -f "manager-go" || true)
    if [ -n "$REMAINING" ]; then
        echo "[WARN] Force killing remaining processes..."
        echo "$REMAINING" | while read -r pid; do
            if [ -n "$pid" ]; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
        done
    fi
fi

# 同时检查 PID 文件中的进程
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[INFO] Stopping PID from file: $PID"
        kill -TERM "$PID" 2>/dev/null || true
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -KILL "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
fi

# 清理 go run 产生的临时进程
GO_RUN_PIDS=$(pgrep -f "go-build.*manager" || true)
if [ -n "$GO_RUN_PIDS" ]; then
    echo "[INFO] Cleaning up go run processes..."
    echo "$GO_RUN_PIDS" | while read -r pid; do
        if [ -n "$pid" ]; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
fi

echo "[SUCCESS] All manager processes stopped"
