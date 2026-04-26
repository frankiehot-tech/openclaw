"""
AI Assistant 云服务MCP框架核心库

提供通用的云服务操作接口，支持多种云平台和容器服务：
- AWS (EC2, S3, RDS, Lambda, CloudFormation)
- Docker (容器、镜像、网络、卷)
- Kubernetes (集群、部署、服务、配置)
- Serverless框架 (AWS Lambda, Vercel)
- 云存储 (S3, MinIO兼容存储)
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from enum import Enum
import base64

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client import stdio
    from mcp.types import (
        CallToolRequest,
        ListToolsRequest,
        Tool,
        TextContent,
        ImageContent
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("警告: mcp包未安装，请运行: pip install mcp")


class CloudServiceType(str, Enum):
    """支持的云服务类型"""
    AWS = "aws"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    SERVERLESS = "serverless"
    STORAGE = "storage"


class CredentialManager:
    """云服务凭据管理器"""

    def __init__(self):
        self._credentials = {}
        self._encryption_key = os.environ.get("AI_ENCRYPTION_KEY", "default-key")

    async def get_aws_credentials(self) -> Dict[str, str]:
        """获取AWS凭据"""
        # 优先级: 环境变量 > 配置文件 > IAM角色
        aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_session_token = os.environ.get("AWS_SESSION_TOKEN")
        aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

        if aws_access_key_id and aws_secret_access_key:
            return {
                "access_key_id": aws_access_key_id,
                "secret_access_key": aws_secret_access_key,
                "session_token": aws_session_token,
                "region": aws_region
            }

        # 检查AWS配置文件
        aws_profile = os.environ.get("AWS_PROFILE", "default")
        aws_config_path = os.path.expanduser("~/.aws/credentials")

        if os.path.exists(aws_config_path):
            # 简化实现，实际应该使用boto3的共享凭据文件
            return {
                "profile": aws_profile,
                "region": aws_region
            }

        # 检查IAM角色（EC2实例元数据）
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/") as resp:
                    if resp.status == 200:
                        role_name = await resp.text()
                        async with session.get(f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role_name}") as role_resp:
                            if role_resp.status == 200:
                                credentials = await role_resp.json()
                                return {
                                    "access_key_id": credentials.get("AccessKeyId"),
                                    "secret_access_key": credentials.get("SecretAccessKey"),
                                    "session_token": credentials.get("Token"),
                                    "region": aws_region
                                }
        except:
            pass

        raise ValueError("未找到有效的AWS凭据")

    async def get_docker_config(self) -> Dict[str, Any]:
        """获取Docker配置"""
        docker_host = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")

        # 检查TLS配置
        docker_tls_verify = os.environ.get("DOCKER_TLS_VERIFY", "0") == "1"
        docker_cert_path = os.environ.get("DOCKER_CERT_PATH")

        config = {
            "base_url": docker_host,
            "tls": docker_tls_verify,
        }

        if docker_tls_verify and docker_cert_path:
            config.update({
                "tls_ca_cert": os.path.join(docker_cert_path, "ca.pem"),
                "tls_client_cert": os.path.join(docker_cert_path, "cert.pem"),
                "tls_client_key": os.path.join(docker_cert_path, "key.pem")
            })

        return config

    async def get_kubernetes_config(self) -> Dict[str, Any]:
        """获取Kubernetes配置"""
        kubeconfig_path = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config"))

        if os.path.exists(kubeconfig_path):
            return {"kubeconfig_path": kubeconfig_path}

        # 检查集群内配置（Pod中运行）
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
                token = f.read().strip()

            with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
                namespace = f.read().strip()

            with open("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt") as f:
                ca_cert = f.read()

            return {
                "host": "https://kubernetes.default.svc",
                "token": token,
                "namespace": namespace,
                "ca_cert": ca_cert,
                "verify_ssl": True
            }

        raise ValueError("未找到有效的Kubernetes配置")

    async def encrypt_credential(self, credential: str) -> str:
        """加密凭据"""
        # 简化实现，实际应该使用强加密算法
        encoded = base64.b64encode(credential.encode()).decode()
        return f"encrypted:{encoded}"

    async def decrypt_credential(self, encrypted_credential: str) -> str:
        """解密凭据"""
        if encrypted_credential.startswith("encrypted:"):
            encoded = encrypted_credential[10:]
            return base64.b64decode(encoded).decode()
        return encrypted_credential


class CloudServiceMCPBase:
    """云服务MCP基类"""

    def __init__(self, service_type: CloudServiceType):
        self.service_type = service_type
        self.credential_manager = CredentialManager()
        self.logger = logging.getLogger(f"cloud-mcp.{service_type}")
        self._clients = {}

    async def initialize(self):
        """初始化云服务客户端"""
        self.logger.info(f"初始化 {self.service_type.value} MCP服务器")

        if self.service_type == CloudServiceType.AWS:
            await self._initialize_aws_client()
        elif self.service_type == CloudServiceType.DOCKER:
            await self._initialize_docker_client()
        elif self.service_type == CloudServiceType.KUBERNETES:
            await self._initialize_kubernetes_client()
        elif self.service_type == CloudServiceType.SERVERLESS:
            await self._initialize_serverless_client()
        elif self.service_type == CloudServiceType.STORAGE:
            await self._initialize_storage_client()

    async def _initialize_aws_client(self):
        """初始化AWS客户端"""
        try:
            import boto3
            credentials = await self.credential_manager.get_aws_credentials()

            self._clients = {
                "ec2": boto3.client(
                    "ec2",
                    aws_access_key_id=credentials.get("access_key_id"),
                    aws_secret_access_key=credentials.get("secret_access_key"),
                    aws_session_token=credentials.get("session_token"),
                    region_name=credentials.get("region")
                ),
                "s3": boto3.client(
                    "s3",
                    aws_access_key_id=credentials.get("access_key_id"),
                    aws_secret_access_key=credentials.get("secret_access_key"),
                    aws_session_token=credentials.get("session_token"),
                    region_name=credentials.get("region")
                ),
                "rds": boto3.client(
                    "rds",
                    aws_access_key_id=credentials.get("access_key_id"),
                    aws_secret_access_key=credentials.get("secret_access_key"),
                    aws_session_token=credentials.get("session_token"),
                    region_name=credentials.get("region")
                ),
                "lambda": boto3.client(
                    "lambda",
                    aws_access_key_id=credentials.get("access_key_id"),
                    aws_secret_access_key=credentials.get("secret_access_key"),
                    aws_session_token=credentials.get("session_token"),
                    region_name=credentials.get("region")
                ),
                "cloudformation": boto3.client(
                    "cloudformation",
                    aws_access_key_id=credentials.get("access_key_id"),
                    aws_secret_access_key=credentials.get("secret_access_key"),
                    aws_session_token=credentials.get("session_token"),
                    region_name=credentials.get("region")
                )
            }
            self.logger.info("AWS客户端初始化成功")
        except Exception as e:
            self.logger.error(f"AWS客户端初始化失败: {e}")
            raise

    async def _initialize_docker_client(self):
        """初始化Docker客户端"""
        try:
            import docker
            config = await self.credential_manager.get_docker_config()

            if config.get("tls"):
                tls_config = docker.tls.TLSConfig(
                    ca_cert=config.get("tls_ca_cert"),
                    client_cert=(config.get("tls_client_cert"), config.get("tls_client_key"))
                )
                self._clients["docker"] = docker.DockerClient(
                    base_url=config["base_url"],
                    tls=tls_config
                )
            else:
                self._clients["docker"] = docker.DockerClient(
                    base_url=config["base_url"]
                )

            self.logger.info("Docker客户端初始化成功")
        except Exception as e:
            self.logger.error(f"Docker客户端初始化失败: {e}")
            raise

    async def _initialize_kubernetes_client(self):
        """初始化Kubernetes客户端"""
        try:
            from kubernetes import client, config
            kube_config = await self.credential_manager.get_kubernetes_config()

            if "kubeconfig_path" in kube_config:
                config.load_kube_config(config_file=kube_config["kubeconfig_path"])
            else:
                configuration = client.Configuration()
                configuration.host = kube_config["host"]
                configuration.verify_ssl = kube_config.get("verify_ssl", True)
                configuration.ssl_ca_cert = kube_config.get("ca_cert")
                configuration.api_key = {"authorization": f"Bearer {kube_config['token']}"}
                client.Configuration.set_default(configuration)

            self._clients = {
                "core_v1": client.CoreV1Api(),
                "apps_v1": client.AppsV1Api(),
                "batch_v1": client.BatchV1Api(),
                "networking_v1": client.NetworkingV1Api()
            }
            self.logger.info("Kubernetes客户端初始化成功")
        except Exception as e:
            self.logger.error(f"Kubernetes客户端初始化失败: {e}")
            raise

    async def _initialize_serverless_client(self):
        """初始化Serverless客户端"""
        # Serverless框架通常通过命令行工具
        # 这里初始化配置和环境检查
        self.logger.info("Serverless客户端初始化")

    async def _initialize_storage_client(self):
        """初始化云存储客户端"""
        # 支持S3和MinIO兼容接口
        try:
            import boto3
            from botocore.client import Config

            # 检查MinIO配置
            minio_endpoint = os.environ.get("MINIO_ENDPOINT")
            minio_access_key = os.environ.get("MINIO_ACCESS_KEY")
            minio_secret_key = os.environ.get("MINIO_SECRET_KEY")

            if minio_endpoint and minio_access_key and minio_secret_key:
                self._clients["storage"] = boto3.client(
                    "s3",
                    endpoint_url=minio_endpoint,
                    aws_access_key_id=minio_access_key,
                    aws_secret_access_key=minio_secret_key,
                    config=Config(signature_version="s3v4")
                )
                self.logger.info("MinIO客户端初始化成功")
            else:
                # 使用AWS S3
                credentials = await self.credential_manager.get_aws_credentials()
                self._clients["storage"] = boto3.client(
                    "s3",
                    aws_access_key_id=credentials.get("access_key_id"),
                    aws_secret_access_key=credentials.get("secret_access_key"),
                    aws_session_token=credentials.get("session_token"),
                    region_name=credentials.get("region")
                )
                self.logger.info("AWS S3客户端初始化成功")
        except Exception as e:
            self.logger.error(f"云存储客户端初始化失败: {e}")
            raise

    async def list_tools(self) -> List[Tool]:
        """列出可用工具"""
        base_tools = [
            Tool(
                name="list_resources",
                description="列出云服务资源",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_type": {"type": "string", "description": "资源类型"},
                        "filters": {"type": "object", "description": "过滤条件"}
                    },
                    "required": ["resource_type"]
                }
            ),
            Tool(
                name="create_resource",
                description="创建云服务资源",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_type": {"type": "string", "description": "资源类型"},
                        "name": {"type": "string", "description": "资源名称"},
                        "spec": {"type": "object", "description": "资源配置"},
                        "tags": {"type": "object", "description": "资源标签"}
                    },
                    "required": ["resource_type", "name", "spec"]
                }
            ),
            Tool(
                name="delete_resource",
                description="删除云服务资源",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_type": {"type": "string", "description": "资源类型"},
                        "resource_id": {"type": "string", "description": "资源ID"},
                        "force": {"type": "boolean", "description": "强制删除"}
                    },
                    "required": ["resource_type", "resource_id"]
                }
            ),
            Tool(
                name="describe_resource",
                description="描述云服务资源详情",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_type": {"type": "string", "description": "资源类型"},
                        "resource_id": {"type": "string", "description": "资源ID"}
                    },
                    "required": ["resource_type", "resource_id"]
                }
            )
        ]

        # 添加服务特定工具
        if self.service_type == CloudServiceType.AWS:
            base_tools.extend(self._get_aws_tools())
        elif self.service_type == CloudServiceType.DOCKER:
            base_tools.extend(self._get_docker_tools())
        elif self.service_type == CloudServiceType.KUBERNETES:
            base_tools.extend(self._get_kubernetes_tools())
        elif self.service_type == CloudServiceType.SERVERLESS:
            base_tools.extend(self._get_serverless_tools())
        elif self.service_type == CloudServiceType.STORAGE:
            base_tools.extend(self._get_storage_tools())

        return base_tools

    def _get_aws_tools(self) -> List[Tool]:
        """获取AWS特定工具"""
        return [
            Tool(
                name="aws_deploy_stack",
                description="部署CloudFormation堆栈",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stack_name": {"type": "string", "description": "堆栈名称"},
                        "template_body": {"type": "string", "description": "模板内容"},
                        "parameters": {"type": "object", "description": "参数"},
                        "capabilities": {"type": "array", "items": {"type": "string"}, "description": "能力"}
                    },
                    "required": ["stack_name", "template_body"]
                }
            ),
            Tool(
                name="aws_invoke_lambda",
                description="调用Lambda函数",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "function_name": {"type": "string", "description": "函数名称"},
                        "payload": {"type": "object", "description": "调用负载"},
                        "invocation_type": {"type": "string", "description": "调用类型", "enum": ["RequestResponse", "Event", "DryRun"]}
                    },
                    "required": ["function_name"]
                }
            ),
            Tool(
                name="aws_upload_to_s3",
                description="上传文件到S3",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "S3桶名称"},
                        "key": {"type": "string", "description": "对象键"},
                        "file_path": {"type": "string", "description": "本地文件路径"},
                        "content_type": {"type": "string", "description": "内容类型"}
                    },
                    "required": ["bucket", "key", "file_path"]
                }
            )
        ]

    def _get_docker_tools(self) -> List[Tool]:
        """获取Docker特定工具"""
        return [
            Tool(
                name="docker_build_image",
                description="构建Docker镜像",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dockerfile": {"type": "string", "description": "Dockerfile内容"},
                        "image_name": {"type": "string", "description": "镜像名称"},
                        "build_args": {"type": "object", "description": "构建参数"},
                        "context": {"type": "string", "description": "构建上下文"}
                    },
                    "required": ["dockerfile", "image_name"]
                }
            ),
            Tool(
                name="docker_run_container",
                description="运行Docker容器",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "description": "镜像名称"},
                        "name": {"type": "string", "description": "容器名称"},
                        "ports": {"type": "object", "description": "端口映射"},
                        "environment": {"type": "object", "description": "环境变量"},
                        "volumes": {"type": "object", "description": "卷映射"}
                    },
                    "required": ["image"]
                }
            ),
            Tool(
                name="docker_compose_up",
                description="启动Docker Compose服务",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "compose_file": {"type": "string", "description": "Compose文件内容"},
                        "services": {"type": "array", "items": {"type": "string"}, "description": "指定服务"}
                    },
                    "required": ["compose_file"]
                }
            )
        ]

    def _get_kubernetes_tools(self) -> List[Tool]:
        """获取Kubernetes特定工具"""
        return [
            Tool(
                name="k8s_apply_yaml",
                description="应用Kubernetes YAML配置",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "yaml_content": {"type": "string", "description": "YAML内容"},
                        "namespace": {"type": "string", "description": "命名空间"}
                    },
                    "required": ["yaml_content"]
                }
            ),
            Tool(
                name="k8s_scale_deployment",
                description="伸缩Kubernetes部署",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "deployment": {"type": "string", "description": "部署名称"},
                        "replicas": {"type": "integer", "description": "副本数"},
                        "namespace": {"type": "string", "description": "命名空间"}
                    },
                    "required": ["deployment", "replicas"]
                }
            ),
            Tool(
                name="k8s_get_logs",
                description="获取Kubernetes Pod日志",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pod": {"type": "string", "description": "Pod名称"},
                        "container": {"type": "string", "description": "容器名称"},
                        "namespace": {"type": "string", "description": "命名空间"},
                        "tail_lines": {"type": "integer", "description": "日志行数"}
                    },
                    "required": ["pod"]
                }
            )
        ]

    def _get_serverless_tools(self) -> List[Tool]:
        """获取Serverless特定工具"""
        return [
            Tool(
                name="serverless_deploy",
                description="部署Serverless应用",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "服务名称"},
                        "provider": {"type": "string", "description": "云提供商", "enum": ["aws", "azure", "google"]},
                        "functions": {"type": "object", "description": "函数配置"},
                        "resources": {"type": "object", "description": "资源配置"}
                    },
                    "required": ["service_name", "provider"]
                }
            ),
            Tool(
                name="serverless_invoke",
                description="调用Serverless函数",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "function": {"type": "string", "description": "函数名称"},
                        "data": {"type": "object", "description": "调用数据"},
                        "path": {"type": "string", "description": "API路径"},
                        "method": {"type": "string", "description": "HTTP方法"}
                    },
                    "required": ["function"]
                }
            )
        ]

    def _get_storage_tools(self) -> List[Tool]:
        """获取云存储特定工具"""
        return [
            Tool(
                name="storage_list_buckets",
                description="列出存储桶",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prefix": {"type": "string", "description": "桶名前缀"}
                    }
                }
            ),
            Tool(
                name="storage_list_objects",
                description="列出存储对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "桶名称"},
                        "prefix": {"type": "string", "description": "对象前缀"},
                        "delimiter": {"type": "string", "description": "分隔符"}
                    },
                    "required": ["bucket"]
                }
            ),
            Tool(
                name="storage_presigned_url",
                description="生成预签名URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "桶名称"},
                        "key": {"type": "string", "description": "对象键"},
                        "expires_in": {"type": "integer", "description": "过期时间（秒）"},
                        "method": {"type": "string", "description": "HTTP方法", "enum": ["GET", "PUT", "DELETE"]}
                    },
                    "required": ["bucket", "key"]
                }
            )
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用"""
        self.logger.info(f"处理工具调用: {tool_name}, 参数: {arguments}")

        # 通用工具处理
        if tool_name == "list_resources":
            return await self._list_resources(arguments)
        elif tool_name == "create_resource":
            return await self._create_resource(arguments)
        elif tool_name == "delete_resource":
            return await self._delete_resource(arguments)
        elif tool_name == "describe_resource":
            return await self._describe_resource(arguments)

        # 服务特定工具处理
        elif tool_name.startswith("aws_"):
            return await self._handle_aws_tool(tool_name, arguments)
        elif tool_name.startswith("docker_"):
            return await self._handle_docker_tool(tool_name, arguments)
        elif tool_name.startswith("k8s_"):
            return await self._handle_kubernetes_tool(tool_name, arguments)
        elif tool_name.startswith("serverless_"):
            return await self._handle_serverless_tool(tool_name, arguments)
        elif tool_name.startswith("storage_"):
            return await self._handle_storage_tool(tool_name, arguments)
        else:
            raise ValueError(f"未知工具: {tool_name}")

    async def _list_resources(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出资源的通用实现"""
        raise NotImplementedError("子类必须实现此方法")

    async def _create_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建资源的通用实现"""
        raise NotImplementedError("子类必须实现此方法")

    async def _delete_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除资源的通用实现"""
        raise NotImplementedError("子类必须实现此方法")

    async def _describe_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """描述资源的通用实现"""
        raise NotImplementedError("子类必须实现此方法")

    async def _handle_aws_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理AWS特定工具"""
        raise NotImplementedError("AWS子类必须实现此方法")

    async def _handle_docker_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理Docker特定工具"""
        raise NotImplementedError("Docker子类必须实现此方法")

    async def _handle_kubernetes_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理Kubernetes特定工具"""
        raise NotImplementedError("Kubernetes子类必须实现此方法")

    async def _handle_serverless_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理Serverless特定工具"""
        raise NotImplementedError("Serverless子类必须实现此方法")

    async def _handle_storage_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理云存储特定工具"""
        raise NotImplementedError("Storage子类必须实现此方法")


def run_cloud_mcp_server(server_class):
    """运行云服务MCP服务器的辅助函数"""
    if not MCP_AVAILABLE:
        print("错误: mcp包未安装")
        print("请安装: pip install mcp")
        return

    import asyncio

    async def main():
        server = server_class()
        await server.initialize()

        # 这里应该启动MCP服务器
        # 简化版本，实际需要完整的MCP服务器实现
        print(f"{server.service_type.value} MCP服务器已就绪")

        # 保持运行
        while True:
            await asyncio.sleep(1)

    asyncio.run(main())


if __name__ == "__main__":
    print("这是云服务MCP框架库，不能直接运行")
    print("请使用具体的云服务MCP服务器实现")