#!/usr/bin/env python3
"""
云存储MCP服务器

为AI Assistant提供云存储操作能力：
- S3存储桶管理
- MinIO兼容存储操作
- 对象上传下载
- 预签名URL生成
"""

import asyncio
import json
import logging
import os
import tempfile
import mimetypes
import hashlib
from typing import Any, Dict, List, Optional, BinaryIO
from pathlib import Path
from datetime import datetime, timedelta

# 导入云服务MCP框架
from . import CloudServiceMCPBase, CloudServiceType, run_cloud_mcp_server


class StorageMCP(CloudServiceMCPBase):
    """云存储MCP实现"""

    def __init__(self):
        super().__init__(CloudServiceType.STORAGE)
        self.logger = logging.getLogger("cloud-mcp.storage")

    async def _list_resources(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出云存储资源"""
        resource_type = args.get("resource_type")

        try:
            if resource_type == "buckets":
                return await self._list_buckets()
            elif resource_type == "objects":
                bucket = args.get("bucket")
                if not bucket:
                    return {"success": False, "error": "需要指定桶名称"}
                return await self._list_objects(bucket, args.get("prefix"), args.get("delimiter"))
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": ["buckets", "objects"]
                }
        except Exception as e:
            self.logger.error(f"列出资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建云存储资源"""
        resource_type = args.get("resource_type")
        name = args.get("name")
        spec = args.get("spec", {})

        try:
            if resource_type == "bucket":
                return await self._create_bucket(name, spec)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": ["bucket"]
                }
        except Exception as e:
            self.logger.error(f"创建资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _delete_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除云存储资源"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")
        force = args.get("force", False)

        try:
            if resource_type == "bucket":
                return await self._delete_bucket(resource_id, force)
            elif resource_type == "object":
                bucket = args.get("bucket")
                if not bucket:
                    return {"success": False, "error": "需要指定桶名称"}
                return await self._delete_object(bucket, resource_id)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": ["bucket", "object"]
                }
        except Exception as e:
            self.logger.error(f"删除资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _describe_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """描述云存储资源详情"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")

        try:
            if resource_type == "bucket":
                return await self._describe_bucket(resource_id)
            elif resource_type == "object":
                bucket = args.get("bucket")
                if not bucket:
                    return {"success": False, "error": "需要指定桶名称"}
                return await self._describe_object(bucket, resource_id)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": ["bucket", "object"]
                }
        except Exception as e:
            self.logger.error(f"描述资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_storage_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理云存储特定工具"""
        try:
            if tool_name == "storage_list_buckets":
                return await self._list_buckets(args.get("prefix"))
            elif tool_name == "storage_list_objects":
                bucket = args.get("bucket")
                if not bucket:
                    return {"success": False, "error": "需要指定桶名称"}
                return await self._list_objects(
                    bucket,
                    args.get("prefix"),
                    args.get("delimiter")
                )
            elif tool_name == "storage_presigned_url":
                bucket = args.get("bucket")
                key = args.get("key")
                if not bucket or not key:
                    return {"success": False, "error": "需要指定桶名称和对象键"}
                return await self._generate_presigned_url(
                    bucket,
                    key,
                    args.get("expires_in", 3600),
                    args.get("method", "GET")
                )
            else:
                return {
                    "success": False,
                    "error": f"未知的云存储工具: {tool_name}"
                }
        except Exception as e:
            self.logger.error(f"处理云存储工具失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # 云存储操作方法
    async def _list_buckets(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """列出存储桶"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            response = storage_client.list_buckets()

            buckets = []
            for bucket in response.get('Buckets', []):
                bucket_name = bucket['Name']

                # 过滤前缀
                if prefix and not bucket_name.startswith(prefix):
                    continue

                # 获取桶的额外信息
                try:
                    location = storage_client.get_bucket_location(Bucket=bucket_name)
                    region = location.get('LocationConstraint', 'us-east-1')

                    buckets.append({
                        "name": bucket_name,
                        "creation_date": bucket['CreationDate'].isoformat() if hasattr(bucket['CreationDate'], 'isoformat') else str(bucket['CreationDate']),
                        "region": region
                    })
                except Exception as e:
                    self.logger.warning(f"获取桶 {bucket_name} 信息失败: {e}")
                    buckets.append({
                        "name": bucket_name,
                        "creation_date": bucket['CreationDate'].isoformat() if hasattr(bucket['CreationDate'], 'isoformat') else str(bucket['CreationDate']),
                        "region": "unknown"
                    })

            return {
                "success": True,
                "resources": buckets,
                "count": len(buckets)
            }
        except Exception as e:
            self.logger.error(f"列出存储桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _list_objects(self, bucket: str, prefix: Optional[str] = None, delimiter: Optional[str] = None) -> Dict[str, Any]:
        """列出存储对象"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            params = {
                "Bucket": bucket
            }

            if prefix:
                params["Prefix"] = prefix
            if delimiter:
                params["Delimiter"] = delimiter

            response = storage_client.list_objects_v2(**params)

            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat() if hasattr(obj['LastModified'], 'isoformat') else str(obj['LastModified']),
                    "etag": obj['ETag'].strip('"'),
                    "storage_class": obj.get('StorageClass', 'STANDARD')
                })

            # 处理前缀（目录）
            prefixes = []
            for prefix_obj in response.get('CommonPrefixes', []):
                prefixes.append({
                    "prefix": prefix_obj['Prefix']
                })

            return {
                "success": True,
                "bucket": bucket,
                "objects": objects,
                "prefixes": prefixes,
                "object_count": len(objects),
                "prefix_count": len(prefixes),
                "is_truncated": response.get('IsTruncated', False),
                "continuation_token": response.get('NextContinuationToken')
            }
        except Exception as e:
            self.logger.error(f"列出存储对象失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_bucket(self, name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """创建存储桶"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            region = spec.get("region", "us-east-1")
            acl = spec.get("acl", "private")

            create_params = {
                "Bucket": name,
                "ACL": acl
            }

            # 如果是除us-east-1以外的区域，需要指定区域
            if region != "us-east-1":
                create_params["CreateBucketConfiguration"] = {
                    "LocationConstraint": region
                }

            storage_client.create_bucket(**create_params)

            # 可选：配置桶策略
            if "policy" in spec:
                policy = spec["policy"]
                if isinstance(policy, dict):
                    policy = json.dumps(policy)

                storage_client.put_bucket_policy(
                    Bucket=name,
                    Policy=policy
                )

            # 可选：配置CORS
            if "cors" in spec:
                cors_config = spec["cors"]
                if isinstance(cors_config, dict):
                    cors_config = [cors_config]

                storage_client.put_bucket_cors(
                    Bucket=name,
                    CORSConfiguration={
                        "CORSRules": cors_config
                    }
                )

            return {
                "success": True,
                "message": f"存储桶 {name} 创建成功",
                "bucket": name,
                "region": region,
                "acl": acl
            }
        except Exception as e:
            self.logger.error(f"创建存储桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_bucket(self, name: str, force: bool) -> Dict[str, Any]:
        """删除存储桶"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            if force:
                # 强制删除：先删除桶内所有对象
                try:
                    # 列出并删除所有对象
                    objects = storage_client.list_objects_v2(Bucket=name)

                    if objects.get('Contents'):
                        delete_objects = [{'Key': obj['Key']} for obj in objects['Contents']]
                        storage_client.delete_objects(
                            Bucket=name,
                            Delete={'Objects': delete_objects}
                        )

                    # 如果还有更多对象，继续删除
                    while objects.get('IsTruncated'):
                        continuation_token = objects.get('NextContinuationToken')
                        objects = storage_client.list_objects_v2(
                            Bucket=name,
                            ContinuationToken=continuation_token
                        )

                        if objects.get('Contents'):
                            delete_objects = [{'Key': obj['Key']} for obj in objects['Contents']]
                            storage_client.delete_objects(
                                Bucket=name,
                                Delete={'Objects': delete_objects}
                            )
                except Exception as e:
                    self.logger.warning(f"清理桶 {name} 对象失败: {e}")

            # 删除桶
            storage_client.delete_bucket(Bucket=name)

            return {
                "success": True,
                "message": f"存储桶 {name} 删除成功",
                "bucket": name,
                "force_delete": force
            }
        except Exception as e:
            self.logger.error(f"删除存储桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_object(self, bucket: str, key: str) -> Dict[str, Any]:
        """删除存储对象"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            storage_client.delete_object(Bucket=bucket, Key=key)

            return {
                "success": True,
                "message": f"对象 {key} 从桶 {bucket} 中删除成功",
                "bucket": bucket,
                "key": key
            }
        except Exception as e:
            self.logger.error(f"删除存储对象失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_bucket(self, name: str) -> Dict[str, Any]:
        """描述存储桶详情"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            # 获取桶基本信息
            try:
                response = storage_client.head_bucket(Bucket=name)
                exists = True
            except Exception:
                exists = False
                return {
                    "success": False,
                    "error": f"存储桶 {name} 不存在或无法访问"
                }

            # 获取桶位置
            try:
                location = storage_client.get_bucket_location(Bucket=name)
                region = location.get('LocationConstraint', 'us-east-1')
            except Exception:
                region = "unknown"

            # 获取桶策略
            policy = None
            try:
                policy_response = storage_client.get_bucket_policy(Bucket=name)
                policy = json.loads(policy_response['Policy'])
            except Exception:
                pass  # 无策略是正常的

            # 获取CORS配置
            cors = None
            try:
                cors_response = storage_client.get_bucket_cors(Bucket=name)
                cors = cors_response.get('CORSRules', [])
            except Exception:
                pass  # 无CORS配置是正常的

            # 获取桶大小和对象数量（近似）
            try:
                objects = storage_client.list_objects_v2(Bucket=name, MaxKeys=1000)
                object_count = objects.get('KeyCount', 0)
                total_size = sum(obj['Size'] for obj in objects.get('Contents', []))
            except Exception:
                object_count = 0
                total_size = 0

            return {
                "success": True,
                "bucket": {
                    "name": name,
                    "exists": exists,
                    "region": region,
                    "object_count": object_count,
                    "total_size": total_size,
                    "has_policy": policy is not None,
                    "has_cors": cors is not None,
                    "policy": policy,
                    "cors": cors
                }
            }
        except Exception as e:
            self.logger.error(f"描述存储桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_object(self, bucket: str, key: str) -> Dict[str, Any]:
        """描述存储对象详情"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            # 获取对象元数据
            response = storage_client.head_object(Bucket=bucket, Key=key)

            # 获取内容类型
            content_type = response.get('ContentType', 'application/octet-stream')
            content_length = response.get('ContentLength', 0)
            last_modified = response.get('LastModified')
            etag = response.get('ETag', '').strip('"')
            storage_class = response.get('StorageClass', 'STANDARD')

            # 获取用户定义的元数据
            metadata = {}
            for key_lower, value in response.get('Metadata', {}).items():
                metadata[key_lower] = value

            # 尝试获取文件扩展名
            ext = Path(key).suffix.lower()

            return {
                "success": True,
                "object": {
                    "bucket": bucket,
                    "key": key,
                    "size": content_length,
                    "content_type": content_type,
                    "last_modified": last_modified.isoformat() if hasattr(last_modified, 'isoformat') else str(last_modified),
                    "etag": etag,
                    "storage_class": storage_class,
                    "metadata": metadata,
                    "extension": ext if ext else None,
                    "is_public": response.get('CacheControl') == 'public' or 'public-read' in str(response.get('ACL', ''))
                }
            }
        except Exception as e:
            self.logger.error(f"描述存储对象失败: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_presigned_url(self, bucket: str, key: str, expires_in: int, method: str) -> Dict[str, Any]:
        """生成预签名URL"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            # 验证方法
            valid_methods = ["GET", "PUT", "DELETE"]
            if method not in valid_methods:
                return {
                    "success": False,
                    "error": f"无效的HTTP方法: {method}，有效方法: {valid_methods}"
                }

            # 生成预签名URL
            url = storage_client.generate_presigned_url(
                ClientMethod=f'{method.lower()}_object',
                Params={
                    'Bucket': bucket,
                    'Key': key
                },
                ExpiresIn=expires_in
            )

            # 计算过期时间
            expires_at = datetime.now() + timedelta(seconds=expires_in)

            return {
                "success": True,
                "url": url,
                "bucket": bucket,
                "key": key,
                "method": method,
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat(),
                "note": "预签名URL允许在指定时间内访问对象，无需AWS凭据"
            }
        except Exception as e:
            self.logger.error(f"生成预签名URL失败: {e}")
            return {"success": False, "error": str(e)}

    # 上传文件方法（可以作为扩展工具）
    async def _upload_file(self, bucket: str, key: str, file_path: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """上传文件到云存储"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {"success": False, "error": f"文件不存在: {file_path}"}

            # 确定内容类型
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = 'application/octet-stream'

            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)

            # 上传文件
            with open(file_path, 'rb') as file:
                storage_client.upload_fileobj(
                    file,
                    bucket,
                    key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'Metadata': {
                            'file-hash': file_hash,
                            'original-filename': os.path.basename(file_path)
                        }
                    }
                )

            # 获取对象信息
            object_info = await self._describe_object(bucket, key)

            return {
                "success": True,
                "message": f"文件上传成功: {key}",
                "bucket": bucket,
                "key": key,
                "file_path": file_path,
                "file_size": os.path.getsize(file_path),
                "file_hash": file_hash,
                "content_type": content_type,
                "object_info": object_info.get("object") if object_info.get("success") else None
            }
        except Exception as e:
            self.logger.error(f"上传文件失败: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    # 其他通用方法
    async def _copy_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> Dict[str, Any]:
        """复制存储对象"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            copy_source = {
                'Bucket': source_bucket,
                'Key': source_key
            }

            storage_client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key
            )

            return {
                "success": True,
                "message": f"对象复制成功: {source_key} -> {dest_key}",
                "source": f"{source_bucket}/{source_key}",
                "destination": f"{dest_bucket}/{dest_key}"
            }
        except Exception as e:
            self.logger.error(f"复制对象失败: {e}")
            return {"success": False, "error": str(e)}

    async def _download_file(self, bucket: str, key: str, dest_path: str) -> Dict[str, Any]:
        """下载存储对象到本地文件"""
        try:
            storage_client = self._clients.get("storage")
            if not storage_client:
                return {"success": False, "error": "云存储客户端未初始化"}

            # 确保目标目录存在
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            storage_client.download_file(bucket, key, dest_path)

            # 验证文件大小
            file_size = os.path.getsize(dest_path)

            return {
                "success": True,
                "message": f"文件下载成功: {key} -> {dest_path}",
                "bucket": bucket,
                "key": key,
                "dest_path": dest_path,
                "file_size": file_size
            }
        except Exception as e:
            self.logger.error(f"下载文件失败: {e}")
            return {"success": False, "error": str(e)}


def main():
    """主函数：运行云存储MCP服务器"""
    run_cloud_mcp_server(StorageMCP)


if __name__ == "__main__":
    main()