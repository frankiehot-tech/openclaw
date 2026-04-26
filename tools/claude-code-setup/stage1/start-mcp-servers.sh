#!/bin/bash

# AI Assistant MCP服务器启动脚本
# 用于启动所有数据库MCP服务器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_SERVERS_DIR="$SCRIPT_DIR/mcp-servers"
MCP_DATABASE_DIR="$MCP_SERVERS_DIR/mcp-database"

echo "🚀 启动AI Assistant数据库MCP服务器..."

# 检查依赖
check_dependencies() {
    echo "🔍 检查依赖..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3未安装"
        exit 1
    fi

    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        echo "❌ pip3未安装"
        exit 1
    fi

    echo "✅ 依赖检查通过"
}

# 安装依赖
install_dependencies() {
    echo "📦 安装Python依赖..."

    if [ -f "$MCP_SERVERS_DIR/requirements.txt" ]; then
        pip3 install -r "$MCP_SERVERS_DIR/requirements.txt"
        echo "✅ 依赖安装完成"
    else
        echo "❌ requirements.txt文件不存在: $MCP_SERVERS_DIR/requirements.txt"
        exit 1
    fi
}

# 安装MCP包到AI Assistant
install_mcp_package() {
    echo "📁 安装MCP包到AI Assistant..."

    if [ -f "$MCP_SERVERS_DIR/setup.py" ]; then
        cd "$MCP_SERVERS_DIR"
        python3 setup.py
        echo "✅ MCP包安装完成"
    else
        echo "❌ setup.py文件不存在: $MCP_SERVERS_DIR/setup.py"
        exit 1
    fi
}

# 启动单个MCP服务器
start_server() {
    local server_name="$1"
    local script_name="$2"
    local env_vars="$3"

    echo "🔄 启动$server_name MCP服务器..."

    if [ -f "$MCP_DATABASE_DIR/$script_name" ]; then
        # 设置环境变量
        if [ -n "$env_vars" ]; then
            export $env_vars
        fi

        # 在后台启动服务器
        cd "$MCP_DATABASE_DIR"
        python3 "$script_name" &
        local pid=$!
        echo "✅ $server_name MCP服务器已启动 (PID: $pid)"
    else
        echo "❌ $server_name脚本不存在: $MCP_DATABASE_DIR/$script_name"
    fi
}

# 停止所有MCP服务器
stop_servers() {
    echo "🛑 停止所有MCP服务器..."

    # 查找并杀死所有MCP服务器进程
    pids=$(pgrep -f "python.*\.py" | grep -v $$ || true)

    if [ -n "$pids" ]; then
        echo "🔍 找到运行中的MCP服务器进程: $pids"
        kill $pids 2>/dev/null || true
        echo "✅ 已发送停止信号"
    else
        echo "ℹ️  没有运行中的MCP服务器"
    fi
}

# 显示状态
show_status() {
    echo "📊 MCP服务器状态:"

    # 检查PostgreSQL
    if pgrep -f "postgres.py" > /dev/null; then
        echo "✅ PostgreSQL: 运行中"
    else
        echo "❌ PostgreSQL: 未运行"
    fi

    # 检查Redis
    if pgrep -f "redis.py" > /dev/null; then
        echo "✅ Redis: 运行中"
    else
        echo "❌ Redis: 未运行"
    fi

    # 检查MongoDB
    if pgrep -f "mongodb.py" > /dev/null; then
        echo "✅ MongoDB: 运行中"
    else
        echo "❌ MongoDB: 未运行"
    fi

    # 检查SQLite
    if pgrep -f "sqlite.py" > /dev/null; then
        echo "✅ SQLite: 运行中"
    else
        echo "❌ SQLite: 未运行"
    fi

    # 检查MySQL
    if pgrep -f "mysql.py" > /dev/null; then
        echo "✅ MySQL: 运行中"
    else
        echo "❌ MySQL: 未运行"
    fi
}

# 显示使用说明
show_usage() {
    echo "使用方法: $0 [command]"
    echo ""
    echo "命令:"
    echo "  install    安装依赖和MCP包"
    echo "  start      启动所有MCP服务器"
    echo "  stop       停止所有MCP服务器"
    echo "  status     显示服务器状态"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install   # 安装依赖"
    echo "  $0 start     # 启动所有服务器"
    echo "  $0 status    # 查看状态"
}

# 主函数
main() {
    case "$1" in
        install)
            check_dependencies
            install_dependencies
            install_mcp_package
            ;;
        start)
            check_dependencies

            # 启动所有服务器
            start_server "PostgreSQL" "postgres.py" "POSTGRES_URL=postgresql://localhost:5432/postgres"
            start_server "Redis" "redis.py" "REDIS_URL=redis://localhost:6379/0"
            start_server "MongoDB" "mongodb.py" "MONGODB_URL=mongodb://localhost:27017/test"
            start_server "SQLite" "sqlite.py" "SQLITE_DB_PATH=:memory:"
            start_server "MySQL" "mysql.py" "MYSQL_HOST=localhost MYSQL_PORT=3306 MYSQL_USER=root MYSQL_PASSWORD='' MYSQL_DATABASE=test"

            echo ""
            echo "🎉 所有MCP服务器已启动!"
            echo ""
            show_status
            echo ""
            echo "💡 提示: 使用 '$0 status' 查看状态"
            echo "💡 提示: 使用 '$0 stop' 停止服务器"
            ;;
        stop)
            stop_servers
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            echo "❌ 未知命令: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"