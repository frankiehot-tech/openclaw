#!/usr/bin/env python3
"""
Docker容器服务MCP服务器

为AI Assistant提供Docker容器操作能力：
- 容器生命周期管理
- 镜像构建和推送
- Docker Compose服务编排
- 网络和卷管理
"""

import asyncio
import json
import logging
import os
import tempfile
import tarfile
import io
from typing import Any, Dict, List, Optional
from pathlib import Path

# 导入云服务MCP框架
from . import CloudServiceMCPBase, CloudServiceType, run_cloud_mcp_server


class DockerMCP(CloudServiceMCPBase):
    """Docker容器服务MCP实现"""

    def __init__(self):
        super().__init__(CloudServiceType.DOCKER)
        self.logger = logging.getLogger("cloud-mcp.docker")

    async def _list_resources(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出Docker资源"""
        resource_type = args.get("resource_type")
        filters = args.get("filters", {})

        try:
            if resource_type == "containers":
                return await self._list_containers(filters)
            elif resource_type == "images":
                return await self._list_images(filters)
            elif resource_type == "networks":
                return await self._list_networks(filters)
            elif resource_type == "volumes":
                return await self._list_volumes(filters)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "containers",
                        "images",
                        "networks",
                        "volumes"
                    ]
                }
        except Exception as e:
            self.logger.error(f"列出资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建Docker资源"""
        resource_type = args.get("resource_type")
        name = args.get("name")
        spec = args.get("spec", {})
        tags = args.get("tags", {})

        try:
            if resource_type == "container":
                return await self._create_container(name, spec, tags)
            elif resource_type == "network":
                return await self._create_network(name, spec, tags)
            elif resource_type == "volume":
                return await self._create_volume(name, spec, tags)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "container",
                        "network",
                        "volume"
                    ]
                }
        except Exception as e:
            self.logger.error(f"创建资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _delete_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除Docker资源"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")
        force = args.get("force", False)

        try:
            if resource_type == "container":
                return await self._delete_container(resource_id, force)
            elif resource_type == "image":
                return await self._delete_image(resource_id, force)
            elif resource_type == "network":
                return await self._delete_network(resource_id, force)
            elif resource_type == "volume":
                return await self._delete_volume(resource_id, force)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "container",
                        "image",
                        "network",
                        "volume"
                    ]
                }
        except Exception as e:
            self.logger.error(f"删除资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _describe_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """描述Docker资源详情"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")

        try:
            if resource_type == "container":
                return await self._describe_container(resource_id)
            elif resource_type == "image":
                return await self._describe_image(resource_id)
            elif resource_type == "network":
                return await self._describe_network(resource_id)
            elif resource_type == "volume":
                return await self._describe_volume(resource_id)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "container",
                        "image",
                        "network",
                        "volume"
                    ]
                }
        except Exception as e:
            self.logger.error(f"描述资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Docker特定工具实现
    async def _handle_docker_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理Docker特定工具"""
        if tool_name == "docker_build_image":
            return await self._docker_build_image(args)
        elif tool_name == "docker_run_container":
            return await self._docker_run_container(args)
        elif tool_name == "docker_compose_up":
            return await self._docker_compose_up(args)
        else:
            return {
                "success": False,
                "error": f"未知的Docker工具: {tool_name}"
            }

    # 容器操作方法
    async def _list_containers(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出容器"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            all_containers = docker_client.containers.list(
                all=filters.get("all", True),
                filters=filters
            )

            containers = []
            for container in all_containers:
                containers.append({
                    "id": container.id[:12],
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                    "status": container.status,
                    "state": container.status,
                    "created": container.attrs.get("Created"),
                    "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                    "labels": container.labels
                })

            return {
                "success": True,
                "containers": containers,
                "count": len(containers)
            }
        except Exception as e:
            self.logger.error(f"列出容器失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_container(self, name: str, spec: Dict[str, Any], tags: Dict[str, str]) -> Dict[str, Any]:
        """创建容器"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            # 构建容器配置
            container_config = {
                "image": spec.get("image", "alpine:latest"),
                "name": name,
                "detach": spec.get("detach", True),
                "stdin_open": spec.get("stdin_open", False),
                "tty": spec.get("tty", False),
                "labels": tags
            }

            # 环境变量
            environment = spec.get("environment")
            if environment:
                container_config["environment"] = [f"{k}={v}" for k, v in environment.items()]

            # 端口映射
            ports = spec.get("ports")
            if ports:
                container_config["ports"] = ports

            # 卷映射
            volumes = spec.get("volumes")
            if volumes:
                container_config["volumes"] = volumes

            # 命令和入口点
            command = spec.get("command")
            if command:
                container_config["command"] = command

            entrypoint = spec.get("entrypoint")
            if entrypoint:
                container_config["entrypoint"] = entrypoint

            # 创建容器
            container = docker_client.containers.create(**container_config)

            # 启动容器（如果指定）
            if spec.get("start", True):
                container.start()

            self.logger.info(f"容器创建成功: {container.id[:12]}")
            return {
                "success": True,
                "container_id": container.id[:12],
                "name": container.name,
                "message": f"容器 {container.name} 创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建容器失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_container(self, container_id: str, force: bool) -> Dict[str, Any]:
        """删除容器"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            container = docker_client.containers.get(container_id)

            # 停止容器（如果正在运行）
            if container.status == "running" and force:
                container.stop()

            container.remove(force=force)

            self.logger.info(f"容器删除成功: {container_id}")
            return {
                "success": True,
                "message": f"容器 {container_id} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除容器失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_container(self, container_id: str) -> Dict[str, Any]:
        """描述容器详情"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            container = docker_client.containers.get(container_id)
            attrs = container.attrs

            # 获取容器日志（最近100行）
            try:
                logs = container.logs(tail=100, timestamps=True).decode("utf-8")
            except:
                logs = ""

            result = {
                "success": True,
                "container": {
                    "id": container.id[:12],
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                    "status": container.status,
                    "state": attrs.get("State", {}).get("Status"),
                    "created": attrs.get("Created"),
                    "started_at": attrs.get("State", {}).get("StartedAt"),
                    "finished_at": attrs.get("State", {}).get("FinishedAt"),
                    "exit_code": attrs.get("State", {}).get("ExitCode"),
                    "config": {
                        "cmd": attrs.get("Config", {}).get("Cmd"),
                        "entrypoint": attrs.get("Config", {}).get("Entrypoint"),
                        "env": attrs.get("Config", {}).get("Env", []),
                        "labels": attrs.get("Config", {}).get("Labels", {})
                    },
                    "network_settings": {
                        "ip_address": attrs.get("NetworkSettings", {}).get("IPAddress"),
                        "ports": attrs.get("NetworkSettings", {}).get("Ports", {}),
                        "networks": list(attrs.get("NetworkSettings", {}).get("Networks", {}).keys())
                    },
                    "mounts": [
                        {
                            "source": mount.get("Source"),
                            "destination": mount.get("Destination"),
                            "mode": mount.get("Mode"),
                            "type": mount.get("Type")
                        }
                        for mount in attrs.get("Mounts", [])
                    ],
                    "logs": logs.split("\n")[-50:] if logs else []  # 最近50行日志
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述容器失败: {e}")
            return {"success": False, "error": str(e)}

    # 镜像操作方法
    async def _list_images(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出镜像"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            all_images = docker_client.images.list(
                filters=filters,
                all=True
            )

            images = []
            for image in all_images:
                # 获取镜像标签
                tags = image.tags if image.tags else [f"<none>:{image.id[:12]}"]
                for tag in tags:
                    images.append({
                        "id": image.id[7:19] if image.id.startswith("sha256:") else image.id[:12],
                        "tags": tags,
                        "size": image.attrs.get("Size", 0),
                        "created": image.attrs.get("Created"),
                        "labels": image.labels
                    })
                # 如果镜像没有标签，也显示
                if not image.tags:
                    images.append({
                        "id": image.id[7:19] if image.id.startswith("sha256:") else image.id[:12],
                        "tags": ["<none>"],
                        "size": image.attrs.get("Size", 0),
                        "created": image.attrs.get("Created"),
                        "labels": image.labels
                    })

            return {
                "success": True,
                "images": images,
                "count": len(images)
            }
        except Exception as e:
            self.logger.error(f"列出镜像失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_image(self, image_id: str, force: bool) -> Dict[str, Any]:
        """删除镜像"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            docker_client.images.remove(image_id, force=force)

            self.logger.info(f"镜像删除成功: {image_id}")
            return {
                "success": True,
                "message": f"镜像 {image_id} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除镜像失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_image(self, image_id: str) -> Dict[str, Any]:
        """描述镜像详情"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            image = docker_client.images.get(image_id)
            attrs = image.attrs

            # 解析镜像历史
            history = []
            try:
                for hist in image.history():
                    history.append({
                        "id": hist.get("Id", "")[:12],
                        "created": hist.get("Created"),
                        "created_by": hist.get("CreatedBy", ""),
                        "size": hist.get("Size", 0),
                        "comment": hist.get("Comment", "")
                    })
            except:
                history = []

            result = {
                "success": True,
                "image": {
                    "id": image.id[7:19] if image.id.startswith("sha256:") else image.id[:12],
                    "tags": image.tags,
                    "architecture": attrs.get("Architecture"),
                    "os": attrs.get("Os"),
                    "created": attrs.get("Created"),
                    "size": attrs.get("Size", 0),
                    "virtual_size": attrs.get("VirtualSize", 0),
                    "config": {
                        "cmd": attrs.get("Config", {}).get("Cmd"),
                        "entrypoint": attrs.get("Config", {}).get("Entrypoint"),
                        "env": attrs.get("Config", {}).get("Env", []),
                        "labels": attrs.get("Config", {}).get("Labels", {}),
                        "working_dir": attrs.get("Config", {}).get("WorkingDir"),
                        "user": attrs.get("Config", {}).get("User")
                    },
                    "rootfs": {
                        "type": attrs.get("RootFS", {}).get("Type"),
                        "layers": attrs.get("RootFS", {}).get("Layers", [])
                    },
                    "history": history,
                    "labels": image.labels
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述镜像失败: {e}")
            return {"success": False, "error": str(e)}

    # 网络操作方法
    async def _list_networks(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出网络"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            all_networks = docker_client.networks.list(
                filters=filters
            )

            networks = []
            for network in all_networks:
                networks.append({
                    "id": network.id[:12],
                    "name": network.name,
                    "driver": network.attrs.get("Driver"),
                    "scope": network.attrs.get("Scope"),
                    "internal": network.attrs.get("Internal", False),
                    "attachable": network.attrs.get("Attachable", False),
                    "containers": len(network.attrs.get("Containers", {}))
                })

            return {
                "success": True,
                "networks": networks,
                "count": len(networks)
            }
        except Exception as e:
            self.logger.error(f"列出网络失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_network(self, name: str, spec: Dict[str, Any], tags: Dict[str, str]) -> Dict[str, Any]:
        """创建网络"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            network = docker_client.networks.create(
                name=name,
                driver=spec.get("driver", "bridge"),
                options=spec.get("options", {}),
                ipam=spec.get("ipam", {
                    "driver": "default",
                    "config": [{"subnet": spec.get("subnet", "172.20.0.0/16")}]
                }),
                labels=tags,
                check_duplicate=True
            )

            self.logger.info(f"网络创建成功: {network.id[:12]}")
            return {
                "success": True,
                "network_id": network.id[:12],
                "name": network.name,
                "message": f"网络 {network.name} 创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建网络失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_network(self, network_id: str, force: bool) -> Dict[str, Any]:
        """删除网络"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            network = docker_client.networks.get(network_id)
            network.remove()

            self.logger.info(f"网络删除成功: {network_id}")
            return {
                "success": True,
                "message": f"网络 {network_id} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除网络失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_network(self, network_id: str) -> Dict[str, Any]:
        """描述网络详情"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            network = docker_client.networks.get(network_id)
            attrs = network.attrs

            # 解析连接的容器
            containers = []
            for container_id, container_info in attrs.get("Containers", {}).items():
                containers.append({
                    "container_id": container_id[:12],
                    "name": container_info.get("Name"),
                    "ipv4_address": container_info.get("IPv4Address"),
                    "ipv6_address": container_info.get("IPv6Address"),
                    "mac_address": container_info.get("MacAddress")
                })

            result = {
                "success": True,
                "network": {
                    "id": network.id[:12],
                    "name": network.name,
                    "driver": attrs.get("Driver"),
                    "scope": attrs.get("Scope"),
                    "internal": attrs.get("Internal", False),
                    "attachable": attrs.get("Attachable", False),
                    "ingress": attrs.get("Ingress", False),
                    "ipam": {
                        "driver": attrs.get("IPAM", {}).get("Driver"),
                        "config": attrs.get("IPAM", {}).get("Config", []),
                        "options": attrs.get("IPAM", {}).get("Options", {})
                    },
                    "options": attrs.get("Options", {}),
                    "labels": attrs.get("Labels", {}),
                    "containers": containers,
                    "created": attrs.get("Created")
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述网络失败: {e}")
            return {"success": False, "error": str(e)}

    # 卷操作方法
    async def _list_volumes(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出卷"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            all_volumes = docker_client.volumes.list(
                filters=filters
            )

            volumes = []
            for volume in all_volumes:
                volumes.append({
                    "name": volume.name,
                    "driver": volume.attrs.get("Driver"),
                    "mountpoint": volume.attrs.get("Mountpoint"),
                    "labels": volume.attrs.get("Labels", {}),
                    "scope": volume.attrs.get("Scope"),
                    "created_at": volume.attrs.get("CreatedAt")
                })

            return {
                "success": True,
                "volumes": volumes,
                "count": len(volumes)
            }
        except Exception as e:
            self.logger.error(f"列出卷失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_volume(self, name: str, spec: Dict[str, Any], tags: Dict[str, str]) -> Dict[str, Any]:
        """创建卷"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            volume = docker_client.volumes.create(
                name=name,
                driver=spec.get("driver", "local"),
                driver_opts=spec.get("driver_opts", {}),
                labels=tags
            )

            self.logger.info(f"卷创建成功: {volume.name}")
            return {
                "success": True,
                "volume_name": volume.name,
                "message": f"卷 {volume.name} 创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建卷失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_volume(self, volume_name: str, force: bool) -> Dict[str, Any]:
        """删除卷"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            docker_client.volumes.get(volume_name).remove(force=force)

            self.logger.info(f"卷删除成功: {volume_name}")
            return {
                "success": True,
                "message": f"卷 {volume_name} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除卷失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_volume(self, volume_name: str) -> Dict[str, Any]:
        """描述卷详情"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            volume = docker_client.volumes.get(volume_name)
            attrs = volume.attrs

            # 获取卷使用情况
            usage_info = {}
            try:
                # 尝试获取卷大小信息
                import shutil
                mountpoint = attrs.get("Mountpoint")
                if mountpoint and os.path.exists(mountpoint):
                    usage = shutil.disk_usage(mountpoint)
                    usage_info = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free
                    }
            except:
                pass

            result = {
                "success": True,
                "volume": {
                    "name": volume.name,
                    "driver": attrs.get("Driver"),
                    "mountpoint": attrs.get("Mountpoint"),
                    "labels": attrs.get("Labels", {}),
                    "scope": attrs.get("Scope"),
                    "options": attrs.get("Options", {}),
                    "created_at": attrs.get("CreatedAt"),
                    "usage": usage_info
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述卷失败: {e}")
            return {"success": False, "error": str(e)}

    # 特定工具实现
    async def _docker_build_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """构建Docker镜像"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            dockerfile = args["dockerfile"]
            image_name = args["image_name"]
            build_args = args.get("build_args", {})
            context = args.get("context", ".")

            # 创建临时目录用于构建
            with tempfile.TemporaryDirectory() as temp_dir:
                # 写入Dockerfile
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile)

                # 如果提供了构建上下文，复制文件
                if context and os.path.exists(context):
                    import shutil
                    for item in os.listdir(context):
                        src = os.path.join(context, item)
                        dst = os.path.join(temp_dir, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)

                # 构建镜像
                self.logger.info(f"开始构建镜像: {image_name}")
                image, build_logs = docker_client.images.build(
                    path=temp_dir,
                    tag=image_name,
                    buildargs=build_args,
                    rm=True,
                    pull=True
                )

                # 收集构建日志
                logs = []
                for chunk in build_logs:
                    if "stream" in chunk:
                        logs.append(chunk["stream"].strip())
                    elif "error" in chunk:
                        logs.append(f"错误: {chunk['error']}")

                self.logger.info(f"镜像构建成功: {image.id[:12]}")
                return {
                    "success": True,
                    "image_id": image.id[7:19] if image.id.startswith("sha256:") else image.id[:12],
                    "tags": image.tags,
                    "logs": logs,
                    "message": f"镜像 {image_name} 构建成功"
                }
        except Exception as e:
            self.logger.error(f"构建镜像失败: {e}")
            return {"success": False, "error": str(e)}

    async def _docker_run_container(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """运行Docker容器"""
        docker_client = self._clients.get("docker")
        if not docker_client:
            return {"success": False, "error": "Docker客户端未初始化"}

        try:
            image = args["image"]
            name = args.get("name")
            ports = args.get("ports", {})
            environment = args.get("environment", {})
            volumes = args.get("volumes", {})

            # 运行容器
            container = docker_client.containers.run(
                image=image,
                name=name,
                ports=ports,
                environment=environment,
                volumes=volumes,
                detach=True
            )

            # 获取容器信息
            container.reload()

            self.logger.info(f"容器运行成功: {container.id[:12]}")
            return {
                "success": True,
                "container_id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "ports": container.ports,
                "message": f"容器 {container.name} 运行成功"
            }
        except Exception as e:
            self.logger.error(f"运行容器失败: {e}")
            return {"success": False, "error": str(e)}

    async def _docker_compose_up(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """启动Docker Compose服务"""
        try:
            compose_file = args["compose_file"]
            services = args.get("services", [])

            # 创建临时目录用于Compose文件
            with tempfile.TemporaryDirectory() as temp_dir:
                # 写入docker-compose.yml
                compose_path = os.path.join(temp_dir, "docker-compose.yml")
                with open(compose_path, "w") as f:
                    f.write(compose_file)

                # 构建docker-compose命令
                cmd = ["docker-compose", "-f", compose_path, "up", "-d"]

                if services:
                    cmd.extend(services)

                # 执行命令
                import subprocess
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=temp_dir
                )

                if result.returncode == 0:
                    self.logger.info("Docker Compose服务启动成功")
                    return {
                        "success": True,
                        "output": result.stdout,
                        "message": "Docker Compose服务启动成功"
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr,
                        "output": result.stdout
                    }
        except Exception as e:
            self.logger.error(f"Docker Compose启动失败: {e}")
            return {"success": False, "error": str(e)}


def main():
    """主函数：启动Docker MCP服务器"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("🚀 启动Docker容器服务MCP服务器...")
    run_cloud_mcp_server(DockerMCP)


if __name__ == "__main__":
    main()