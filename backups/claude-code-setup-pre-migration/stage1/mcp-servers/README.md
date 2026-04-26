# AI Assistant 数据库MCP包

基于MCP (Model Context Protocol) 的数据库操作服务器包，为AI Assistant提供多种数据库的直接操作能力。

## 📦 支持的数据库

| 数据库 | 实现文件 | Python包 | 默认连接 |
|--------|----------|-----------|----------|
| PostgreSQL | `postgres.py` | `asyncpg` | `postgresql://localhost:5432/postgres` |
| Redis | `redis.py` | `aioredis` | `redis://localhost:6379/0` |
| MongoDB | `mongodb.py` | `motor` | `mongodb://localhost:27017/test` |
| SQLite | `sqlite.py` | `aiosqlite` | `:memory:` |
| MySQL | `mysql.py` | `aiomysql` | `localhost:3306/test` |

## 🚀 快速开始

### 1. 安装依赖

```bash
cd stage1/mcp-servers
pip install -r requirements.txt
```

### 2. 安装到AI Assistant

```bash
python setup.py
```

### 3. 配置AI Assistant

将MCP服务器添加到AI Assistant的settings.json文件中：

```json
{
  "mcpServers": {
    "postgres": {
      "command": "python",
      "args": ["/path/to/mcp-database/postgres.py"],
      "env": {
        "POSTGRES_URL": "postgresql://localhost:5432/mydb"
      }
    },
    "redis": {
      "command": "python",
      "args": ["/path/to/mcp-database/redis.py"]
    }
  }
}
```

### 4. 启动AI Assistant

```bash
ai
```

## 🛠️ 可用工具

### PostgreSQL工具
- `postgres_execute_query` - 执行SQL查询
- `postgres_list_databases` - 列出所有数据库
- `postgres_list_tables` - 列出所有表
- `postgres_create_table` - 创建新表
- `postgres_insert_data` - 插入数据
- `postgres_update_data` - 更新数据
- `postgres_delete_data` - 删除数据
- `postgres_create_index` - 创建索引
- `postgres_execute_transaction` - 执行事务

### Redis工具
- `redis_set` - 设置键值
- `redis_get` - 获取键值
- `redis_delete` - 删除键
- `redis_keys` - 查找匹配模式的键
- `redis_hash_set` - 设置哈希字段
- `redis_hash_get` - 获取哈希字段
- `redis_list_push` - 向列表添加元素
- `redis_list_range` - 获取列表范围
- `redis_set_add` - 向集合添加元素
- `redis_set_members` - 获取集合成员
- `redis_info` - 获取Redis服务器信息
- `redis_pipeline` - 执行管道操作

### MongoDB工具
- `mongodb_list_collections` - 列出所有集合
- `mongodb_find_documents` - 查询文档
- `mongodb_insert_one` - 插入单个文档
- `mongodb_insert_many` - 插入多个文档
- `mongodb_update_one` - 更新单个文档
- `mongodb_update_many` - 更新多个文档
- `mongodb_delete_one` - 删除单个文档
- `mongodb_delete_many` - 删除多个文档
- `mongodb_create_index` - 创建索引
- `mongodb_drop_collection` - 删除集合
- `mongodb_aggregate` - 执行聚合管道
- `mongodb_count_documents` - 统计文档数量

### SQLite工具
- `sqlite_execute_query` - 执行SQL查询
- `sqlite_list_tables` - 列出所有表
- `sqlite_create_table` - 创建新表
- `sqlite_insert_data` - 插入数据
- `sqlite_update_data` - 更新数据
- `sqlite_delete_data` - 删除数据
- `sqlite_create_index` - 创建索引
- `sqlite_execute_transaction` - 执行事务
- `sqlite_vacuum` - 优化数据库文件
- `sqlite_backup` - 备份数据库
- `sqlite_get_schema` - 获取数据库模式信息

### MySQL工具
- `mysql_execute_query` - 执行SQL查询
- `mysql_list_databases` - 列出所有数据库
- `mysql_list_tables` - 列出所有表
- `mysql_create_database` - 创建新数据库
- `mysql_create_table` - 创建新表
- `mysql_insert_data` - 插入数据
- `mysql_update_data` - 更新数据
- `mysql_delete_data` - 删除数据
- `mysql_create_index` - 创建索引
- `mysql_execute_transaction` - 执行事务
- `mysql_show_processlist` - 显示当前进程
- `mysql_explain_query` - 解释查询执行计划
- `mysql_get_table_schema` - 获取表结构信息

## 🔧 环境变量配置

### PostgreSQL
```bash
export POSTGRES_URL="postgresql://user:password@localhost:5432/mydb"
```

### Redis
```bash
export REDIS_URL="redis://localhost:6379/0"
```

### MongoDB
```bash
export MONGODB_URL="mongodb://user:password@localhost:27017/mydb"
```

### SQLite
```bash
export SQLITE_DB_PATH="/path/to/database.db"
```

### MySQL
```bash
export MYSQL_HOST="localhost"
export MYSQL_PORT="3306"
export MYSQL_USER="root"
export MYSQL_PASSWORD="password"
export MYSQL_DATABASE="mydb"
```

## 📁 项目结构

```
mcp-database/
├── __init__.py          # 数据库MCP框架基类
├── postgres.py          # PostgreSQL MCP实现
├── redis.py             # Redis MCP实现
├── mongodb.py           # MongoDB MCP实现
├── sqlite.py            # SQLite MCP实现
├── mysql.py             # MySQL MCP实现
├── requirements.txt     # Python依赖
├── setup.py            # 安装脚本
├── README.md           # 本文档
├── start-*.sh          # 启动脚本
└── mcp.json            # MCP配置示例
```

## 🧪 测试

启动测试服务器：

```bash
# PostgreSQL
python postgres.py

# Redis
python redis.py

# MongoDB
python mongodb.py

# SQLite
python sqlite.py

# MySQL
python mysql.py
```

## 🔍 开发指南

### 添加新的数据库支持

1. 创建新的Python文件，继承 `DatabaseMCPBase` 类
2. 实现 `list_tools()` 方法定义工具
3. 实现 `handle_tool_call()` 方法处理工具调用
4. 添加数据库特定工具的实现方法
5. 在 `setup.py` 中注册新的数据库服务器

### 工具定义规范

```python
tool_def = {
    "name": "tool_name",
    "description": "工具描述",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数描述"},
            "param2": {"type": "integer", "description": "参数描述"}
        },
        "required": ["param1"]
    }
}
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请创建Issue或联系维护者。