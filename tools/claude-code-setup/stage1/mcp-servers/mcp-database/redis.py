"""
Redis MCP服务器实现

基于aioredis提供高性能Redis数据库操作支持
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import aioredis
from . import DatabaseMCPBase, DatabaseType, run_mcp_server


class RedisMCP(DatabaseMCPBase):
    """Redis MCP服务器"""

    def __init__(self, connection_string: str = None):
        super().__init__(DatabaseType.REDIS)
        self.connection_string = connection_string or "redis://localhost:6379/0"
        self.redis_client = None

    async def initialize(self):
        """初始化Redis连接"""
        await super().initialize()

        # 创建Redis连接
        self.redis_client = await aioredis.from_url(
            self.connection_string,
            decode_responses=True,
            max_connections=10
        )
        self.logger.info(f"Redis连接已创建: {self.connection_string}")

    async def list_tools(self) -> List[Any]:
        """列出Redis特定工具"""
        tools = await super().list_tools()

        # 添加Redis特定工具
        redis_tools = [
            {
                "name": "redis_set",
                "description": "设置Redis键值",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"},
                        "value": {"type": "string", "description": "值"},
                        "expire": {"type": "integer", "description": "过期时间(秒)"}
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "redis_get",
                "description": "获取Redis键值",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "redis_delete",
                "description": "删除Redis键",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "redis_keys",
                "description": "查找匹配模式的键",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "键模式，如 'user:*'"}
                    }
                }
            },
            {
                "name": "redis_hash_set",
                "description": "设置Redis哈希字段",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "哈希键名"},
                        "field": {"type": "string", "description": "字段名"},
                        "value": {"type": "string", "description": "字段值"}
                    },
                    "required": ["key", "field", "value"]
                }
            },
            {
                "name": "redis_hash_get",
                "description": "获取Redis哈希字段",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "哈希键名"},
                        "field": {"type": "string", "description": "字段名"}
                    },
                    "required": ["key", "field"]
                }
            },
            {
                "name": "redis_list_push",
                "description": "向Redis列表添加元素",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "列表键名"},
                        "values": {"type": "array", "items": {"type": "string"}, "description": "要添加的值"},
                        "side": {"type": "string", "description": "添加位置: left|right", "enum": ["left", "right"]}
                    },
                    "required": ["key", "values"]
                }
            },
            {
                "name": "redis_list_range",
                "description": "获取Redis列表范围",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "列表键名"},
                        "start": {"type": "integer", "description": "起始索引"},
                        "stop": {"type": "integer", "description": "结束索引"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "redis_set_add",
                "description": "向Redis集合添加元素",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "集合键名"},
                        "members": {"type": "array", "items": {"type": "string"}, "description": "成员值"}
                    },
                    "required": ["key", "members"]
                }
            },
            {
                "name": "redis_set_members",
                "description": "获取Redis集合所有成员",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "集合键名"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "redis_info",
                "description": "获取Redis服务器信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "redis_pipeline",
                "description": "执行Redis管道操作",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "commands": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string", "description": "Redis命令，如 'SET'"},
                                    "args": {"type": "array", "items": {"type": "string"}, "description": "命令参数"}
                                }
                            },
                            "description": "要执行的命令列表"
                        }
                    },
                    "required": ["commands"]
                }
            }
        ]

        # 合并工具列表
        from mcp.types import Tool
        all_tools = []
        for tool in tools:
            all_tools.append(tool)
        for tool_def in redis_tools:
            all_tools.append(Tool(**tool_def))

        return all_tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理Redis工具调用"""
        self.logger.info(f"Redis工具调用: {tool_name}")

        if tool_name == "redis_set":
            return await self._redis_set(arguments)
        elif tool_name == "redis_get":
            return await self._redis_get(arguments)
        elif tool_name == "redis_delete":
            return await self._redis_delete(arguments)
        elif tool_name == "redis_keys":
            return await self._redis_keys(arguments)
        elif tool_name == "redis_hash_set":
            return await self._redis_hash_set(arguments)
        elif tool_name == "redis_hash_get":
            return await self._redis_hash_get(arguments)
        elif tool_name == "redis_list_push":
            return await self._redis_list_push(arguments)
        elif tool_name == "redis_list_range":
            return await self._redis_list_range(arguments)
        elif tool_name == "redis_set_add":
            return await self._redis_set_add(arguments)
        elif tool_name == "redis_set_members":
            return await self._redis_set_members(arguments)
        elif tool_name == "redis_info":
            return await self._redis_info(arguments)
        elif tool_name == "redis_pipeline":
            return await self._redis_pipeline(arguments)
        else:
            # 回退到基类工具
            return await super().handle_tool_call(tool_name, arguments)

    async def _redis_set(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """设置键值"""
        key = args["key"]
        value = args["value"]
        expire = args.get("expire")

        try:
            if expire:
                await self.redis_client.set(key, value, ex=expire)
            else:
                await self.redis_client.set(key, value)

            return {
                "success": True,
                "message": f"键 '{key}' 设置成功",
                "expire": expire
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取键值"""
        key = args["key"]

        try:
            value = await self.redis_client.get(key)
            return {
                "success": True,
                "key": key,
                "value": value,
                "exists": value is not None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除键"""
        key = args["key"]

        try:
            deleted = await self.redis_client.delete(key)
            return {
                "success": True,
                "key": key,
                "deleted": bool(deleted)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_keys(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查找键"""
        pattern = args.get("pattern", "*")

        try:
            keys = await self.redis_client.keys(pattern)
            return {
                "success": True,
                "pattern": pattern,
                "keys": keys,
                "count": len(keys)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern
            }

    async def _redis_hash_set(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """设置哈希字段"""
        key = args["key"]
        field = args["field"]
        value = args["value"]

        try:
            await self.redis_client.hset(key, field, value)
            return {
                "success": True,
                "message": f"哈希 '{key}' 字段 '{field}' 设置成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key,
                "field": field
            }

    async def _redis_hash_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取哈希字段"""
        key = args["key"]
        field = args["field"]

        try:
            value = await self.redis_client.hget(key, field)
            return {
                "success": True,
                "key": key,
                "field": field,
                "value": value,
                "exists": value is not None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key,
                "field": field
            }

    async def _redis_list_push(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """向列表添加元素"""
        key = args["key"]
        values = args["values"]
        side = args.get("side", "right")

        try:
            if side == "left":
                result = await self.redis_client.lpush(key, *values)
            else:
                result = await self.redis_client.rpush(key, *values)

            return {
                "success": True,
                "key": key,
                "side": side,
                "values_added": len(values),
                "list_length": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_list_range(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取列表范围"""
        key = args["key"]
        start = args.get("start", 0)
        stop = args.get("stop", -1)

        try:
            values = await self.redis_client.lrange(key, start, stop)
            return {
                "success": True,
                "key": key,
                "start": start,
                "stop": stop,
                "values": values,
                "count": len(values)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_set_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """向集合添加元素"""
        key = args["key"]
        members = args["members"]

        try:
            added = await self.redis_client.sadd(key, *members)
            return {
                "success": True,
                "key": key,
                "members_added": added,
                "total_members": len(members)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_set_members(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取集合成员"""
        key = args["key"]

        try:
            members = await self.redis_client.smembers(key)
            return {
                "success": True,
                "key": key,
                "members": list(members),
                "count": len(members)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key
            }

    async def _redis_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取Redis服务器信息"""
        try:
            info = await self.redis_client.info()
            return {
                "success": True,
                "info": info
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _redis_pipeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行管道操作"""
        commands = args["commands"]

        try:
            pipeline = self.redis_client.pipeline()
            results = []

            for cmd in commands:
                command = cmd["command"].lower()
                command_args = cmd.get("args", [])

                # 调用对应的管道方法
                if command == "set":
                    pipeline.set(*command_args)
                elif command == "get":
                    pipeline.get(*command_args)
                elif command == "delete":
                    pipeline.delete(*command_args)
                elif command == "hset":
                    pipeline.hset(*command_args)
                elif command == "hget":
                    pipeline.hget(*command_args)
                elif command == "lpush":
                    pipeline.lpush(*command_args)
                elif command == "rpush":
                    pipeline.rpush(*command_args)
                elif command == "lrange":
                    pipeline.lrange(*command_args)
                elif command == "sadd":
                    pipeline.sadd(*command_args)
                elif command == "smembers":
                    pipeline.smembers(*command_args)
                else:
                    # 通用方法调用
                    getattr(pipeline, command)(*command_args)

            # 执行管道
            pipe_results = await pipeline.execute()

            return {
                "success": True,
                "commands_executed": len(commands),
                "results": pipe_results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "commands": len(commands)
            }

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Redis连接已关闭")


def main():
    """主函数：启动Redis MCP服务器"""
    # 从环境变量获取连接字符串
    import os
    connection_string = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    server = RedisMCP(connection_string)

    # 运行MCP服务器
    run_mcp_server(server)


if __name__ == "__main__":
    main()