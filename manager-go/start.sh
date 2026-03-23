#!/bin/bash

# Arco Manager 启动脚本
# 用法: ./start.sh [config_path]

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Go 编译缓存（避免某些环境下默认缓存目录无权限）
export GOCACHE="${GOCACHE:-/tmp/arco-manager-go-build-cache}"
export GOMODCACHE="${GOMODCACHE:-/tmp/arco-manager-go-mod-cache}"

# 默认配置文件路径
CONFIG_PATH="${1:-config/manager.yaml}"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_PATH" ]; then
    echo "[WARN] Config file not found: $CONFIG_PATH"
    echo "[INFO] Using default configuration"
    CONFIG_PATH=""
fi

# 创建日志目录
mkdir -p logs

# 日志文件
LOG_FILE="logs/manager_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="logs/manager.pid"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[ERROR] Manager is already running (PID: $PID)"
        echo "[INFO] Use ./stop.sh to stop it first"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

echo "=================================="
echo "  Arco Manager Starting..."
echo "=================================="
echo "[INFO] Script directory: $SCRIPT_DIR"
echo "[INFO] Config path: ${CONFIG_PATH:-<default>}"
echo "[INFO] Log file: $LOG_FILE"

# 输出配置摘要（脱敏）
if [ -n "$CONFIG_PATH" ] && [ -f "$CONFIG_PATH" ]; then
    MASK_DSN() {
        local dsn="$1"
        if [[ -z "$dsn" ]]; then
            echo "<empty>"
            return
        fi
        if [[ "$dsn" == *"://"* ]]; then
            # 脱敏 user:pass@ 部分
            echo "$dsn" | sed -E 's#(.*://)[^@]*@#\1***@#'
            return
        fi
        echo "$dsn"
    }

    CFG_MANAGER_ADDR=$(grep -E '^[[:space:]]*manager_addr:' "$CONFIG_PATH" | head -n1 | cut -d: -f2- | sed 's/#.*//' | xargs)
    CFG_DB_URL=$(grep -E '^[[:space:]]*manager_database_url:' "$CONFIG_PATH" | head -n1 | cut -d: -f2- | sed 's/#.*//' | sed 's/^ *//;s/ *$//' | sed 's/^"//;s/"$//;s/^'\''//;s/'\''$//')
    CFG_REDIS=$(grep -E '^[[:space:]]*redis_addr:' "$CONFIG_PATH" | head -n1 | cut -d: -f2- | sed 's/#.*//' | xargs)
    CFG_VM=$(grep -E '^[[:space:]]*victoria_metrics_url:' "$CONFIG_PATH" | head -n1 | cut -d: -f2- | sed 's/#.*//' | xargs)

    echo "[INFO] Config summary:"
    echo "       manager_addr: ${CFG_MANAGER_ADDR:-<env/default>}"
    echo "       manager_database_url: $(MASK_DSN "$CFG_DB_URL")"
    echo "       redis_addr: ${CFG_REDIS:-<env/default>}"
    echo "       victoria_metrics_url: ${CFG_VM:-<env/default>}"
fi

# 检查 Go 环境
if ! command -v go &> /dev/null; then
    echo "[ERROR] Go is not installed or not in PATH"
    exit 1
fi

# 每次启动前重新编译
BINARY="./manager"
echo "[INFO] Building manager..."
go build -o "$BINARY" ./cmd/manager
if [ ! -f "$BINARY" ]; then
    echo "[ERROR] Build failed"
    exit 1
fi
echo "[INFO] Build successful: $BINARY"

# 使用编译后的二进制启动
if [ -n "$CONFIG_PATH" ]; then
    nohup "$BINARY" -config "$CONFIG_PATH" > "$LOG_FILE" 2>&1 &
else
    nohup "$BINARY" > "$LOG_FILE" 2>&1 &
fi

# 保存 PID
PID=$!
echo $PID > "$PID_FILE"

echo "[INFO] Manager started with PID: $PID"
echo "[INFO] Waiting for startup..."

# 等待启动
sleep 2

# 检查进程是否还在运行
if ps -p "$PID" > /dev/null 2>&1; then
    echo "[SUCCESS] Manager is running!"
    echo "[INFO] PID: $PID"
    echo "[INFO] Log: tail -f $LOG_FILE"
    echo ""
    echo "Commands:"
    echo "  tail -f $LOG_FILE    # 查看日志"
    echo "  ./stop.sh            # 停止服务"
else
    echo "[ERROR] Manager failed to start"
    echo "[INFO] Check log: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
