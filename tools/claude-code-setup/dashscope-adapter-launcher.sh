#!/bin/bash

# AI Assistant DashScope适配器启动脚本
# 启动本地代理服务器，将LLM格式转换为OpenAI格式

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置文件
CONFIG_FILE="/Users/frankie/claude-code-setup/claude-config.sh"
ADAPTER_SCRIPT="/Users/frankie/claude-code-setup/dashscope-adapter.py"

# 加载配置
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${RED}❌ 配置文件不存在: $CONFIG_FILE${NC}"
    exit 1
fi

# 检查适配器脚本
if [ ! -f "$ADAPTER_SCRIPT" ]; then
    echo -e "${RED}❌ 适配器脚本不存在: $ADAPTER_SCRIPT${NC}"
    echo -e "${YELLOW}请先创建适配器脚本:${NC}"
    echo "  python3 $ADAPTER_SCRIPT"
    exit 1
fi

# 显示状态函数
show_header() {
    echo "=========================================="
    echo "  AI Assistant - DashScope适配器"
    echo "  解决LLM↔OpenAI格式转换问题"
    echo "=========================================="
    echo ""
}

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}🔍 检查依赖...${NC}"

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3未安装${NC}"
        echo "请安装Python3: brew install python@3"
        exit 1
    fi

    if ! python3 -c "import requests" &> /dev/null; then
        echo -e "${YELLOW}⚠️  requests库未安装，正在安装...${NC}"
        python3 -m pip install requests --quiet
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ 安装requests库失败${NC}"
            echo "请手动安装: pip3 install requests"
            exit 1
        fi
        echo -e "${GREEN}✅ requests库已安装${NC}"
    fi

    echo -e "${GREEN}✅ 所有依赖已满足${NC}"
}

# 启动适配器
start_adapter() {
    echo ""
    echo -e "${BLUE}🚀 启动DashScope适配器...${NC}"

    # 检查是否已在运行
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null; then
        echo -e "${YELLOW}⚠️  适配器已在端口8080运行${NC}"
        echo -e "${YELLOW}   跳过启动，直接配置环境变量${NC}"
        return 0
    fi

    # 在后台启动适配器，将输出重定向到日志文件
    LOG_FILE="/tmp/dashscope-adapter-$(date +%Y%m%d-%H%M%S).log"
    python3 "$ADAPTER_SCRIPT" > "$LOG_FILE" 2>&1 &
    ADAPTER_PID=$!
    echo -e "${YELLOW}📝 适配器日志: $LOG_FILE${NC}"

    # 等待适配器启动
    echo -e "${YELLOW}⏳ 等待适配器启动...${NC}"
    sleep 2

    if kill -0 $ADAPTER_PID 2>/dev/null; then
        echo -e "${GREEN}✅ 适配器已启动 (PID: $ADAPTER_PID)${NC}"
        echo $ADAPTER_PID > /tmp/claude-dashscope-adapter.pid
    else
        echo -e "${RED}❌ 适配器启动失败${NC}"
        return 1
    fi

    # 验证适配器是否响应
    if curl -s http://localhost:8080/v1/models > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 适配器响应正常${NC}"
        return 0
    else
        echo -e "${RED}❌ 适配器未响应${NC}"
        kill $ADAPTER_PID 2>/dev/null
        return 1
    fi
}

# 配置环境变量
setup_environment() {
    echo ""
    echo -e "${BLUE}🔧 配置环境变量...${NC}"

    # 导出环境变量
    export LLM_BASE_URL="http://localhost:8080"
    export LLM_MODEL="qwen3.6-plus"
    export LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY"
    export AI_CODE_BARE=1
    export AI_CODE_SKIP_KEYCHAIN=1

    echo -e "${GREEN}✅ 环境变量已配置:${NC}"
    echo "   LLM_BASE_URL: $LLM_BASE_URL"
    echo "   LLM_MODEL: $LLM_MODEL"
    echo "   LLM_AUTH_TOKEN: ${DASHSCOPE_API_KEY:0:10}..."
    echo ""

    # 创建启动AI Assistant的命令
    echo -e "${BLUE}📋 启动AI Assistant:${NC}"
    echo "   方法1: 直接运行: /opt/homebrew/bin/claude"
    echo "   方法2: 使用别名: claude"
    echo ""
    echo -e "${YELLOW}⚠️  注意: 适配器在后台运行，使用完成后请停止${NC}"
}

# 停止适配器
stop_adapter() {
    echo ""
    echo -e "${BLUE}🛑 停止适配器...${NC}"

    if [ -f /tmp/claude-dashscope-adapter.pid ]; then
        ADAPTER_PID=$(cat /tmp/claude-dashscope-adapter.pid)
        if kill -0 $ADAPTER_PID 2>/dev/null; then
            kill $ADAPTER_PID
            echo -e "${GREEN}✅ 适配器已停止 (PID: $ADAPTER_PID)${NC}"
            rm -f /tmp/claude-dashscope-adapter.pid
        else
            echo -e "${YELLOW}⚠️  适配器进程不存在${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  未找到适配器PID文件${NC}"
        # 尝试查找并杀死进程
        PIDS=$(lsof -ti:8080 2>/dev/null)
        if [ -n "$PIDS" ]; then
            echo "$PIDS" | xargs kill -9 2>/dev/null
            echo -e "${GREEN}✅ 已停止端口8080上的进程${NC}"
        else
            echo -e "${YELLOW}⚠️  未找到运行中的适配器${NC}"
        fi
    fi
}

# 显示使用说明
show_usage() {
    echo -e "${BLUE}📖 使用说明:${NC}"
    echo "  $0 start     启动适配器并配置环境变量"
    echo "  $0 stop      停止适配器"
    echo "  $0 status    查看适配器状态"
    echo "  $0 run       启动适配器并运行AI Assistant"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  $0 start      # 启动适配器"
    echo "  eval \"\$($0 start)\" # 启动并导出环境变量"
    echo "  $0 run        # 启动适配器并运行AI Assistant"
}

# 查看状态
check_status() {
    echo -e "${BLUE}📊 适配器状态:${NC}"

    # 检查端口
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null; then
        echo -e "${GREEN}✅ 适配器正在运行 (端口: 8080)${NC}"
        if [ -f /tmp/claude-dashscope-adapter.pid ]; then
            ADAPTER_PID=$(cat /tmp/claude-dashscope-adapter.pid)
            echo "   PID: $ADAPTER_PID"
        fi
    else
        echo -e "${RED}❌ 适配器未运行${NC}"
    fi

    # 检查环境变量
    echo ""
    echo -e "${BLUE}🔧 环境变量:${NC}"
    if [ -n "$LLM_BASE_URL" ]; then
        echo "   LLM_BASE_URL: ${LLM_BASE_URL}"
    else
        echo "   LLM_BASE_URL: ${RED}未设置${NC}"
    fi
}

# 主函数
main() {
    case "$1" in
        start)
            # 如果是quiet模式，重定向stdout到stderr，保留环境变量输出到原始stdout
            if [ "$2" = "quiet" ]; then
                # 保存原始stdout到文件描述符3
                exec 3>&1
                # 重定向stdout到stderr，这样函数输出不会污染eval
                exec 1>&2

                check_dependencies
                if start_adapter; then
                    setup_environment
                    # 恢复原始stdout并输出环境变量
                    exec 1>&3
                    echo "export LLM_BASE_URL=\"http://localhost:8080\""
                    echo "export LLM_MODEL=\"qwen3.6-plus\""
                    echo "export LLM_AUTH_TOKEN=\"$DASHSCOPE_API_KEY\""
                    echo "export AI_CODE_BARE=1"
                    echo "export AI_CODE_SKIP_KEYCHAIN=1"
                else
                    # 如果启动失败，恢复stdout并退出
                    exec 1>&3
                    exit 1
                fi
            else
                # 正常模式
                show_header
                check_dependencies
                if start_adapter; then
                    setup_environment
                    echo ""
                    echo -e "${CYAN}📝 要导出环境变量，运行:${NC}"
                    echo "  eval \"\$($0 start quiet)\""
                    echo ""
                    echo "export LLM_BASE_URL=\"http://localhost:8080\""
                    echo "export LLM_MODEL=\"qwen3.6-plus\""
                    echo "export LLM_AUTH_TOKEN=\"$DASHSCOPE_API_KEY\""
                    echo "export AI_CODE_BARE=1"
                    echo "export AI_CODE_SKIP_KEYCHAIN=1"
                fi
            fi
            ;;
        stop)
            stop_adapter
            ;;
        status)
            check_status
            ;;
        run)
            show_header
            check_dependencies
            if start_adapter; then
                setup_environment
                echo ""
                echo -e "${CYAN}🚀 启动AI Assistant...${NC}"
                echo ""
                exec /opt/homebrew/bin/claude
            fi
            ;;
        *)
            show_usage
            ;;
    esac
}

# 如果直接执行，调用主函数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [ "$1" = "start" ] && [ "$2" != "run" ]; then
        # 只输出环境变量，不执行
        main "$@"
    else
        main "$@"
    fi
fi