"""
SQLite MCP服务器实现

基于aiosqlite提供异步SQLite数据库操作支持
"""

import asyncio
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional
import aiosqlite
from . import DatabaseMCPBase, DatabaseType, run_mcp_server


class SQLiteMCP(DatabaseMCPBase):
    """SQLite MCP服务器"""

    def __init__(self, database_path: str = None):
        super().__init__(DatabaseType.SQLITE)
        self.database_path = database_path or ":memory:"
        self.connection = None

    async def initialize(self):
        """初始化SQLite连接"""
        await super().initialize()

        # 创建SQLite连接
        self.connection = await aiosqlite.connect(self.database_path)

        # 启用外键约束
        await self.connection.execute("PRAGMA foreign_keys = ON")

        # 设置返回字典格式的行
        self.connection.row_factory = aiosqlite.Row

        self.logger.info(f"SQLite连接已创建: {self.database_path}")

    async def list_tools(self) -> List[Any]:
        """列出SQLite特定工具"""
        tools = await super().list_tools()

        # 添加SQLite特定工具
        sqlite_tools = [
            {
                "name": "sqlite_execute_query",
                "description": "执行SQLite SQL查询",
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
                "name": "sqlite_list_tables",
                "description": "列出所有表",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "sqlite_create_table",
                "description": "创建新表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "列定义，如 'id INTEGER PRIMARY KEY AUTOINCREMENT', 'name TEXT NOT NULL'"
                        }
                    },
                    "required": ["table_name", "columns"]
                }
            },
            {
                "name": "sqlite_drop_table",
                "description": "删除表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "sqlite_insert_data",
                "description": "插入数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "data": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "要插入的数据行"
                        }
                    },
                    "required": ["table_name", "data"]
                }
            },
            {
                "name": "sqlite_update_data",
                "description": "更新数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"},
                        "set_clause": {"type": "string", "description": "SET子句，如 'name = ?'"},
                        "where_clause": {"type": "string", "description": "WHERE子句，如 'id = ?'"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "参数值"}
                    },
                    "required": ["table_name", "set_clause"]
                }
            },
            {
                "name": "sqlite_delete_data",
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
                "name": "sqlite_create_index",
                "description": "创建索引",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index_name": {"type": "string", "description": "索引名"},
                        "table_name": {"type": "string", "description": "表名"},
                        "columns": {"type": "array", "items": {"type": "string"}, "description": "列名"},
                        "unique": {"type": "boolean", "description": "是否唯一索引"}
                    },
                    "required": ["index_name", "table_name", "columns"]
                }
            },
            {
                "name": "sqlite_execute_transaction",
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
                "name": "sqlite_vacuum",
                "description": "优化数据库文件",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "sqlite_backup",
                "description": "备份数据库",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "backup_path": {"type": "string", "description": "备份文件路径"}
                    },
                    "required": ["backup_path"]
                }
            },
            {
                "name": "sqlite_get_schema",
                "description": "获取数据库模式信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "表名"}
                    }
                }
            }
        ]

        # 合并工具列表
        from mcp.types import Tool
        all_tools = []
        for tool in tools:
            all_tools.append(tool)
        for tool_def in sqlite_tools:
            all_tools.append(Tool(**tool_def))

        return all_tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理SQLite工具调用"""
        self.logger.info(f"SQLite工具调用: {tool_name}")

        if tool_name == "sqlite_execute_query":
            return await self._sqlite_execute_query(arguments)
        elif tool_name == "sqlite_list_tables":
            return await self._sqlite_list_tables(arguments)
        elif tool_name == "sqlite_create_table":
            return await self._sqlite_create_table(arguments)
        elif tool_name == "sqlite_drop_table":
            return await self._sqlite_drop_table(arguments)
        elif tool_name == "sqlite_insert_data":
            return await self._sqlite_insert_data(arguments)
        elif tool_name == "sqlite_update_data":
            return await self._sqlite_update_data(arguments)
        elif tool_name == "sqlite_delete_data":
            return await self._sqlite_delete_data(arguments)
        elif tool_name == "sqlite_create_index":
            return await self._sqlite_create_index(arguments)
        elif tool_name == "sqlite_execute_transaction":
            return await self._sqlite_execute_transaction(arguments)
        elif tool_name == "sqlite_vacuum":
            return await self._sqlite_vacuum(arguments)
        elif tool_name == "sqlite_backup":
            return await self._sqlite_backup(arguments)
        elif tool_name == "sqlite_get_schema":
            return await self._sqlite_get_schema(arguments)
        else:
            # 回退到基类工具
            return await super().handle_tool_call(tool_name, arguments)

    async def _sqlite_execute_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        query = args.get("query", "")
        parameters = args.get("parameters", [])

        try:
            cursor = await self.connection.execute(query, parameters)

            # 如果是SELECT查询，获取结果
            if query.strip().upper().startswith("SELECT"):
                rows = await cursor.fetchall()

                # 转换为字典列表
                result_rows = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(cursor.description):
                        row_dict[col[0]] = row[i]
                    result_rows.append(row_dict)

                return {
                    "success": True,
                    "rows": result_rows,
                    "row_count": len(result_rows),
                    "query": query
                }
            else:
                # 对于非SELECT查询，获取影响的行数
                await self.connection.commit()
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

    async def _sqlite_list_tables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有表"""
        query = """
        SELECT name as table_name, sql
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
        """

        return await self._sqlite_execute_query({"query": query})

    async def _sqlite_create_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建新表"""
        table_name = args["table_name"]
        columns = args["columns"]

        # 构建CREATE TABLE语句
        columns_sql = ",\n  ".join(columns)
        query = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  {columns_sql}\n);'

        return await self._sqlite_execute_query({"query": query})

    async def _sqlite_drop_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除表"""
        table_name = args["table_name"]

        query = f'DROP TABLE IF EXISTS "{table_name}";'

        return await self._sqlite_execute_query({"query": query})

    async def _sqlite_insert_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """插入数据"""
        table_name = args["table_name"]
        data = args["data"]

        if not data:
            return {"success": False, "error": "没有提供数据"}

        # 获取第一行数据的键作为列名
        first_row = data[0]
        columns = list(first_row.keys())
        columns_str = ', '.join([f'"{col}"' for col in columns])

        results = []
        for row in data:
            # 构建参数占位符 ?, ?, ...
            param_placeholders = ', '.join(['?' for _ in columns])
            values = [row[col] for col in columns]

            query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({param_placeholders});'

            result = await self._sqlite_execute_query({
                "query": query,
                "parameters": values
            })
            results.append(result)

        return {
            "success": all(r["success"] for r in results),
            "inserted_rows": len(data),
            "results": results
        }

    async def _sqlite_update_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据"""
        table_name = args["table_name"]
        set_clause = args["set_clause"]
        where_clause = args.get("where_clause", "1=1")
        parameters = args.get("parameters", [])

        query = f'UPDATE "{table_name}" SET {set_clause} WHERE {where_clause};'

        return await self._sqlite_execute_query({
            "query": query,
            "parameters": parameters
        })

    async def _sqlite_delete_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除数据"""
        table_name = args["table_name"]
        where_clause = args.get("where_clause", "1=0")  # 默认不删除任何数据
        parameters = args.get("parameters", [])

        if where_clause == "1=0":
            return {"success": False, "error": "必须提供WHERE子句以防止误删除"}

        query = f'DELETE FROM "{table_name}" WHERE {where_clause};'

        return await self._sqlite_execute_query({
            "query": query,
            "parameters": parameters
        })

    async def _sqlite_create_index(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建索引"""
        index_name = args["index_name"]
        table_name = args["table_name"]
        columns = args["columns"]
        unique = args.get("unique", False)

        columns_str = ', '.join(columns)
        unique_str = "UNIQUE " if unique else ""

        query = f'CREATE {unique_str}INDEX "{index_name}" ON "{table_name}" ({columns_str});'

        return await self._sqlite_execute_query({"query": query})

    async def _sqlite_execute_transaction(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行事务"""
        queries = args["queries"]

        results = []
        try:
            async with self.connection.cursor() as cursor:
                for query_info in queries:
                    query = query_info["query"]
                    parameters = query_info.get("parameters", [])

                    try:
                        await cursor.execute(query, parameters)

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

                await self.connection.commit()

            return {
                "success": all(r["success"] for r in results),
                "results": results,
                "transaction_completed": True
            }
        except Exception as e:
            await self.connection.rollback()
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "transaction_completed": False
            }

    async def _sqlite_vacuum(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """优化数据库文件"""
        try:
            await self.connection.execute("VACUUM;")
            await self.connection.commit()

            return {
                "success": True,
                "message": "数据库优化完成"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _sqlite_backup(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """备份数据库"""
        backup_path = args["backup_path"]

        try:
            # 确保备份目录存在
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # 备份当前数据库到新文件
            backup_conn = await aiosqlite.connect(backup_path)
            await self.connection.backup(backup_conn)
            await backup_conn.close()

            return {
                "success": True,
                "message": f"数据库备份完成: {backup_path}",
                "backup_path": backup_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "backup_path": backup_path
            }

    async def _sqlite_get_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取数据库模式信息"""
        table_name = args.get("table_name")

        if table_name:
            # 获取特定表的模式
            query = f"""
            SELECT name, type, pk as is_primary_key, [notnull] as is_not_null, dflt_value as default_value
            FROM pragma_table_info('{table_name}')
            ORDER BY cid;
            """

            table_info = await self._sqlite_execute_query({"query": query})

            if table_info["success"]:
                table_info["table_name"] = table_name

            return table_info
        else:
            # 获取所有表的模式
            tables_result = await self._sqlite_list_tables({})

            if not tables_result["success"]:
                return tables_result

            all_schemas = []
            for table_row in tables_result["rows"]:
                table_name = table_row["table_name"]

                # 获取表结构
                query = f"""
                SELECT name, type, pk as is_primary_key, [notnull] as is_not_null, dflt_value as default_value
                FROM pragma_table_info('{table_name}')
                ORDER BY cid;
                """

                table_schema = await self._sqlite_execute_query({"query": query})

                if table_schema["success"]:
                    all_schemas.append({
                        "table_name": table_name,
                        "sql": table_row.get("sql", ""),
                        "columns": table_schema["rows"]
                    })

            return {
                "success": True,
                "schemas": all_schemas,
                "table_count": len(all_schemas)
            }

    async def close(self):
        """关闭SQLite连接"""
        if self.connection:
            await self.connection.close()
            self.logger.info("SQLite连接已关闭")


def main():
    """主函数：启动SQLite MCP服务器"""
    # 从环境变量获取数据库路径
    import os
    database_path = os.getenv("SQLITE_DB_PATH", ":memory:")

    server = SQLiteMCP(database_path)

    # 运行MCP服务器
    run_mcp_server(server)


if __name__ == "__main__":
    main()