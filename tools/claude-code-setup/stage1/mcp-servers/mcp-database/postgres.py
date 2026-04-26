"""
PostgreSQL MCP服务器实现

基于asyncpg提供高性能PostgreSQL数据库操作支持
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import asyncpg
from . import DatabaseMCPBase, DatabaseType, run_mcp_server


class PostgreSQLMCP(DatabaseMCPBase):
    """PostgreSQL MCP服务器"""

    def __init__(self, connection_string: str = None):
        super().__init__(DatabaseType.POSTGRESQL)
        self.connection_string = connection_string or "postgresql://localhost:5432/postgres"
        self.connection_pool = None

    async def initialize(self):
        """初始化PostgreSQL连接池"""
        await super().initialize()

        # 创建连接池
        self.connection_pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        self.logger.info(f"PostgreSQL连接池已创建: {self.connection_string}")

    async def list_tools(self) -> List[Any]:
        """列出PostgreSQL特定工具"""
        tools = await super().list_tools()

        # 添加PostgreSQL特定工具
        postgres_tools = [
            {
                "name": "postgres_execute_query",
                "description": "执行PostgreSQL SQL查询",
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
                "name": "postgres_list_databases",
                "description": "列出所有数据库",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "postgres_list_schemas",
                "description": "列出所有模式",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "postgres_create_table",
                "description": "创建新表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "列定义，如 'id SERIAL PRIMARY KEY', 'name VARCHAR(255)'"
                        },
                        "schema": {"type": "string", "description": "模式名，默认public"}
                    },
                    "required": ["table_name", "columns"]
                }
            },
            {
                "name": "postgres_drop_table",
                "description": "删除表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "schema": {"type": "string", "description": "模式名"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "postgres_insert_data",
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
                        "schema": {"type": "string", "description": "模式名"}
                    },
                    "required": ["table_name", "data"]
                }
            },
            {
                "name": "postgres_update_data",
                "description": "更新数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "set_clause": {"type": "string", "description": "SET子句，如 'name = $1'"},
                        "where_clause": {"type": "string", "description": "WHERE子句，如 'id = $2'"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "参数值"}
                    },
                    "required": ["table_name", "set_clause"]
                }
            },
            {
                "name": "postgres_delete_data",
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
                "name": "postgres_create_index",
                "description": "创建索引",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index_name": {"type": "string", "description": "索引名"},
                        "table_name": {"type": "string", "description": "表名"},
                        "columns": {"type": "array", "items": {"type": "string"}, "description": "列名"},
                        "schema": {"type": "string", "description": "模式名"},
                        "unique": {"type": "boolean", "description": "是否唯一索引"}
                    },
                    "required": ["index_name", "table_name", "columns"]
                }
            },
            {
                "name": "postgres_execute_transaction",
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
            }
        ]

        # 合并工具列表
        from mcp.types import Tool
        all_tools = []
        for tool in tools:
            all_tools.append(tool)
        for tool_def in postgres_tools:
            all_tools.append(Tool(**tool_def))

        return all_tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理PostgreSQL工具调用"""
        self.logger.info(f"PostgreSQL工具调用: {tool_name}")

        if tool_name == "postgres_execute_query":
            return await self._postgres_execute_query(arguments)
        elif tool_name == "postgres_list_databases":
            return await self._postgres_list_databases(arguments)
        elif tool_name == "postgres_list_schemas":
            return await self._postgres_list_schemas(arguments)
        elif tool_name == "postgres_list_tables":
            return await self._postgres_list_tables(arguments)
        elif tool_name == "postgres_create_table":
            return await self._postgres_create_table(arguments)
        elif tool_name == "postgres_drop_table":
            return await self._postgres_drop_table(arguments)
        elif tool_name == "postgres_insert_data":
            return await self._postgres_insert_data(arguments)
        elif tool_name == "postgres_update_data":
            return await self._postgres_update_data(arguments)
        elif tool_name == "postgres_delete_data":
            return await self._postgres_delete_data(arguments)
        elif tool_name == "postgres_create_index":
            return await self._postgres_create_index(arguments)
        elif tool_name == "postgres_execute_transaction":
            return await self._postgres_execute_transaction(arguments)
        else:
            # 回退到基类工具
            return await super().handle_tool_call(tool_name, arguments)

    async def _postgres_execute_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        query = args.get("query", "")
        parameters = args.get("parameters", [])

        async with self.connection_pool.acquire() as conn:
            try:
                if parameters:
                    result = await conn.fetch(query, *parameters)
                else:
                    result = await conn.fetch(query)

                # 转换结果为JSON可序列化格式
                rows = []
                for row in result:
                    row_dict = {}
                    for key, value in row.items():
                        # 处理不能JSON序列化的类型
                        if hasattr(value, 'isoformat'):  # datetime等
                            row_dict[key] = value.isoformat()
                        else:
                            row_dict[key] = value
                    rows.append(row_dict)

                return {
                    "success": True,
                    "rows": rows,
                    "row_count": len(rows),
                    "query": query
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "query": query
                }

    async def _postgres_list_databases(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有数据库"""
        query = """
        SELECT datname as database_name,
               pg_encoding_to_char(encoding) as encoding,
               datcollate as collation,
               datctype as ctype
        FROM pg_database
        WHERE datistemplate = false
        ORDER BY datname;
        """

        return await self._postgres_execute_query({"query": query})

    async def _postgres_list_schemas(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有模式"""
        query = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schema_name;
        """

        return await self._postgres_execute_query({"query": query})

    async def _postgres_list_tables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有表"""
        schema = args.get("schema", "public")
        query = """
        SELECT table_name,
               table_schema as schema_name,
               table_type
        FROM information_schema.tables
        WHERE table_schema = $1
        ORDER BY table_name;
        """

        return await self._postgres_execute_query({
            "query": query,
            "parameters": [schema]
        })

    async def _postgres_create_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建新表"""
        table_name = args["table_name"]
        columns = args["columns"]
        schema = args.get("schema", "public")

        # 构建CREATE TABLE语句
        columns_sql = ",\n  ".join(columns)
        query = f'CREATE TABLE "{schema}"."{table_name}" (\n  {columns_sql}\n);'

        return await self._postgres_execute_query({"query": query})

    async def _postgres_drop_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除表"""
        table_name = args["table_name"]
        schema = args.get("schema", "public")

        query = f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE;'

        return await self._postgres_execute_query({"query": query})

    async def _postgres_insert_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """插入数据"""
        table_name = args["table_name"]
        data = args["data"]
        schema = args.get("schema", "public")

        if not data:
            return {"success": False, "error": "没有提供数据"}

        # 获取第一行数据的键作为列名
        first_row = data[0]
        columns = list(first_row.keys())
        columns_str = ', '.join([f'"{col}"' for col in columns])

        results = []
        for row in data:
            # 构建参数占位符 $1, $2, ...
            param_placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
            values = [row[col] for col in columns]

            query = f'INSERT INTO "{schema}"."{table_name}" ({columns_str}) VALUES ({param_placeholders});'

            result = await self._postgres_execute_query({
                "query": query,
                "parameters": values
            })
            results.append(result)

        return {
            "success": all(r["success"] for r in results),
            "inserted_rows": len(data),
            "results": results
        }

    async def _postgres_update_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据"""
        table_name = args["table_name"]
        set_clause = args["set_clause"]
        where_clause = args.get("where_clause", "TRUE")
        parameters = args.get("parameters", [])

        query = f'UPDATE "{table_name}" SET {set_clause} WHERE {where_clause};'

        return await self._postgres_execute_query({
            "query": query,
            "parameters": parameters
        })

    async def _postgres_delete_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除数据"""
        table_name = args["table_name"]
        where_clause = args.get("where_clause", "FALSE")
        parameters = args.get("parameters", [])

        if where_clause == "FALSE":
            return {"success": False, "error": "必须提供WHERE子句以防止误删除"}

        query = f'DELETE FROM "{table_name}" WHERE {where_clause};'

        return await self._postgres_execute_query({
            "query": query,
            "parameters": parameters
        })

    async def _postgres_create_index(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建索引"""
        index_name = args["index_name"]
        table_name = args["table_name"]
        columns = args["columns"]
        schema = args.get("schema", "public")
        unique = args.get("unique", False)

        columns_str = ', '.join(columns)
        unique_str = "UNIQUE " if unique else ""

        query = f'CREATE {unique_str}INDEX "{index_name}" ON "{schema}"."{table_name}" ({columns_str});'

        return await self._postgres_execute_query({"query": query})

    async def _postgres_execute_transaction(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行事务"""
        queries = args["queries"]

        results = []
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for query_info in queries:
                    query = query_info["query"]
                    parameters = query_info.get("parameters", [])

                    try:
                        if parameters:
                            result = await conn.fetch(query, *parameters)
                        else:
                            result = await conn.fetch(query)

                        results.append({
                            "success": True,
                            "query": query,
                            "row_count": len(result)
                        })
                    except Exception as e:
                        results.append({
                            "success": False,
                            "query": query,
                            "error": str(e)
                        })
                        # 事务中出错会回滚
                        raise

        return {
            "success": all(r["success"] for r in results),
            "results": results,
            "transaction_completed": True
        }

    async def close(self):
        """关闭连接池"""
        if self.connection_pool:
            await self.connection_pool.close()
            self.logger.info("PostgreSQL连接池已关闭")


def main():
    """主函数：启动PostgreSQL MCP服务器"""
    # 从环境变量获取连接字符串
    import os
    connection_string = os.getenv("POSTGRES_URL", "postgresql://localhost:5432/postgres")

    server = PostgreSQLMCP(connection_string)

    # 运行MCP服务器
    run_mcp_server(server)


if __name__ == "__main__":
    main()