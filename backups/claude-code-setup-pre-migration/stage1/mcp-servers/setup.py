#!/usr/bin/env python3
"""
AI Assistant 数据库MCP包安装脚本

安装数据库MCP服务器到AI Assistant的MCP服务器目录
"""

import os
import sys
import shutil
import json
from pathlib import Path

def get_ai_mcp_dir():
    """获取AI Assistant MCP服务器目录"""
    # 尝试从环境变量获取
    mcp_dir = os.environ.get("AI_MCP_DIR")
    if mcp_dir:
        return Path(mcp_dir)

    # 默认位置
    home = Path.home()

    # AI Assistant MCP服务器目录
    ai_mcp_dir = home / ".ai" / "mcp-servers"

    # 如果目录不存在，创建它
    ai_mcp_dir.mkdir(parents=True, exist_ok=True)

    return ai_mcp_dir

def install_database_mcp():
    """安装数据库MCP包"""
    print("🚀 开始安装AI Assistant数据库MCP包...")

    # 获取当前脚本目录
    current_dir = Path(__file__).parent
    mcp_dir = get_ai_mcp_dir()

    # 目标目录
    target_dir = mcp_dir / "mcp-database"

    # 复制整个mcp-database目录
    source_dir = current_dir / "mcp-database"

    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        return False

    # 如果目标目录已存在，先删除
    if target_dir.exists():
        print(f"🗑️  删除现有目录: {target_dir}")
        shutil.rmtree(target_dir)

    # 复制目录
    print(f"📁 复制数据库MCP文件到: {target_dir}")
    shutil.copytree(source_dir, target_dir)

    # 复制requirements.txt
    requirements_src = current_dir / "requirements.txt"
    requirements_dst = target_dir / "requirements.txt"
    if requirements_src.exists():
        shutil.copy2(requirements_src, requirements_dst)
        print(f"📦 复制依赖文件: {requirements_dst}")

    # 创建启动脚本
    create_startup_scripts(target_dir)

    # 创建mcp.json配置文件
    create_mcp_config(target_dir)

    print("✅ 数据库MCP包安装完成!")
    print(f"📁 安装位置: {target_dir}")

    # 显示使用说明
    print("\n📖 使用说明:")
    print("1. 安装依赖: pip install -r requirements.txt")
    print("2. 启动PostgreSQL MCP服务器: python postgres.py")
    print("3. 启动Redis MCP服务器: python redis.py")
    print("4. 启动MongoDB MCP服务器: python mongodb.py")
    print("5. 启动SQLite MCP服务器: python sqlite.py")
    print("6. 启动MySQL MCP服务器: python mysql.py")

    return True

def create_startup_scripts(target_dir: Path):
    """创建启动脚本"""
    # 创建启动脚本
    scripts = {
        "start-postgres.sh": """#!/bin/bash
# 启动PostgreSQL MCP服务器
export POSTGRES_URL=${POSTGRES_URL:-"postgresql://localhost:5432/postgres"}
python postgres.py
""",
        "start-redis.sh": """#!/bin/bash
# 启动Redis MCP服务器
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
python redis.py
""",
        "start-mongodb.sh": """#!/bin/bash
# 启动MongoDB MCP服务器
export MONGODB_URL=${MONGODB_URL:-"mongodb://localhost:27017/test"}
python mongodb.py
""",
        "start-sqlite.sh": """#!/bin/bash
# 启动SQLite MCP服务器
export SQLITE_DB_PATH=${SQLITE_DB_PATH:-":memory:"}
python sqlite.py
""",
        "start-mysql.sh": """#!/bin/bash
# 启动MySQL MCP服务器
export MYSQL_HOST=${MYSQL_HOST:-"localhost"}
export MYSQL_PORT=${MYSQL_PORT:-"3306"}
export MYSQL_USER=${MYSQL_USER:-"root"}
export MYSQL_PASSWORD=${MYSQL_PASSWORD:-""}
export MYSQL_DATABASE=${MYSQL_DATABASE:-"test"}
python mysql.py
""",
        "install-deps.sh": """#!/bin/bash
# 安装Python依赖
pip install -r requirements.txt
"""
    }

    for script_name, script_content in scripts.items():
        script_path = target_dir / script_name
        with open(script_path, "w") as f:
            f.write(script_content)
        script_path.chmod(0o755)
        print(f"📝 创建启动脚本: {script_path}")

def create_mcp_config(target_dir: Path):
    """创建MCP配置文件"""
    mcp_config = {
        "mcpServers": {
            "postgres": {
                "command": "python",
                "args": [str(target_dir / "postgres.py")],
                "env": {
                    "POSTGRES_URL": "postgresql://localhost:5432/postgres"
                }
            },
            "redis": {
                "command": "python",
                "args": [str(target_dir / "redis.py")],
                "env": {
                    "REDIS_URL": "redis://localhost:6379/0"
                }
            },
            "mongodb": {
                "command": "python",
                "args": [str(target_dir / "mongodb.py")],
                "env": {
                    "MONGODB_URL": "mongodb://localhost:27017/test"
                }
            },
            "sqlite": {
                "command": "python",
                "args": [str(target_dir / "sqlite.py")],
                "env": {
                    "SQLITE_DB_PATH": ":memory:"
                }
            },
            "mysql": {
                "command": "python",
                "args": [str(target_dir / "mysql.py")],
                "env": {
                    "MYSQL_HOST": "localhost",
                    "MYSQL_PORT": "3306",
                    "MYSQL_USER": "root",
                    "MYSQL_PASSWORD": "",
                    "MYSQL_DATABASE": "test"
                }
            }
        }
    }

    config_path = target_dir / "mcp.json"
    with open(config_path, "w") as f:
        json.dump(mcp_config, f, indent=2)

    print(f"⚙️  创建MCP配置文件: {config_path}")

def main():
    """主函数"""
    try:
        success = install_database_mcp()
        if success:
            print("\n🎉 安装成功！")
            print("💡 提示: 您可以将MCP服务器配置添加到AI Assistant的settings.json文件中")
            print("📄 配置示例:")
            print('''
{
  "mcpServers": {
    "postgres": {
      "command": "python",
      "args": ["/path/to/mcp-database/postgres.py"]
    },
    "redis": {
      "command": "python",
      "args": ["/path/to/mcp-database/redis.py"]
    }
  }
}
            ''')
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ 安装失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()