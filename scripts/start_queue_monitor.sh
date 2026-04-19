#!/bin/bash
# Athena队列监控系统启动脚本
# 优先级P0修复 - 短期监控部署

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

CONFIG_FILE="${1:-scripts/queue_monitor_config.yaml}"
LOG_DIR="$PROJECT_ROOT/logs"
MONITOR_SCRIPT="$PROJECT_ROOT/scripts/queue_monitor.py"
PID_FILE="$LOG_DIR/queue_monitor.pid"
LOG_FILE="$LOG_DIR/queue_monitor_daemon.log"

# 检查依赖
check_dependencies() {
    echo "🔍 检查依赖..."

    # 检查Python3
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 未安装"
        exit 1
    fi

    # 检查PyYAML
    if ! python3 -c "import yaml" &> /dev/null; then
        echo "❌ PyYAML 未安装，尝试安装..."
        pip3 install pyyaml || {
            echo "❌ 安装PyYAML失败"
            exit 1
        }
    fi

    # 检查psutil
    if ! python3 -c "import psutil" &> /dev/null; then
        echo "❌ psutil 未安装，尝试安装..."
        pip3 install psutil || {
            echo "❌ 安装psutil失败"
            exit 1
        }
    fi

    # 检查requests
    if ! python3 -c "import requests" &> /dev/null; then
        echo "❌ requests 未安装，尝试安装..."
        pip3 install requests || {
            echo "❌ 安装requests失败"
            exit 1
        }
    fi

    echo "✅ 依赖检查完成"
}

# 检查配置文件
check_config() {
    echo "🔍 检查配置文件..."

    if [ ! -f "$CONFIG_FILE" ]; then
        echo "⚠️ 配置文件不存在: $CONFIG_FILE"
        echo "   使用默认配置运行"
        return 1
    fi

    # 验证YAML语法
    if python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE', 'r') as f:
        yaml.safe_load(f)
    print('✅ 配置文件语法正确')
except Exception as e:
    print(f'❌ 配置文件语法错误: {e}')
    sys.exit(1)
"; then
        echo "✅ 配置文件检查完成"
    else
        exit 1
    fi
}

# 创建日志目录
create_log_dir() {
    echo "📁 创建日志目录..."

    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        echo "✅ 创建日志目录: $LOG_DIR"
    else
        echo "✅ 日志目录已存在: $LOG_DIR"
    fi
}

# 检查是否已有监控进程在运行
check_existing_process() {
    echo "🔍 检查现有监控进程..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️ 已有监控进程在运行 (PID: $PID)"

            read -p "是否停止现有进程并重新启动? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "🛑 停止现有监控进程..."
                kill "$PID" 2>/dev/null || true
                sleep 2

                # 确认进程已停止
                if ps -p "$PID" > /dev/null 2>&1; then
                    echo "❌ 无法停止现有进程，请手动停止"
                    exit 1
                else
                    echo "✅ 现有监控进程已停止"
                    rm -f "$PID_FILE"
                fi
            else
                echo "ℹ️ 保持现有进程运行，退出脚本"
                exit 0
            fi
        else
            # 清理无效的PID文件
            echo "⚠️ 发现无效的PID文件，清理中..."
            rm -f "$PID_FILE"
        fi
    else
        echo "✅ 无现有监控进程"
    fi
}

# 启动监控守护进程
start_daemon() {
    echo "🚀 启动队列监控守护进程..."

    # 启动守护进程
    nohup python3 "$MONITOR_SCRIPT" --daemon --config "$CONFIG_FILE" > "$LOG_FILE" 2>&1 &

    MONITOR_PID=$!

    # 等待进程启动
    echo "⏳ 等待监控进程启动..."
    sleep 3

    # 检查进程是否运行
    if kill -0 $MONITOR_PID 2>/dev/null; then
        # 保存PID到文件
        echo "$MONITOR_PID" > "$PID_FILE"

        echo "✅ 队列监控守护进程已启动 (PID: $MONITOR_PID)"
        echo "📄 日志文件: $LOG_FILE"
        echo "📊 查看实时日志: tail -f $LOG_FILE"
        echo "🛑 停止命令: ./scripts/stop_queue_monitor.sh"
    else
        echo "❌ 监控进程启动失败"
        echo "📄 查看错误日志: cat $LOG_FILE"
        exit 1
    fi
}

# 测试单次运行
test_once() {
    echo "🧪 测试单次运行模式..."

    if python3 "$MONITOR_SCRIPT" --once --config "$CONFIG_FILE"; then
        echo "✅ 单次运行测试成功"
        return 0
    else
        echo "❌ 单次运行测试失败"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo "Athena队列监控系统启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start     启动监控守护进程（默认）"
    echo "  stop      停止监控守护进程"
    echo "  restart   重启监控守护进程"
    echo "  status    查看监控进程状态"
    echo "  test      测试单次运行模式"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start     # 启动守护进程"
    echo "  $0 test      # 测试单次运行"
    echo "  $0 status    # 查看状态"
}

# 停止监控进程
stop_daemon() {
    echo "🛑 停止队列监控进程..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null || true
            sleep 2

            if ps -p "$PID" > /dev/null 2>&1; then
                echo "❌ 无法停止监控进程，尝试强制停止..."
                kill -9 "$PID" 2>/dev/null || true
                sleep 1
            fi

            echo "✅ 队列监控进程已停止"
            rm -f "$PID_FILE"
        else
            echo "⚠️ PID文件存在但进程不存在，清理中..."
            rm -f "$PID_FILE"
        fi
    else
        # 如果没有PID文件，尝试通过进程名停止
        if pgrep -f "queue_monitor.py.*daemon" > /dev/null; then
            echo "⚠️ 通过进程名查找监控进程..."
            pkill -f "queue_monitor.py.*daemon"
            sleep 2
            echo "✅ 队列监控进程已停止"
        else
            echo "ℹ️ 无正在运行的监控进程"
        fi
    fi
}

# 查看状态
show_status() {
    echo "📊 队列监控系统状态"
    echo ""

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 监控守护进程正在运行"
            echo ""
            echo "  PID: $PID"
            echo "  命令行: $(ps -p $PID -o command=)"
            echo "  运行时间: $(ps -p $PID -o etime=)"
            echo "  内存使用: $(ps -p $PID -o rss= | awk '{printf \"%.1f MB\n\", \$1/1024}')"
            echo "  CPU使用: $(ps -p $PID -o %cpu=)%"
            echo ""

            # 检查日志文件
            if [ -f "$LOG_FILE" ]; then
                echo "📄 日志文件: $LOG_FILE"
                echo "  文件大小: $(du -h "$LOG_FILE" 2>/dev/null | cut -f1 || echo "N/A")"
                echo "  最后修改: $(stat -f "%Sm" "$LOG_FILE" 2>/dev/null || echo "N/A")"
                echo "  最后几行日志:"
                tail -5 "$LOG_FILE" 2>/dev/null | sed 's/^/    /' || echo "    无法读取日志"
            fi
        else
            echo "❌ PID文件存在但进程未运行 (PID: $PID)"
            echo "⚠️ 清理无效的PID文件..."
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ 监控守护进程未运行"
        echo "💡 使用 '$0 start' 启动监控"
    fi
}

# 重启监控进程
restart_daemon() {
    echo "🔄 重启队列监控守护进程..."
    stop_daemon
    sleep 2
    check_dependencies
    check_config
    create_log_dir
    start_daemon
}

# 主函数
main() {
    # 如果没有参数或第一个参数是配置文件（以.yaml或.yml结尾），则默认为start
    if [ $# -eq 0 ] || [[ "$1" =~ \.(yaml|yml)$ ]]; then
        CONFIG_FILE="${1:-scripts/queue_monitor_config.yaml}"
        ACTION="start"
    else
        ACTION="$1"
        CONFIG_FILE="${2:-scripts/queue_monitor_config.yaml}"
    fi

    case "$ACTION" in
        start)
            check_dependencies
            check_config
            create_log_dir
            check_existing_process
            start_daemon
            ;;
        stop)
            stop_daemon
            ;;
        restart)
            restart_daemon
            ;;
        status)
            show_status
            ;;
        test)
            check_dependencies
            check_config
            create_log_dir
            test_once
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "❌ 未知操作: $ACTION"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"