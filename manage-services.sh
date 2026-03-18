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
    
    # 检查可执行文件
    if [ -f "./manager-go" ]; then
        nohup ./manager-go > "$MANAGER_LOG" 2>&1 &
    elif [ -f "./cmd/manager/main.go" ]; then
        echo -e "${YELLOW}未找到编译后的二进制文件，尝试编译...${NC}"
        go build -o manager-go ./cmd/manager/main.go
        nohup ./manager-go > "$MANAGER_LOG" 2>&1 &
    else
        echo -e "${RED}错误: 未找到 manager-go 可执行文件或源代码${NC}"
        return 1
    fi
    
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
    
    # 检查可执行文件
    if [ -f "./collector-go" ]; then
        nohup ./collector-go > "$COLLECTOR_LOG" 2>&1 &
    elif [ -f "./cmd/collector/main.go" ]; then
        echo -e "${YELLOW}未找到编译后的二进制文件，尝试编译...${NC}"
        go build -o collector-go ./cmd/collector/main.go
        nohup ./collector-go > "$COLLECTOR_LOG" 2>&1 &
    else
        echo -e "${RED}错误: 未找到 collector-go 可执行文件或源代码${NC}"
        return 1
    fi
    
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

# 查看状态
show_status() {
    echo -e "${BLUE}================ 服务状态 ================${NC}"
    echo ""
    
    # Manager 状态
    local manager_pid=$(get_pid "$MANAGER_PID_FILE")
    if is_running "$manager_pid"; then
        echo -e "manager-go: ${GREEN}运行中${NC} (PID: $manager_pid)"
        echo -e "  日志: $MANAGER_LOG"
    else
        echo -e "manager-go: ${RED}未运行${NC}"
        [ -n "$manager_pid" ] && rm -f "$MANAGER_PID_FILE"
    fi
    
    echo ""
    
    # Collector 状态
    local collector_pid=$(get_pid "$COLLECTOR_PID_FILE")
    if is_running "$collector_pid"; then
        echo -e "collector-go: ${GREEN}运行中${NC} (PID: $collector_pid)"
        echo -e "  日志: $COLLECTOR_LOG"
    else
        echo -e "collector-go: ${RED}未运行${NC}"
        [ -n "$collector_pid" ] && rm -f "$COLLECTOR_PID_FILE"
    fi
    
    echo ""
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
