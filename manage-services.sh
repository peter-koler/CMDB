#!/bin/bash

# 监控服务管理脚本
# 用法: ./manage-services.sh [start|stop|restart|status] [all|manager|collector]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/Users/peter/Documents/arco"
MANAGER_DIR="$PROJECT_ROOT/manager-go"
COLLECTOR_DIR="$PROJECT_ROOT/collector-go"
MANAGER_CONFIG="${MANAGER_CONFIG:-$MANAGER_DIR/config/manager.yaml}"

# Go 编译缓存（避免某些环境下默认缓存目录无权限）
export GOCACHE="${GOCACHE:-/tmp/arco-go-build-cache}"
export GOMODCACHE="${GOMODCACHE:-/tmp/arco-go-mod-cache}"

# PID 文件
MANAGER_PID_FILE="/tmp/manager-go.pid"
COLLECTOR_PID_FILE="/tmp/collector-go.pid"

# 日志文件
MANAGER_LOG="/tmp/manager-go.log"
COLLECTOR_LOG="/tmp/collector-go.log"

# 显示帮助信息
show_help() {
    echo -e "${BLUE}监控服务管理脚本${NC}"
    echo ""
    echo "用法: $0 [命令] [服务]"
    echo ""
    echo "命令:"
    echo "  start     启动服务"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  status    查看服务状态"
    echo ""
    echo "服务:"
    echo "  all       所有服务（默认）"
    echo "  manager   仅 manager-go"
    echo "  collector 仅 collector-go"
    echo ""
    echo "示例:"
    echo "  $0 start all        # 启动所有服务"
    echo "  $0 stop manager     # 仅停止 manager"
    echo "  $0 restart          # 重启所有服务"
    echo "  $0 status           # 查看所有服务状态"
}

# 获取进程 PID
get_pid() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        cat "$pid_file" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# 检查进程是否运行
is_running() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 启动 manager-go
start_manager() {
    echo -e "${BLUE}正在启动 manager-go...${NC}"
    
    local pid=$(get_pid "$MANAGER_PID_FILE")
    if is_running "$pid"; then
        echo -e "${YELLOW}manager-go 已经在运行中 (PID: $pid)${NC}"
        return 0
    fi
    
    cd "$MANAGER_DIR"

    if [ ! -f "$MANAGER_CONFIG" ]; then
        echo -e "${RED}错误: manager 配置文件不存在: $MANAGER_CONFIG${NC}"
        return 1
    fi
    
    # 强制重新编译
    echo -e "${YELLOW}正在编译 manager-go...${NC}"
    if [ -f "./cmd/manager/main.go" ]; then
        go build -o manager-go ./cmd/manager
    else
        echo -e "${RED}错误: 未找到 manager-go 源代码${NC}"
        return 1
    fi
    
    echo -e "${BLUE}使用配置文件: $MANAGER_CONFIG${NC}"
    nohup ./manager-go -config "$MANAGER_CONFIG" > "$MANAGER_LOG" 2>&1 &
    
    local new_pid=$!
    echo $new_pid > "$MANAGER_PID_FILE"
    
    # 等待服务启动
    sleep 2
    if is_running "$new_pid"; then
        echo -e "${GREEN}manager-go 启动成功 (PID: $new_pid)${NC}"
        echo -e "${BLUE}日志文件: $MANAGER_LOG${NC}"
    else
        echo -e "${RED}manager-go 启动失败，请检查日志${NC}"
        rm -f "$MANAGER_PID_FILE"
        return 1
    fi
}

# 启动 collector-go
start_collector() {
    echo -e "${BLUE}正在启动 collector-go...${NC}"
    
    local pid=$(get_pid "$COLLECTOR_PID_FILE")
    if is_running "$pid"; then
        echo -e "${YELLOW}collector-go 已经在运行中 (PID: $pid)${NC}"
        return 0
    fi
    
    cd "$COLLECTOR_DIR"

    # IPMI 内置工具路径（默认不依赖系统 PATH）
    if [ -z "${COLLECTOR_IPMITOOL_BIN:-}" ]; then
        local detect_script="$COLLECTOR_DIR/tools/ipmitool/scripts/detect_ipmitool.sh"
        if [ -x "$detect_script" ]; then
            local detected_ipmi_bin
            detected_ipmi_bin="$("$detect_script" "$COLLECTOR_DIR" || true)"
            if [ -n "$detected_ipmi_bin" ]; then
                export COLLECTOR_IPMITOOL_BIN="$detected_ipmi_bin"
            else
                echo -e "${YELLOW}警告: 未发现内置 ipmitool，可在需要时设置 COLLECTOR_IPMITOOL_BIN${NC}"
            fi
        fi
    fi
    
    # 强制重新编译
    echo -e "${YELLOW}正在编译 collector-go...${NC}"
    if [ -f "./cmd/collector/main.go" ]; then
        local build_tags="${COLLECTOR_GO_BUILD_TAGS:-}"
        local build_args=()
        if [ -n "$build_tags" ]; then
            build_args=(-tags "$build_tags")
            echo -e "${BLUE}collector-go build tags: $build_tags${NC}"
        fi
        if [[ ",$build_tags," == *",db2,"* ]] || [[ " $build_tags " == *" db2 "* ]]; then
            if [ -z "${IBM_DB_HOME:-}" ]; then
                echo -e "${RED}错误: 已启用 db2 tag，但未设置 IBM_DB_HOME${NC}"
                echo -e "${YELLOW}请先安装 IBM clidriver 并设置: IBM_DB_HOME, CGO_CFLAGS, CGO_LDFLAGS, LD_LIBRARY_PATH/DYLD_LIBRARY_PATH${NC}"
                return 1
            fi
            if [ ! -f "${IBM_DB_HOME}/include/sqlcli1.h" ]; then
                echo -e "${RED}错误: 未找到 ${IBM_DB_HOME}/include/sqlcli1.h${NC}"
                echo -e "${YELLOW}请确认 IBM_DB_HOME 指向包含 include/sqlcli1.h 的 clidriver 目录${NC}"
                return 1
            fi
            if [ ! -f "${IBM_DB_HOME}/lib/libdb2.dylib" ] && [ ! -f "${IBM_DB_HOME}/lib/libdb2.so" ]; then
                echo -e "${RED}错误: 未找到 ${IBM_DB_HOME}/lib/libdb2.dylib 或 libdb2.so${NC}"
                echo -e "${YELLOW}请确认 clidriver lib 目录完整，并配置库搜索路径${NC}"
                return 1
            fi
        fi
        go build "${build_args[@]}" -o collector-go ./cmd/collector
    else
        echo -e "${RED}错误: 未找到 collector-go 源代码${NC}"
        return 1
    fi
    
    nohup ./collector-go > "$COLLECTOR_LOG" 2>&1 &
    
    local new_pid=$!
    echo $new_pid > "$COLLECTOR_PID_FILE"
    
    # 等待服务启动
    sleep 2
    if is_running "$new_pid"; then
        echo -e "${GREEN}collector-go 启动成功 (PID: $new_pid)${NC}"
        echo -e "${BLUE}日志文件: $COLLECTOR_LOG${NC}"
    else
        echo -e "${RED}collector-go 启动失败，请检查日志${NC}"
        rm -f "$COLLECTOR_PID_FILE"
        return 1
    fi
}

# 停止 manager-go
stop_manager() {
    echo -e "${BLUE}正在停止 manager-go...${NC}"
    
    local pid=$(get_pid "$MANAGER_PID_FILE")
    if [ -z "$pid" ]; then
        echo -e "${YELLOW}manager-go 未在运行${NC}"
        return 0
    fi
    
    if is_running "$pid"; then
        kill "$pid" 2>/dev/null
        # 等待进程结束
        local count=0
        while is_running "$pid" && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if is_running "$pid"; then
            echo -e "${YELLOW}强制终止 manager-go...${NC}"
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        echo -e "${GREEN}manager-go 已停止${NC}"
    else
        echo -e "${YELLOW}manager-go 进程已不存在${NC}"
    fi
    
    rm -f "$MANAGER_PID_FILE"
}

# 停止 collector-go
stop_collector() {
    echo -e "${BLUE}正在停止 collector-go...${NC}"
    
    local pid=$(get_pid "$COLLECTOR_PID_FILE")
    if [ -z "$pid" ]; then
        echo -e "${YELLOW}collector-go 未在运行${NC}"
        return 0
    fi
    
    if is_running "$pid"; then
        kill "$pid" 2>/dev/null
        # 等待进程结束
        local count=0
        while is_running "$pid" && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if is_running "$pid"; then
            echo -e "${YELLOW}强制终止 collector-go...${NC}"
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        echo -e "${GREEN}collector-go 已停止${NC}"
    else
        echo -e "${YELLOW}collector-go 进程已不存在${NC}"
    fi
    
    rm -f "$COLLECTOR_PID_FILE"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    local service=$2
    # 检查 lsof 命令是否存在
    if ! command -v lsof >/dev/null 2>&1; then
        echo -e "${YELLOW}警告: lsof 命令不存在，无法检查端口占用${NC}"
        return 2
    fi
    
    if lsof -i :$port >/dev/null 2>&1; then
        local pid=$(lsof -ti:$port 2>/dev/null || echo "未知")
        echo -e "${YELLOW}$service 端口 $port 被占用 (PID: $pid)${NC}"
        return 0
    else
        echo -e "${GREEN}$service 端口 $port 可用${NC}"
        return 1
    fi
}

# 检查进程详细信息
check_process_details() {
    local pid=$1
    local service=$2
    if [ -n "$pid" ] && is_running "$pid"; then
        # 获取进程详细信息
        local cmdline=$(ps -p "$pid" -o command= 2>/dev/null || echo "未知")
        local cpu=$(ps -p "$pid" -o %cpu= 2>/dev/null || echo "未知")
        local mem=$(ps -p "$pid" -o %mem= 2>/dev/null || echo "未知")
        local start_time=$(ps -p "$pid" -o lstart= 2>/dev/null || echo "未知")
        
        echo -e "${GREEN}$service 进程详情:${NC}"
        echo -e "  PID: $pid"
        echo -e "  启动时间: $start_time"
        echo -e "  CPU使用率: $cpu%"
        echo -e "  内存使用率: $mem%"
        echo -e "  命令行: $cmdline"
        
        # 检查端口占用情况
        case "$service" in
            "manager-go")
                check_port 8080 "manager-go"
                ;;
            "collector-go")
                check_port 8081 "collector-go"
                ;;
        esac
        return 0
    else
        echo -e "${RED}$service 进程不存在${NC}"
        return 1
    fi
}

# 检查单个服务状态
check_service_status() {
    local service_name=$1
    local pid_file=$2
    local log_file=$3
    local port=$4
    
    local pid=$(get_pid "$pid_file")
    
    echo -e "${BLUE}$service_name 状态:${NC}"
    
    if is_running "$pid"; then
        echo -e "  ${GREEN}运行中${NC} (PID: $pid)"
        echo -e "  日志文件: $log_file"
        
        # 获取进程详细信息
        local cmdline=$(ps -p "$pid" -o command= 2>/dev/null || echo "未知")
        local cpu=$(ps -p "$pid" -o %cpu= 2>/dev/null || echo "未知")
        local mem=$(ps -p "$pid" -o %mem= 2>/dev/null || echo "未知")
        local start_time=$(ps -p "$pid" -o lstart= 2>/dev/null || echo "未知")
        
        echo -e "  启动时间: $start_time"
        echo -e "  CPU使用率: $cpu%"
        echo -e "  内存使用率: $mem%"
        echo -e "  命令行: $cmdline"
        
        # 检查端口
        if command -v lsof >/dev/null 2>&1; then
            if lsof -i :$port >/dev/null 2>&1; then
                local port_pid=$(lsof -ti:$port 2>/dev/null || echo "未知")
                echo -e "  ${GREEN}端口 $port 被占用 (PID: $port_pid)${NC}"
            else
                echo -e "  ${YELLOW}端口 $port 可用${NC}"
            fi
        else
            echo -e "  ${YELLOW}警告: 无法检查端口占用 (lsof 命令不存在)${NC}"
        fi
    else
        echo -e "  ${RED}未运行${NC}"
        echo -e "  日志文件: $log_file"
        
        # 检查端口是否被其他进程占用
        if command -v lsof >/dev/null 2>&1; then
            if lsof -i :$port >/dev/null 2>&1; then
                local port_pid=$(lsof -ti:$port 2>/dev/null || echo "未知")
                echo -e "  ${YELLOW}端口 $port 被其他进程占用 (PID: $port_pid)${NC}"
            else
                echo -e "  ${GREEN}端口 $port 可用${NC}"
            fi
        else
            echo -e "  ${YELLOW}警告: 无法检查端口占用 (lsof 命令不存在)${NC}"
        fi
        
        [ -n "$pid" ] && rm -f "$pid_file"
    fi
    echo ""
}

# 查看状态
show_status() {
    echo -e "${BLUE}================ 服务状态 ================${NC}"
    echo ""
    
    # Manager 状态
    check_service_status "manager-go" "$MANAGER_PID_FILE" "$MANAGER_LOG" 8080
    
    # Collector 状态
    check_service_status "collector-go" "$COLLECTOR_PID_FILE" "$COLLECTOR_LOG" 8081
    
    echo -e "${BLUE}==========================================${NC}"
}

# 查看日志
show_logs() {
    local service=$1
    local lines=${2:-50}
    
    case "$service" in
        manager)
            if [ -f "$MANAGER_LOG" ]; then
                echo -e "${BLUE}manager-go 日志 (最后 $lines 行):${NC}"
                tail -n "$lines" "$MANAGER_LOG"
            else
                echo -e "${YELLOW}manager-go 日志文件不存在${NC}"
            fi
            ;;
        collector)
            if [ -f "$COLLECTOR_LOG" ]; then
                echo -e "${BLUE}collector-go 日志 (最后 $lines 行):${NC}"
                tail -n "$lines" "$COLLECTOR_LOG"
            else
                echo -e "${YELLOW}collector-go 日志文件不存在${NC}"
            fi
            ;;
        *)
            echo -e "${RED}用法: $0 logs [manager|collector] [行数]${NC}"
            ;;
    esac
}

# 主函数
main() {
    local command=${1:-help}
    local service=${2:-all}
    
    case "$command" in
        start)
            case "$service" in
                all)
                    start_manager
                    echo ""
                    start_collector
                    ;;
                manager)
                    start_manager
                    ;;
                collector)
                    start_collector
                    ;;
                *)
                    echo -e "${RED}错误: 未知服务 '$service'${NC}"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        stop)
            case "$service" in
                all)
                    stop_collector
                    echo ""
                    stop_manager
                    ;;
                manager)
                    stop_manager
                    ;;
                collector)
                    stop_collector
                    ;;
                *)
                    echo -e "${RED}错误: 未知服务 '$service'${NC}"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        restart)
            case "$service" in
                all)
                    stop_collector
                    stop_manager
                    echo ""
                    start_manager
                    echo ""
                    start_collector
                    ;;
                manager)
                    stop_manager
                    echo ""
                    start_manager
                    ;;
                collector)
                    stop_collector
                    echo ""
                    start_collector
                    ;;
                *)
                    echo -e "${RED}错误: 未知服务 '$service'${NC}"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$service" "$3"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}错误: 未知命令 '$command'${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
