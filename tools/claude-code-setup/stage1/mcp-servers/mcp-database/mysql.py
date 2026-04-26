"""
MySQL MCP服务器实现

基于aiomysql提供异步MySQL数据库操作支持
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import aiomysql
from . import DatabaseMCPBase, DatabaseType, run_mcp_server


class MySQLMCP(DatabaseMCPBase):
    """MySQL MCP服务器"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        super().__init__(DatabaseType.MYSQL)
        self.host = host or "localhost"
        self.port = port or 3306
        self.user = user or "root"
        self.password = password or ""
        self.database = database or "test"
        self.connection_pool = None

    async def initialize(self):
        """初始化MySQL连接池"""
        await super().initialize()

        # 创建MySQL连接池
        self.connection_pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            minsize=1,
            maxsize=10,
            autocommit=True
        )
        self.logger.info(f"MySQL连接池已创建: {self.host}:{self.port}/{self.database}")

    async def list_tools(self) -> List[Any]:
        """列出MySQL特定工具"""
        tools = await super().list_tools()

        # 添加MySQL特定工具
        mysql_tools = [
            {
                "name": "mysql_execute_query",
                "description": "执行MySQL SQL查询",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL查询语句"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "查询参数"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "mysql_list_databases",
                "description": "列出所有数据库",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "mysql_list_tables",
                "description": "列出所有表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "database": {"type": "string", "description": "数据库名"}
                    }
                }
            },
            {
                "name": "mysql_create_database",
                "description": "创建新数据库",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "database_name": {"type": "string", "description": "数据库名"},
                        "charset": {"type": "string", "description": "字符集"},
                        "collation": {"type": "string", "description": "排序规则"}
                    },
                    "required": ["database_name"]
                }
            },
            {
                "name": "mysql_create_table",
                "description": "创建新表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "列定义，如 'id INT PRIMARY KEY AUTO_INCREMENT', 'name VARCHAR(255) NOT NULL'"
                        },
                        "engine": {"type": "string", "description": "存储引擎"},
                        "charset": {"type": "string", "description": "字符集"}
                    },
                    "required": ["table_name", "columns"]
                }
            },
            {
                "name": "mysql_drop_table",
                "description": "删除表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "if_exists": {"type": "boolean", "description": "如果存在才删除"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "mysql_insert_data",
                "description": "插入数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "data": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "要插入的数据行"
                        },
                        "ignore": {"type": "boolean", "description": "使用INSERT IGNORE"}
                    },
                    "required": ["table_name", "data"]
                }
            },
            {
                "name": "mysql_update_data",
                "description": "更新数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "set_clause": {"type": "string", "description": "SET子句，如 'name = %s'"},
                        "where_clause": {"type": "string", "description": "WHERE子句，如 'id = %s'"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "参数值"}
                    },
                    "required": ["table_name", "set_clause"]
                }
            },
            {
                "name": "mysql_delete_data",
                "description": "删除数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "where_clause": {"type": "string", "description": "WHERE子句"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "参数值"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "mysql_create_index",
                "description": "创建索引",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index_name": {"type": "string", "description": "索引名"},
                        "table_name": {"type": "string", "description": "表名"},
                        "columns": {"type": "array", "items": {"type": "string"}, "description": "列名"},
                        "index_type": {"type": "string", "description": "索引类型: INDEX|UNIQUE|FULLTEXT|SPATIAL"}
                    },
                    "required": ["index_name", "table_name", "columns"]
                }
            },
            {
                "name": "mysql_execute_transaction",
                "description": "执行事务",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "parameters": {"type": "array", "items": {"type": "string"}}
                                }
                            },
                            "description": "事务中的查询列表"
                        }
                    },
                    "required": ["queries"]
                }
            },
            {
                "name": "mysql_show_processlist",
                "description": "显示当前进程",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "mysql_explain_query",
                "description": "解释查询执行计划",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "要解释的查询"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "mysql_get_table_schema",
                "description": "获取表结构信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"}
                    },
                    "required": ["table_name"]
                }
            }
        ]

        # 合并工具列表
        from mcp.types import Tool
        all_tools = []
        for tool in tools:
            all_tools.append(tool)
        for tool_def in mysql_tools:
            all_tools.append(Tool(**tool_def))

        return all_tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理MySQL工具调用"""
        self.logger.info(f"MySQL工具调用: {tool_name}")

        if tool_name == "mysql_execute_query":
            return await self._mysql_execute_query(arguments)
        elif tool_name == "mysql_list_databases":
            return await self._mysql_list_databases(arguments)
        elif tool_name == "mysql_list_tables":
            return await self._mysql_list_tables(arguments)
        elif tool_name == "mysql_create_database":
            return await self._mysql_create_database(arguments)
        elif tool_name == "mysql_create_table":
            return await self._mysql_create_table(arguments)
        elif tool_name == "mysql_drop_table":
            return await self._mysql_drop_table(arguments)
        elif tool_name == "mysql_insert_data":
            return await self._mysql_insert_data(arguments)
        elif tool_name == "mysql_update_data":
            return await self._mysql_update_data(arguments)
        elif tool_name == "mysql_delete_data":
            return await self._mysql_delete_data(arguments)
        elif tool_name == "mysql_create_index":
            return await self._mysql_create_index(arguments)
        elif tool_name == "mysql_execute_transaction":
            return await self._mysql_execute_transaction(arguments)
        elif tool_name == "mysql_show_processlist":
            return await self._mysql_show_processlist(arguments)
        elif tool_name == "mysql_explain_query":
            return await self._mysql_explain_query(arguments)
        elif tool_name == "mysql_get_table_schema":
            return await self._mysql_get_table_schema(arguments)
        else:
            # 回退到基类工具
            return await super().handle_tool_call(tool_name, arguments)

    async def _mysql_execute_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        query = args.get("query", "")
        parameters = args.get("parameters", [])

        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    if parameters:
                        await cursor.execute(query, parameters)
                    else:
                        await cursor.execute(query)

                    # 如果是SELECT查询，获取结果
                    if query.strip().upper().startswith("SELECT"):
                        rows = await cursor.fetchall()
                        return {
                            "success": True,
                            "rows": rows,
                            "row_count": len(rows),
                            "query": query
                        }
                    else:
                        # 对于非SELECT查询，获取影响的行数
                        return {
                            "success": True,
                            "row_count": cursor.rowcount,
                            "lastrowid": cursor.lastrowid,
                            "query": query
                        }

                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "query": query
                    }

    async def _mysql_list_databases(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有数据库"""
        query = "SHOW DATABASES;"

        return await self._mysql_execute_query({"query": query})

    async def _mysql_list_tables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有表"""
        database = args.get("database", self.database)
        query = f"SHOW TABLES FROM `{database}`;"

        return await self._mysql_execute_query({"query": query})

    async def _mysql_create_database(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建新数据库"""
        database_name = args["database_name"]
        charset = args.get("charset", "utf8mb4")
        collation = args.get("collation", "utf8mb4_unicode_ci")

        query = f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET {charset} COLLATE {collation};"

        return await self._mysql_execute_query({"query": query})

    async def _mysql_create_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建新表"""
        table_name = args["table_name"]
        columns = args["columns"]
        engine = args.get("engine", "InnoDB")
        charset = args.get("charset", "utf8mb4")

        # 构建CREATE TABLE语句
        columns_sql = ",\n  ".join(columns)
        query = f'CREATE TABLE IF NOT EXISTS `{table_name}` (\n  {columns_sql}\n) ENGINE={engine} DEFAULT CHARSET={charset};'

        return await self._mysql_execute_query({"query": query})

    async def _mysql_drop_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除表"""
        table_name = args["table_name"]
        if_exists = args.get("if_exists", True)

        if if_exists:
            query = f'DROP TABLE IF EXISTS `{table_name}`;'
        else:
            query = f'DROP TABLE `{table_name}`;'

        return await self._mysql_execute_query({"query": query})

    async def _mysql_insert_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """插入数据"""
        table_name = args["table_name"]
        data = args["data"]
        ignore = args.get("ignore", False)

        if not data:
            return {"success": False, "error": "没有提供数据"}

        # 获取第一行数据的键作为列名
        first_row = data[0]
        columns = list(first_row.keys())
        columns_str = ', '.join([f'`{col}`' for col in columns])

        results = []
        for row in data:
            # 构建参数占位符 %s, %s, ...
            param_placeholders = ', '.join(['%s' for _ in columns])
            values = [row[col] for col in columns]

            ignore_str = "IGNORE " if ignore else ""
            query = f'INSERT {ignore_str}INTO `{table_name}` ({columns_str}) VALUES ({param_placeholders});'

            result = await self._mysql_execute_query({
                "query": query,
                "parameters": values
            })
            results.append(result)

        return {
            "success": all(r["success"] for r in results),
            "inserted_rows": len(data),
            "results": results
        }

    async def _mysql_update_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据"""
        table_name = args["table_name"]
        set_clause = args["set_clause"]
        where_clause = args.get("where_clause", "1=1")
        parameters = args.get("parameters", [])

        query = f'UPDATE `{table_name}` SET {set_clause} WHERE {where_clause};'

        return await self._mysql_execute_query({
            "query": query,
            "parameters": parameters
        })

    async def _mysql_delete_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除数据"""
        table_name = args["table_name"]
        where_clause = args.get("where_clause", "1=0")  # 默认不删除任何数据
        parameters = args.get("parameters", [])

        if where_clause == "1=0":
            return {"success": False, "error": "必须提供WHERE子句以防止误删除"}

        query = f'DELETE FROM `{table_name}` WHERE {where_clause};'

        return await self._mysql_execute_query({
            "query": query,
            "parameters": parameters
        })

    async def _mysql_create_index(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建索引"""
        index_name = args["index_name"]
        table_name = args["table_name"]
        columns = args["columns"]
        index_type = args.get("index_type", "INDEX")

        columns_str = ', '.join([f'`{col}`' for col in columns])

        query = f'CREATE {index_type} `{index_name}` ON `{table_name}` ({columns_str});'

        return await self._mysql_execute_query({"query": query})

    async def _mysql_execute_transaction(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行事务"""
        queries = args["queries"]

        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    # 开始事务
                    await conn.begin()

                    results = []
                    for query_info in queries:
                        query = query_info["query"]
                        parameters = query_info.get("parameters", [])

                        try:
                            if parameters:
                                await cursor.execute(query, parameters)
                            else:
                                await cursor.execute(query)

                            # 检查是否是SELECT查询
                            if query.strip().upper().startswith("SELECT"):
                                rows = await cursor.fetchall()
                                row_count = len(rows)
                            else:
                                row_count = cursor.rowcount

                            results.append({
                                "success": True,
                                "query": query,
                                "row_count": row_count
                            })
                        except Exception as e:
                            results.append({
                                "success": False,
                                "query": query,
                                "error": str(e)
                            })
                            raise  # 事务中出错会回滚

                    # 提交事务
                    await conn.commit()

                    return {
                        "success": all(r["success"] for r in results),
                        "results": results,
                        "transaction_completed": True
                    }
                except Exception as e:
                    # 回滚事务
                    await conn.rollback()
                    return {
                        "success": False,
                        "error": str(e),
                        "results": results,
                        "transaction_completed": False
                    }

    async def _mysql_show_processlist(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """显示当前进程"""
        query = "SHOW PROCESSLIST;"

        return await self._mysql_execute_query({"query": query})

    async def _mysql_explain_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """解释查询执行计划"""
        query = args["query"]

        explain_query = f"EXPLAIN {query}"

        return await self._mysql_execute_query({"query": explain_query})

    async def _mysql_get_table_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取表结构信息"""
        table_name = args["table_name"]

        # 获取表结构信息
        query = f"""
        SELECT
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_KEY,
            COLUMN_DEFAULT,
            EXTRA
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION;
        """

        result = await self._mysql_execute_query({
            "query": query,
            "parameters": [table_name]
        })

        if result["success"]:
            result["table_name"] = table_name
            result["database"] = self.database

        return result

    async def close(self):
        """关闭连接池"""
        if self.connection_pool:
            self.connection_pool.close()
            await self.connection_pool.wait_closed()
            self.logger.info("MySQL连接池已关闭")


def main():
    """主函数：启动MySQL MCP服务器"""
    # 从环境变量获取连接参数
    import os
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "test")

    server = MySQLMCP(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

    # 运行MCP服务器
    run_mcp_server(server)


if __name__ == "__main__":
    main()