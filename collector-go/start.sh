#!/bin/bash

# Arco Collector 启动脚本
# 用法: ./start.sh [config_path]

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Go 编译缓存（避免某些环境下默认缓存目录无权限）
export GOCACHE="${GOCACHE:-/tmp/arco-collector-go-build-cache}"
export GOMODCACHE="${GOMODCACHE:-/tmp/arco-collector-go-mod-cache}"

# IPMI 内置工具路径（商用部署默认不依赖系统 PATH）
if [ -z "${COLLECTOR_IPMITOOL_BIN:-}" ]; then
    IPMI_DETECT_SCRIPT="$SCRIPT_DIR/tools/ipmitool/scripts/detect_ipmitool.sh"
    if [ -x "$IPMI_DETECT_SCRIPT" ]; then
        DETECTED_IPMI_BIN="$("$IPMI_DETECT_SCRIPT" "$SCRIPT_DIR" || true)"
        if [ -n "$DETECTED_IPMI_BIN" ]; then
            export COLLECTOR_IPMITOOL_BIN="$DETECTED_IPMI_BIN"
        else
            echo "[WARN] No bundled ipmitool detected under tools/ipmitool/bin"
        fi
    fi
fi

# 默认配置文件路径
CONFIG_PATH="${1:-config/collector.json}"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_PATH" ]; then
    echo "[WARN] Config file not found: $CONFIG_PATH"
    echo "[INFO] Using default configuration"
    CONFIG_PATH=""
fi

# 创建日志目录
mkdir -p logs

# 日志文件
LOG_FILE="logs/collector_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="logs/collector.pid"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[ERROR] Collector is already running (PID: $PID)"
        echo "[INFO] Use ./stop.sh to stop it first"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

echo "=================================="
echo "  Arco Collector Starting..."
echo "=================================="
echo "[INFO] Script directory: $SCRIPT_DIR"
echo "[INFO] Config path: ${CONFIG_PATH:-<default>}"
echo "[INFO] Log file: $LOG_FILE"

# 检查 Go 环境
if ! command -v go &> /dev/null; then
    echo "[ERROR] Go is not installed or not in PATH"
    exit 1
fi

# 每次启动前重新编译
BINARY="./collector"
echo "[INFO] Building collector..."
BUILD_TAGS="${COLLECTOR_GO_BUILD_TAGS:-}"
BUILD_ARGS=()
if [ -n "$BUILD_TAGS" ]; then
    BUILD_ARGS=(-tags "$BUILD_TAGS")
    echo "[INFO] collector build tags: $BUILD_TAGS"
fi
if [[ ",$BUILD_TAGS," == *",db2,"* ]] || [[ " $BUILD_TAGS " == *" db2 "* ]]; then
    if [ -z "${IBM_DB_HOME:-}" ]; then
        echo "[ERROR] db2 tag enabled but IBM_DB_HOME is empty"
        echo "[INFO] Please set IBM_DB_HOME, CGO_CFLAGS, CGO_LDFLAGS and library path env before build"
        exit 1
    fi
    if [ ! -f "${IBM_DB_HOME}/include/sqlcli1.h" ]; then
        echo "[ERROR] Missing ${IBM_DB_HOME}/include/sqlcli1.h"
        echo "[INFO] IBM_DB_HOME should point to clidriver root directory"
        exit 1
    fi
    if [ ! -f "${IBM_DB_HOME}/lib/libdb2.dylib" ] && [ ! -f "${IBM_DB_HOME}/lib/libdb2.so" ]; then
        echo "[ERROR] Missing libdb2 under ${IBM_DB_HOME}/lib"
        echo "[INFO] Please ensure clidriver lib files are complete and library path env is set"
        exit 1
    fi
fi
go build "${BUILD_ARGS[@]}" -o "$BINARY" ./cmd/collector
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

echo "[INFO] Collector started with PID: $PID"
echo "[INFO] Waiting for startup..."

# 等待启动
sleep 2

# 检查进程是否还在运行
if ps -p "$PID" > /dev/null 2>&1; then
    echo "[SUCCESS] Collector is running!"
    echo "[INFO] PID: $PID"
    echo "[INFO] Log: tail -f $LOG_FILE"
    echo ""
    echo "Commands:"
    echo "  tail -f $LOG_FILE    # 查看日志"
    echo "  ./stop.sh            # 停止服务"
else
    echo "[ERROR] Collector failed to start"
    echo "[INFO] Check log: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
