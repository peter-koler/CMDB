#!/bin/bash

# =============================================================================
# 一键重启 Manager 和 Collector 服务脚本
# 启动顺序: 先 Manager，后 Collector
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 服务配置
MANAGER_NAME="manager-go"
COLLECTOR_NAME="collector-go"
MANAGER_PORT="8080"
COLLECTOR_PORT="50051"
MANAGER_GRPC_PORT="50050"

# 启动等待时间（秒）
MANAGER_START_WAIT=3
COLLECTOR_START_WAIT=2

# =============================================================================
# 函数定义
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查进程是否在运行
check_process() {
    local name=$1
    pgrep -f "$name" > /dev/null 2>&1
}

# 获取进程 PID
get_pid() {
    local name=$1
    pgrep -f "$name" | head -1
}

# 停止服务
stop_service() {
    local name=$1
    local display_name=$2
    
    log_info "正在停止 $display_name..."
    
    if check_process "$name"; then
        local pid=$(get_pid "$name")
        log_warn "找到 $display_name 进程 (PID: $pid)，正在终止..."
        
        # 先尝试优雅终止
        kill "$pid" 2>/dev/null || true
        
        # 等待进程结束
        local count=0
        while check_process "$name" && [ $count -lt 10 ]; do
            sleep 0.5
            count=$((count + 1))
        done
        
        # 如果还在运行，强制终止
        if check_process "$name"; then
            log_warn "$display_name 未响应，强制终止..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
        
        if check_process "$name"; then
            log_error "$display_name 停止失败"
            return 1
        else
            log_success "$display_name 已停止"
        fi
    else
        log_warn "$display_name 未在运行"
    fi
}

# 等待端口就绪
wait_for_port() {
    local port=$1
    local service=$2
    local max_wait=${3:-30}
    
    log_info "等待 $service 端口 $port 就绪..."
    
    local count=0
    while [ $count -lt $max_wait ]; do
        if lsof -i :"$port" > /dev/null 2>&1; then
            log_success "$service 端口 $port 已就绪"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo
    
    log_error "$service 端口 $port 在 ${max_wait} 秒内未就绪"
    return 1
}

# 编译 Manager
build_manager() {
    log_info "========================================"
    log_info "编译 Manager..."
    log_info "========================================"
    
    cd "$PROJECT_ROOT/manager-go"
    
    if ! command -v go &> /dev/null; then
        log_error "Go 未安装，无法编译 Manager"
        return 1
    fi
    
    # 删除旧的可执行文件
    rm -f ./manager-go ./manager
    
    # 编译
    if go build -o manager-go ./cmd/manager/; then
        log_success "Manager 编译完成"
        return 0
    else
        log_error "Manager 编译失败"
        return 1
    fi
}

# 启动 Manager
start_manager() {
    log_info "========================================"
    log_info "启动 Manager 服务..."
    log_info "========================================"
    
    cd "$PROJECT_ROOT/manager-go"
    
    # 先编译
    if ! build_manager; then
        return 1
    fi
    
    # 启动 Manager
    local manager_bin="./manager-go"
    
    log_info "执行: $manager_bin"
    nohup "$manager_bin" > "$PROJECT_ROOT/logs/manager.log" 2>&1 &
    
    # 等待启动
    sleep $MANAGER_START_WAIT
    
    if wait_for_port "$MANAGER_PORT" "Manager HTTP" 10; then
        log_success "Manager 服务启动成功"
        log_info "  - HTTP API: http://localhost:$MANAGER_PORT"
        log_info "  - gRPC: localhost:$MANAGER_GRPC_PORT"
        return 0
    else
        log_error "Manager 服务启动失败"
        log_error "请检查日志: $PROJECT_ROOT/logs/manager.log"
        return 1
    fi
}

# 编译 Collector
build_collector() {
    log_info "========================================"
    log_info "编译 Collector..."
    log_info "========================================"
    
    cd "$PROJECT_ROOT/collector-go"
    
    if ! command -v go &> /dev/null; then
        log_error "Go 未安装，无法编译 Collector"
        return 1
    fi
    
    # 删除旧的可执行文件
    rm -f ./collector-go ./collector
    
    # 编译
    if go build -o collector-go ./cmd/collector/; then
        log_success "Collector 编译完成"
        return 0
    else
        log_error "Collector 编译失败"
        return 1
    fi
}

# 启动 Collector
start_collector() {
    log_info "========================================"
    log_info "启动 Collector 服务..."
    log_info "========================================"
    
    cd "$PROJECT_ROOT/collector-go"
    
    # 先编译
    if ! build_collector; then
        return 1
    fi
    
    # 启动 Collector
    local collector_bin="./collector-go"
    
    log_info "执行: $collector_bin"
    nohup "$collector_bin" > "$PROJECT_ROOT/logs/collector.log" 2>&1 &
    
    # 等待启动
    sleep $COLLECTOR_START_WAIT
    
    if wait_for_port "$COLLECTOR_PORT" "Collector gRPC" 10; then
        log_success "Collector 服务启动成功"
        log_info "  - gRPC: localhost:$COLLECTOR_PORT"
        return 0
    else
        log_error "Collector 服务启动失败"
        log_error "请检查日志: $PROJECT_ROOT/logs/collector.log"
        return 1
    fi
}

# 显示状态
show_status() {
    log_info "========================================"
    log_info "服务状态检查"
    log_info "========================================"
    
    if check_process "$MANAGER_NAME"; then
        local pid=$(get_pid "$MANAGER_NAME")
        log_success "Manager 运行中 (PID: $pid)"
    else
        log_error "Manager 未运行"
    fi
    
    if check_process "$COLLECTOR_NAME"; then
        local pid=$(get_pid "$COLLECTOR_NAME")
        log_success "Collector 运行中 (PID: $pid)"
    else
        log_error "Collector 未运行"
    fi
}

# =============================================================================
# 主流程
# =============================================================================

main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           IT Ops Platform - 服务重启脚本                      ║"
    echo "║           Manager & Collector Restart Script                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    log_info "项目目录: $PROJECT_ROOT"
    
    # 创建日志目录
    mkdir -p "$PROJECT_ROOT/logs"
    
    # 记录启动时间
    echo "=== 重启时间: $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$PROJECT_ROOT/logs/manager.log"
    echo "=== 重启时间: $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$PROJECT_ROOT/logs/collector.log"
    
    # Step 1: 停止服务
    log_info "========================================"
    log_info "步骤 1/4: 停止现有服务"
    log_info "========================================"
    
    stop_service "$COLLECTOR_NAME" "Collector"
    stop_service "$MANAGER_NAME" "Manager"
    
    echo
    
    # Step 2: 启动 Manager
    log_info "========================================"
    log_info "步骤 2/4: 启动 Manager"
    log_info "========================================"
    
    if ! start_manager; then
        log_error "Manager 启动失败，停止后续操作"
        show_status
        exit 1
    fi
    
    echo
    
    # Step 3: 启动 Collector
    log_info "========================================"
    log_info "步骤 3/4: 启动 Collector"
    log_info "========================================"
    
    if ! start_collector; then
        log_error "Collector 启动失败"
        show_status
        exit 1
    fi
    
    echo
    
    # Step 4: 状态检查
    log_info "========================================"
    log_info "步骤 4/4: 服务状态检查"
    log_info "========================================"
    
    sleep 2
    show_status
    
    echo
    log_success "所有服务重启完成！"
    log_info "日志文件:"
    log_info "  - Manager:  $PROJECT_ROOT/logs/manager.log"
    log_info "  - Collector: $PROJECT_ROOT/logs/collector.log"
    
    return 0
}

# 处理中断信号
trap 'log_error "脚本被中断"; exit 1' INT TERM

# 执行主流程
main "$@"
