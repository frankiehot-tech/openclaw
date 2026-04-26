#!/usr/bin/env python3
"""
AI Assistant MCP 工具服务器 - 为百炼 PRO 模型提供完整工具能力。
实现 AI Assistant 核心工具：Bash、Read、Write、Edit、Glob、Grep、WebFetch。
"""

import asyncio
import glob
import json
import os
import subprocess
import sys
from typing import Any

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
except ImportError:
    print("正在安装 MCP SDK...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp>=1.0.0"])
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# 创建服务器实例
app = Server("ai-tools-server")


# =============================================================================
# 工具定义
# =============================================================================

TOOLS = [
    Tool(
        name="Bash",
        description="Execute a bash command in the shell environment.",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute.",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of why this command is being run.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default: 30).",
                },
            },
            "required": ["command"],
        },
    ),
    Tool(
        name="Read",
        description="Read the contents of a file at the specified path.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read.",
                },
                "offset": {
                    "type": "number",
                    "description": "Line offset to start reading from (0-based).",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of lines to read.",
                },
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="Write",
        description="Write content to a file, creating it if it doesn't exist.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
        },
    ),
    Tool(
        name="Edit",
        description="Apply targeted edits to a file using SEARCH/REPLACE blocks.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit.",
                },
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "oldText": {
                                "type": "string",
                                "description": "Text to search for.",
                            },
                            "newText": {
                                "type": "string",
                                "description": "Text to replace with.",
                            },
                        },
                        "required": ["oldText", "newText"],
                    },
                    "description": "List of search/replace edits.",
                },
            },
            "required": ["file_path", "edits"],
        },
    ),
    Tool(
        name="Glob",
        description="Find files matching a glob pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g., '*.py').",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current).",
                },
            },
            "required": ["pattern"],
        },
    ),
    Tool(
        name="Grep",
        description="Search for a pattern in files using regex.",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in.",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output mode (default: content).",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Filter by file glob pattern.",
                },
            },
            "required": ["pattern"],
        },
    ),
    Tool(
        name="WebFetch",
        description="Fetch content from a URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch.",
                },
                "max_length": {
                    "type": "number",
                    "description": "Maximum characters to return (default: 5000).",
                },
            },
            "required": ["url"],
        },
    ),
]


# =============================================================================
# 工具实现
# =============================================================================

async def execute_bash(command: str, timeout: float = 30) -> dict:
    """执行 Bash 命令。"""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            return {
                "output": stdout_str,
                "error": stderr_str,
                "exit_code": proc.returncode,
            }
        except asyncio.TimeoutError:
            proc.kill()
            return {"output": "", "error": f"Command timed out after {timeout}s", "exit_code": -1}
    except Exception as e:
        return {"output": "", "error": str(e), "exit_code": -1}


async def read_file(file_path: str, offset: int = 0, limit: int = 1000) -> dict:
    """读取文件内容。"""
    try:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return {"error": f"File not found: {file_path}", "content": ""}
        if not os.path.isfile(abs_path):
            return {"error": f"Not a file: {file_path}", "content": ""}
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total_lines = len(lines)
        start = min(offset, total_lines)
        end = min(start + limit, total_lines)
        selected = lines[start:end]
        result = "".join(selected)
        return {
            "content": result,
            "total_lines": total_lines,
            "lines_read": end - start,
            "offset": start,
        }
    except Exception as e:
        return {"error": str(e), "content": ""}


async def write_file(file_path: str, content: str) -> dict:
    """写入文件。"""
    try:
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": abs_path, "bytes_written": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def edit_file(file_path: str, edits: list) -> dict:
    """编辑文件。"""
    try:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        applied = 0
        for edit in edits:
            old_text = edit["oldText"]
            new_text = edit["newText"]
            if old_text in content:
                content = content.replace(old_text, new_text, 1)
                applied += 1
            else:
                return {"success": False, "error": f"Text not found: {old_text[:50]}...", "applied": applied}
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "applied": applied, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def glob_files(pattern: str, path: str = ".") -> dict:
    """Glob 查找文件。"""
    try:
        search_path = os.path.abspath(path)
        full_pattern = os.path.join(search_path, pattern)
        matches = glob.glob(full_pattern, recursive=True)
        # 过滤只保留文件
        files = [m for m in matches if os.path.isfile(m)]
        dirs = [m for m in matches if os.path.isdir(m)]
        return {
            "files": files[:100],
            "directories": dirs[:50],
            "total_files": len(files),
            "total_dirs": len(dirs),
        }
    except Exception as e:
        return {"error": str(e), "files": [], "directories": []}


async def grep_search(pattern: str, path: str = ".", output_mode: str = "content", file_pattern: str = None) -> dict:
    """Grep 搜索。"""
    try:
        import re
        search_path = os.path.abspath(path)
        results = []
        regex = re.compile(pattern)
        for root, dirs, files in os.walk(search_path):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".git")]
            for fname in files:
                if file_pattern:
                    import fnmatch
                    if not fnmatch.fnmatch(fname, file_pattern):
                        continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                if output_mode == "content":
                                    results.append({"file": fpath, "line": line_num, "content": line.rstrip()})
                                elif output_mode == "count":
                                    results.append({"file": fpath, "count": 1})
                                elif output_mode == "files_with_matches":
                                    results.append({"file": fpath})
                                    break
                except (PermissionError, OSError):
                    pass
                if output_mode == "files_with_matches" and len(results) >= 100:
                    break
        return {"results": results[:100], "total_matches": len(results)}
    except Exception as e:
        return {"error": str(e), "results": []}


async def web_fetch(url: str, max_length: int = 5000) -> dict:
    """获取网页内容。"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")
        # 简单提取文本内容
        import re
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()
        return {
            "content": text[:max_length],
            "total_length": len(text),
            "url": url,
        }
    except Exception as e:
        return {"error": str(e), "content": ""}


# =============================================================================
# MCP 路由
# =============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """返回可用工具列表。"""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用。"""
    result = {}

    if name == "Bash":
        result = await execute_bash(
            arguments.get("command", ""),
            arguments.get("timeout", 30),
        )
    elif name == "Read":
        result = await read_file(
            arguments.get("file_path", ""),
            arguments.get("offset", 0),
            arguments.get("limit", 1000),
        )
    elif name == "Write":
        result = await write_file(
            arguments.get("file_path", ""),
            arguments.get("content", ""),
        )
    elif name == "Edit":
        result = await edit_file(
            arguments.get("file_path", ""),
            arguments.get("edits", []),
        )
    elif name == "Glob":
        result = await glob_files(
            arguments.get("pattern", ""),
            arguments.get("path", "."),
        )
    elif name == "Grep":
        result = await grep_search(
            arguments.get("pattern", ""),
            arguments.get("path", "."),
            arguments.get("output_mode", "content"),
            arguments.get("file_pattern"),
        )
    elif name == "WebFetch":
        result = await web_fetch(
            arguments.get("url", ""),
            arguments.get("max_length", 5000),
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    # 格式化为 JSON 文本响应
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# =============================================================================
# 启动
# =============================================================================

async def main():
    """启动 MCP 服务器。"""
    print("🚀 AI Tools MCP Server 启动中...", file=sys.stderr)
    print(f"   工作目录: {os.getcwd()}", file=sys.stderr)
    print(f"   Python: {sys.version}", file=sys.stderr)
    print("   工具: Bash, Read, Write, Edit, Glob, Grep, WebFetch", file=sys.stderr)
    print("   按 Ctrl+C 停止\n", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())