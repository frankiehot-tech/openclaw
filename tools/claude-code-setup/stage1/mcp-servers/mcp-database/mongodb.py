"""
MongoDB MCP服务器实现

基于motor提供异步MongoDB数据库操作支持
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId, json_util
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from . import DatabaseMCPBase, DatabaseType, run_mcp_server


class MongoDBMCP(DatabaseMCPBase):
    """MongoDB MCP服务器"""

    def __init__(self, connection_string: str = None):
        super().__init__(DatabaseType.MONGODB)
        self.connection_string = connection_string or "mongodb://localhost:27017"
        self.client = None
        self.db = None

    async def initialize(self):
        """初始化MongoDB连接"""
        await super().initialize()

        # 创建MongoDB客户端和数据库连接
        self.client = AsyncIOMotorClient(self.connection_string)
        # 默认使用第一个数据库名
        db_name = self.connection_string.split('/')[-1] if '/' in self.connection_string else 'test'
        self.db = self.client[db_name]

        self.logger.info(f"MongoDB连接已创建: {self.connection_string}, 数据库: {db_name}")

    async def list_tools(self) -> List[Any]:
        """列出MongoDB特定工具"""
        tools = await super().list_tools()

        # 添加MongoDB特定工具
        mongodb_tools = [
            {
                "name": "mongodb_list_collections",
                "description": "列出所有集合",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "mongodb_find_documents",
                "description": "查询文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询过滤器"},
                        "limit": {"type": "integer", "description": "返回文档数量限制"},
                        "skip": {"type": "integer", "description": "跳过文档数"},
                        "sort": {"type": "array", "items": {"type": "string"}, "description": "排序字段"}
                    },
                    "required": ["collection"]
                }
            },
            {
                "name": "mongodb_insert_one",
                "description": "插入单个文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "document": {"type": "object", "description": "要插入的文档"}
                    },
                    "required": ["collection", "document"]
                }
            },
            {
                "name": "mongodb_insert_many",
                "description": "插入多个文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "documents": {"type": "array", "items": {"type": "object"}, "description": "要插入的文档列表"}
                    },
                    "required": ["collection", "documents"]
                }
            },
            {
                "name": "mongodb_update_one",
                "description": "更新单个文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询过滤器"},
                        "update": {"type": "object", "description": "更新操作"},
                        "upsert": {"type": "boolean", "description": "如果不存在是否插入"}
                    },
                    "required": ["collection", "filter", "update"]
                }
            },
            {
                "name": "mongodb_update_many",
                "description": "更新多个文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询过滤器"},
                        "update": {"type": "object", "description": "更新操作"},
                        "upsert": {"type": "boolean", "description": "如果不存在是否插入"}
                    },
                    "required": ["collection", "filter", "update"]
                }
            },
            {
                "name": "mongodb_delete_one",
                "description": "删除单个文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询过滤器"}
                    },
                    "required": ["collection", "filter"]
                }
            },
            {
                "name": "mongodb_delete_many",
                "description": "删除多个文档",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询过滤器"}
                    },
                    "required": ["collection", "filter"]
                }
            },
            {
                "name": "mongodb_create_index",
                "description": "创建索引",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "keys": {"type": "object", "description": "索引键和方向，如 {'name': 1, 'age': -1}'"},
                        "options": {"type": "object", "description": "索引选项"}
                    },
                    "required": ["collection", "keys"]
                }
            },
            {
                "name": "mongodb_drop_collection",
                "description": "删除集合",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"}
                    },
                    "required": ["collection"]
                }
            },
            {
                "name": "mongodb_aggregate",
                "description": "执行聚合管道",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "pipeline": {"type": "array", "items": {"type": "object"}, "description": "聚合管道阶段"}
                    },
                    "required": ["collection", "pipeline"]
                }
            },
            {
                "name": "mongodb_count_documents",
                "description": "统计文档数量",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询过滤器"}
                    },
                    "required": ["collection"]
                }
            }
        ]

        # 合并工具列表
        from mcp.types import Tool
        all_tools = []
        for tool in tools:
            all_tools.append(tool)
        for tool_def in mongodb_tools:
            all_tools.append(Tool(**tool_def))

        return all_tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理MongoDB工具调用"""
        self.logger.info(f"MongoDB工具调用: {tool_name}")

        if tool_name == "mongodb_list_collections":
            return await self._mongodb_list_collections(arguments)
        elif tool_name == "mongodb_find_documents":
            return await self._mongodb_find_documents(arguments)
        elif tool_name == "mongodb_insert_one":
            return await self._mongodb_insert_one(arguments)
        elif tool_name == "mongodb_insert_many":
            return await self._mongodb_insert_many(arguments)
        elif tool_name == "mongodb_update_one":
            return await self._mongodb_update_one(arguments)
        elif tool_name == "mongodb_update_many":
            return await self._mongodb_update_many(arguments)
        elif tool_name == "mongodb_delete_one":
            return await self._mongodb_delete_one(arguments)
        elif tool_name == "mongodb_delete_many":
            return await self._mongodb_delete_many(arguments)
        elif tool_name == "mongodb_create_index":
            return await self._mongodb_create_index(arguments)
        elif tool_name == "mongodb_drop_collection":
            return await self._mongodb_drop_collection(arguments)
        elif tool_name == "mongodb_aggregate":
            return await self._mongodb_aggregate(arguments)
        elif tool_name == "mongodb_count_documents":
            return await self._mongodb_count_documents(arguments)
        else:
            # 回退到基类工具
            return await super().handle_tool_call(tool_name, arguments)

    def _convert_object_id(self, obj):
        """转换ObjectId为字符串以便JSON序列化"""
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_object_id(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_object_id(item) for item in obj]
        else:
            return obj

    async def _mongodb_list_collections(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有集合"""
        try:
            collections = await self.db.list_collection_names()
            return {
                "success": True,
                "collections": collections,
                "count": len(collections)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _mongodb_find_documents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查询文档"""
        collection_name = args["collection"]
        filter_query = args.get("filter", {})
        limit = args.get("limit", 100)
        skip = args.get("skip", 0)
        sort_fields = args.get("sort", [])

        try:
            collection = self.db[collection_name]
            cursor = collection.find(filter_query).skip(skip).limit(limit)

            if sort_fields:
                sort_dict = {}
                for field in sort_fields:
                    if field.startswith("-"):
                        sort_dict[field[1:]] = -1
                    else:
                        sort_dict[field] = 1
                cursor = cursor.sort(list(sort_dict.items()))

            documents = await cursor.to_list(length=limit)

            # 转换ObjectId为字符串
            converted_docs = self._convert_object_id(documents)

            return {
                "success": True,
                "collection": collection_name,
                "documents": converted_docs,
                "count": len(documents),
                "filter": filter_query,
                "limit": limit,
                "skip": skip
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_insert_one(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """插入单个文档"""
        collection_name = args["collection"]
        document = args["document"]

        try:
            collection = self.db[collection_name]
            result = await collection.insert_one(document)

            return {
                "success": True,
                "collection": collection_name,
                "inserted_id": str(result.inserted_id),
                "document": self._convert_object_id(document)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_insert_many(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """插入多个文档"""
        collection_name = args["collection"]
        documents = args["documents"]

        try:
            collection = self.db[collection_name]
            result = await collection.insert_many(documents)

            inserted_ids = [str(id) for id in result.inserted_ids]

            return {
                "success": True,
                "collection": collection_name,
                "inserted_ids": inserted_ids,
                "inserted_count": len(inserted_ids),
                "documents": self._convert_object_id(documents)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_update_one(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """更新单个文档"""
        collection_name = args["collection"]
        filter_query = args["filter"]
        update_operation = args["update"]
        upsert = args.get("upsert", False)

        try:
            collection = self.db[collection_name]
            result = await collection.update_one(filter_query, update_operation, upsert=upsert)

            return {
                "success": True,
                "collection": collection_name,
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": str(result.upserted_id) if result.upserted_id else None,
                "upsert": upsert
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_update_many(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """更新多个文档"""
        collection_name = args["collection"]
        filter_query = args["filter"]
        update_operation = args["update"]
        upsert = args.get("upsert", False)

        try:
            collection = self.db[collection_name]
            result = await collection.update_many(filter_query, update_operation, upsert=upsert)

            return {
                "success": True,
                "collection": collection_name,
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": str(result.upserted_id) if result.upserted_id else None,
                "upsert": upsert
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_delete_one(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除单个文档"""
        collection_name = args["collection"]
        filter_query = args["filter"]

        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(filter_query)

            return {
                "success": True,
                "collection": collection_name,
                "deleted_count": result.deleted_count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_delete_many(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除多个文档"""
        collection_name = args["collection"]
        filter_query = args["filter"]

        try:
            collection = self.db[collection_name]
            result = await collection.delete_many(filter_query)

            return {
                "success": True,
                "collection": collection_name,
                "deleted_count": result.deleted_count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_create_index(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建索引"""
        collection_name = args["collection"]
        keys = args["keys"]
        options = args.get("options", {})

        try:
            collection = self.db[collection_name]
            index_name = await collection.create_index(keys, **options)

            return {
                "success": True,
                "collection": collection_name,
                "index_name": index_name,
                "keys": keys,
                "options": options
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_drop_collection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除集合"""
        collection_name = args["collection"]

        try:
            result = await self.db.drop_collection(collection_name)

            return {
                "success": True,
                "collection": collection_name,
                "dropped": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_aggregate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行聚合管道"""
        collection_name = args["collection"]
        pipeline = args["pipeline"]

        try:
            collection = self.db[collection_name]
            cursor = collection.aggregate(pipeline)
            documents = await cursor.to_list(length=None)

            # 转换ObjectId为字符串
            converted_docs = self._convert_object_id(documents)

            return {
                "success": True,
                "collection": collection_name,
                "documents": converted_docs,
                "count": len(documents),
                "pipeline": pipeline
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def _mongodb_count_documents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """统计文档数量"""
        collection_name = args["collection"]
        filter_query = args.get("filter", {})

        try:
            collection = self.db[collection_name]
            count = await collection.count_documents(filter_query)

            return {
                "success": True,
                "collection": collection_name,
                "count": count,
                "filter": filter_query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "collection": collection_name
            }

    async def close(self):
        """关闭MongoDB连接"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB连接已关闭")


def main():
    """主函数：启动MongoDB MCP服务器"""
    # 从环境变量获取连接字符串
    import os
    connection_string = os.getenv("MONGODB_URL", "mongodb://localhost:27017/test")

    server = MongoDBMCP(connection_string)

    # 运行MCP服务器
    run_mcp_server(server)


if __name__ == "__main__":
    main()