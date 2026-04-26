#!/usr/bin/env python3
"""
AWS云服务MCP服务器

为AI Assistant提供AWS服务操作能力：
- EC2实例管理
- S3存储操作
- RDS数据库管理
- Lambda函数操作
- CloudFormation堆栈部署
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional
from pathlib import Path

# 导入云服务MCP框架
from . import CloudServiceMCPBase, CloudServiceType, run_cloud_mcp_server


class AWSMCP(CloudServiceMCPBase):
    """AWS云服务MCP实现"""

    def __init__(self):
        super().__init__(CloudServiceType.AWS)
        self.logger = logging.getLogger("cloud-mcp.aws")

    async def _list_resources(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出AWS资源"""
        resource_type = args.get("resource_type")
        filters = args.get("filters", {})

        try:
            if resource_type == "ec2_instances":
                return await self._list_ec2_instances(filters)
            elif resource_type == "s3_buckets":
                return await self._list_s3_buckets(filters)
            elif resource_type == "rds_instances":
                return await self._list_rds_instances(filters)
            elif resource_type == "lambda_functions":
                return await self._list_lambda_functions(filters)
            elif resource_type == "cloudformation_stacks":
                return await self._list_cloudformation_stacks(filters)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "ec2_instances",
                        "s3_buckets",
                        "rds_instances",
                        "lambda_functions",
                        "cloudformation_stacks"
                    ]
                }
        except Exception as e:
            self.logger.error(f"列出资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """创建AWS资源"""
        resource_type = args.get("resource_type")
        name = args.get("name")
        spec = args.get("spec", {})
        tags = args.get("tags", {})

        try:
            if resource_type == "ec2_instance":
                return await self._create_ec2_instance(name, spec, tags)
            elif resource_type == "s3_bucket":
                return await self._create_s3_bucket(name, spec, tags)
            elif resource_type == "lambda_function":
                return await self._create_lambda_function(name, spec, tags)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "ec2_instance",
                        "s3_bucket",
                        "lambda_function"
                    ]
                }
        except Exception as e:
            self.logger.error(f"创建资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _delete_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除AWS资源"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")
        force = args.get("force", False)

        try:
            if resource_type == "ec2_instance":
                return await self._delete_ec2_instance(resource_id, force)
            elif resource_type == "s3_bucket":
                return await self._delete_s3_bucket(resource_id, force)
            elif resource_type == "lambda_function":
                return await self._delete_lambda_function(resource_id, force)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "ec2_instance",
                        "s3_bucket",
                        "lambda_function"
                    ]
                }
        except Exception as e:
            self.logger.error(f"删除资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _describe_resource(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """描述AWS资源详情"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")

        try:
            if resource_type == "ec2_instance":
                return await self._describe_ec2_instance(resource_id)
            elif resource_type == "s3_bucket":
                return await self._describe_s3_bucket(resource_id)
            elif resource_type == "rds_instance":
                return await self._describe_rds_instance(resource_id)
            elif resource_type == "lambda_function":
                return await self._describe_lambda_function(resource_id)
            elif resource_type == "cloudformation_stack":
                return await self._describe_cloudformation_stack(resource_id)
            else:
                return {
                    "success": False,
                    "error": f"不支持的资源类型: {resource_type}",
                    "supported_types": [
                        "ec2_instance",
                        "s3_bucket",
                        "rds_instance",
                        "lambda_function",
                        "cloudformation_stack"
                    ]
                }
        except Exception as e:
            self.logger.error(f"描述资源失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # AWS特定工具实现
    async def _handle_aws_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理AWS特定工具"""
        if tool_name == "aws_deploy_stack":
            return await self._aws_deploy_stack(args)
        elif tool_name == "aws_invoke_lambda":
            return await self._aws_invoke_lambda(args)
        elif tool_name == "aws_upload_to_s3":
            return await self._aws_upload_to_s3(args)
        else:
            return {
                "success": False,
                "error": f"未知的AWS工具: {tool_name}"
            }

    # EC2实例操作方法
    async def _list_ec2_instances(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出EC2实例"""
        ec2_client = self._clients.get("ec2")
        if not ec2_client:
            return {"success": False, "error": "EC2客户端未初始化"}

        try:
            # 构建过滤器
            filter_list = []
            for key, value in filters.items():
                filter_list.append({"Name": key, "Values": [value]})

            response = ec2_client.describe_instances(Filters=filter_list)

            instances = []
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instances.append({
                        "instance_id": instance.get("InstanceId"),
                        "instance_type": instance.get("InstanceType"),
                        "state": instance.get("State", {}).get("Name"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                        "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                    })

            return {
                "success": True,
                "instances": instances,
                "count": len(instances)
            }
        except Exception as e:
            self.logger.error(f"列出EC2实例失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_ec2_instance(self, name: str, spec: Dict[str, Any], tags: Dict[str, str]) -> Dict[str, Any]:
        """创建EC2实例"""
        ec2_client = self._clients.get("ec2")
        if not ec2_client:
            return {"success": False, "error": "EC2客户端未初始化"}

        try:
            # 构建标签
            tag_specifications = [
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": name}] + [{"Key": k, "Value": v} for k, v in tags.items()]
                }
            ]

            # 创建实例
            response = ec2_client.run_instances(
                ImageId=spec.get("image_id", "ami-0c55b159cbfafe1f0"),  # Amazon Linux 2 AMI
                MinCount=1,
                MaxCount=1,
                InstanceType=spec.get("instance_type", "t2.micro"),
                KeyName=spec.get("key_name"),
                SecurityGroupIds=spec.get("security_group_ids", []),
                SubnetId=spec.get("subnet_id"),
                TagSpecifications=tag_specifications
            )

            instance_id = response["Instances"][0]["InstanceId"]

            self.logger.info(f"EC2实例创建成功: {instance_id}")
            return {
                "success": True,
                "instance_id": instance_id,
                "message": f"EC2实例 {instance_id} 创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建EC2实例失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_ec2_instance(self, instance_id: str, force: bool) -> Dict[str, Any]:
        """删除EC2实例"""
        ec2_client = self._clients.get("ec2")
        if not ec2_client:
            return {"success": False, "error": "EC2客户端未初始化"}

        try:
            ec2_client.terminate_instances(InstanceIds=[instance_id])

            self.logger.info(f"EC2实例删除成功: {instance_id}")
            return {
                "success": True,
                "message": f"EC2实例 {instance_id} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除EC2实例失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        """描述EC2实例详情"""
        ec2_client = self._clients.get("ec2")
        if not ec2_client:
            return {"success": False, "error": "EC2客户端未初始化"}

        try:
            response = ec2_client.describe_instances(InstanceIds=[instance_id])

            if not response["Reservations"]:
                return {"success": False, "error": f"实例 {instance_id} 不存在"}

            instance = response["Reservations"][0]["Instances"][0]

            result = {
                "success": True,
                "instance": {
                    "instance_id": instance.get("InstanceId"),
                    "instance_type": instance.get("InstanceType"),
                    "state": instance.get("State", {}).get("Name"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_dns": instance.get("PrivateDnsName"),
                    "public_dns": instance.get("PublicDnsName"),
                    "vpc_id": instance.get("VpcId"),
                    "subnet_id": instance.get("SubnetId"),
                    "security_groups": [
                        {"id": sg.get("GroupId"), "name": sg.get("GroupName")}
                        for sg in instance.get("SecurityGroups", [])
                    ],
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                    "block_devices": [
                        {
                            "device_name": bdm.get("DeviceName"),
                            "volume_id": bdm.get("Ebs", {}).get("VolumeId")
                        }
                        for bdm in instance.get("BlockDeviceMappings", [])
                    ]
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述EC2实例失败: {e}")
            return {"success": False, "error": str(e)}

    # S3操作方法
    async def _list_s3_buckets(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出S3桶"""
        s3_client = self._clients.get("s3")
        if not s3_client:
            return {"success": False, "error": "S3客户端未初始化"}

        try:
            response = s3_client.list_buckets()

            buckets = []
            for bucket in response.get("Buckets", []):
                bucket_name = bucket["Name"]
                creation_date = bucket["CreationDate"].isoformat() if bucket.get("CreationDate") else None

                # 获取桶位置
                try:
                    location = s3_client.get_bucket_location(Bucket=bucket_name)
                    region = location.get("LocationConstraint") or "us-east-1"
                except:
                    region = "unknown"

                buckets.append({
                    "name": bucket_name,
                    "creation_date": creation_date,
                    "region": region
                })

            return {
                "success": True,
                "buckets": buckets,
                "count": len(buckets)
            }
        except Exception as e:
            self.logger.error(f"列出S3桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_s3_bucket(self, name: str, spec: Dict[str, Any], tags: Dict[str, str]) -> Dict[str, Any]:
        """创建S3桶"""
        s3_client = self._clients.get("s3")
        if not s3_client:
            return {"success": False, "error": "S3客户端未初始化"}

        try:
            region = spec.get("region", "us-east-1")

            # 创建桶
            if region == "us-east-1":
                s3_client.create_bucket(Bucket=name)
            else:
                s3_client.create_bucket(
                    Bucket=name,
                    CreateBucketConfiguration={"LocationConstraint": region}
                )

            # 添加标签
            if tags:
                tag_set = [{"Key": k, "Value": v} for k, v in tags.items()]
                s3_client.put_bucket_tagging(
                    Bucket=name,
                    Tagging={"TagSet": tag_set}
                )

            # 配置策略
            if spec.get("public_access_block"):
                s3_client.put_public_access_block(
                    Bucket=name,
                    PublicAccessBlockConfiguration={
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True
                    }
                )

            self.logger.info(f"S3桶创建成功: {name}")
            return {
                "success": True,
                "bucket_name": name,
                "region": region,
                "message": f"S3桶 {name} 创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建S3桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_s3_bucket(self, bucket_name: str, force: bool) -> Dict[str, Any]:
        """删除S3桶"""
        s3_client = self._clients.get("s3")
        if not s3_client:
            return {"success": False, "error": "S3客户端未初始化"}

        try:
            # 如果需要强制删除，先删除所有对象
            if force:
                # 列出所有对象
                objects = []
                paginator = s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket_name):
                    if "Contents" in page:
                        objects.extend([{"Key": obj["Key"]} for obj in page["Contents"]])

                # 删除所有对象
                if objects:
                    s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": objects}
                    )

            # 删除桶
            s3_client.delete_bucket(Bucket=bucket_name)

            self.logger.info(f"S3桶删除成功: {bucket_name}")
            return {
                "success": True,
                "message": f"S3桶 {bucket_name} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除S3桶失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_s3_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """描述S3桶详情"""
        s3_client = self._clients.get("s3")
        if not s3_client:
            return {"success": False, "error": "S3客户端未初始化"}

        try:
            # 获取桶信息
            bucket_info = {}

            # 获取位置
            location = s3_client.get_bucket_location(Bucket=bucket_name)
            bucket_info["region"] = location.get("LocationConstraint") or "us-east-1"

            # 获取标签
            try:
                tagging = s3_client.get_bucket_tagging(Bucket=bucket_name)
                bucket_info["tags"] = {tag["Key"]: tag["Value"] for tag in tagging.get("TagSet", [])}
            except:
                bucket_info["tags"] = {}

            # 获取对象数量
            try:
                paginator = s3_client.get_paginator("list_objects_v2")
                object_count = 0
                total_size = 0

                for page in paginator.paginate(Bucket=bucket_name):
                    if "Contents" in page:
                        object_count += len(page["Contents"])
                        total_size += sum(obj["Size"] for obj in page["Contents"])

                bucket_info["object_count"] = object_count
                bucket_info["total_size"] = total_size
                bucket_info["total_size_human"] = self._format_bytes(total_size)
            except:
                bucket_info["object_count"] = 0
                bucket_info["total_size"] = 0

            return {
                "success": True,
                "bucket_name": bucket_name,
                "info": bucket_info
            }
        except Exception as e:
            self.logger.error(f"描述S3桶失败: {e}")
            return {"success": False, "error": str(e)}

    # Lambda函数操作方法
    async def _list_lambda_functions(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出Lambda函数"""
        lambda_client = self._clients.get("lambda")
        if not lambda_client:
            return {"success": False, "error": "Lambda客户端未初始化"}

        try:
            response = lambda_client.list_functions()

            functions = []
            for func in response.get("Functions", []):
                functions.append({
                    "function_name": func.get("FunctionName"),
                    "runtime": func.get("Runtime"),
                    "handler": func.get("Handler"),
                    "memory_size": func.get("MemorySize"),
                    "timeout": func.get("Timeout"),
                    "last_modified": func.get("LastModified"),
                    "description": func.get("Description")
                })

            return {
                "success": True,
                "functions": functions,
                "count": len(functions)
            }
        except Exception as e:
            self.logger.error(f"列出Lambda函数失败: {e}")
            return {"success": False, "error": str(e)}

    async def _create_lambda_function(self, name: str, spec: Dict[str, Any], tags: Dict[str, str]) -> Dict[str, Any]:
        """创建Lambda函数"""
        lambda_client = self._clients.get("lambda")
        if not lambda_client:
            return {"success": False, "error": "Lambda客户端未初始化"}

        try:
            # 创建函数
            response = lambda_client.create_function(
                FunctionName=name,
                Runtime=spec.get("runtime", "python3.9"),
                Role=spec.get("role_arn"),
                Handler=spec.get("handler", "lambda_function.lambda_handler"),
                Code={
                    "ZipFile": spec.get("zip_file") or b""  # 简化实现，实际应该支持文件上传
                },
                Description=spec.get("description", ""),
                Timeout=spec.get("timeout", 3),
                MemorySize=spec.get("memory_size", 128),
                Publish=True,
                Environment={"Variables": spec.get("environment", {})},
                Tags=tags
            )

            function_arn = response["FunctionArn"]

            self.logger.info(f"Lambda函数创建成功: {function_arn}")
            return {
                "success": True,
                "function_arn": function_arn,
                "message": f"Lambda函数 {name} 创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建Lambda函数失败: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_lambda_function(self, function_name: str, force: bool) -> Dict[str, Any]:
        """删除Lambda函数"""
        lambda_client = self._clients.get("lambda")
        if not lambda_client:
            return {"success": False, "error": "Lambda客户端未初始化"}

        try:
            lambda_client.delete_function(FunctionName=function_name)

            self.logger.info(f"Lambda函数删除成功: {function_name}")
            return {
                "success": True,
                "message": f"Lambda函数 {function_name} 删除成功"
            }
        except Exception as e:
            self.logger.error(f"删除Lambda函数失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_lambda_function(self, function_name: str) -> Dict[str, Any]:
        """描述Lambda函数详情"""
        lambda_client = self._clients.get("lambda")
        if not lambda_client:
            return {"success": False, "error": "Lambda客户端未初始化"}

        try:
            response = lambda_client.get_function(FunctionName=function_name)

            configuration = response["Configuration"]
            code_location = response.get("Code", {}).get("Location")

            result = {
                "success": True,
                "function": {
                    "function_name": configuration.get("FunctionName"),
                    "function_arn": configuration.get("FunctionArn"),
                    "runtime": configuration.get("Runtime"),
                    "role": configuration.get("Role"),
                    "handler": configuration.get("Handler"),
                    "code_size": configuration.get("CodeSize"),
                    "description": configuration.get("Description"),
                    "timeout": configuration.get("Timeout"),
                    "memory_size": configuration.get("MemorySize"),
                    "last_modified": configuration.get("LastModified"),
                    "code_sha256": configuration.get("CodeSha256"),
                    "version": configuration.get("Version"),
                    "environment": configuration.get("Environment", {}).get("Variables", {}),
                    "code_location": code_location
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述Lambda函数失败: {e}")
            return {"success": False, "error": str(e)}

    # CloudFormation操作方法
    async def _list_cloudformation_stacks(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出CloudFormation堆栈"""
        cf_client = self._clients.get("cloudformation")
        if not cf_client:
            return {"success": False, "error": "CloudFormation客户端未初始化"}

        try:
            response = cf_client.describe_stacks()

            stacks = []
            for stack in response.get("Stacks", []):
                stacks.append({
                    "stack_name": stack.get("StackName"),
                    "stack_id": stack.get("StackId"),
                    "status": stack.get("StackStatus"),
                    "creation_time": stack.get("CreationTime").isoformat() if stack.get("CreationTime") else None,
                    "description": stack.get("Description")
                })

            return {
                "success": True,
                "stacks": stacks,
                "count": len(stacks)
            }
        except Exception as e:
            self.logger.error(f"列出CloudFormation堆栈失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_cloudformation_stack(self, stack_name: str) -> Dict[str, Any]:
        """描述CloudFormation堆栈详情"""
        cf_client = self._clients.get("cloudformation")
        if not cf_client:
            return {"success": False, "error": "CloudFormation客户端未初始化"}

        try:
            response = cf_client.describe_stacks(StackName=stack_name)

            if not response["Stacks"]:
                return {"success": False, "error": f"堆栈 {stack_name} 不存在"}

            stack = response["Stacks"][0]

            # 获取堆栈输出
            outputs = []
            for output in stack.get("Outputs", []):
                outputs.append({
                    "output_key": output.get("OutputKey"),
                    "output_value": output.get("OutputValue"),
                    "description": output.get("Description")
                })

            # 获取堆栈资源
            try:
                resources_response = cf_client.describe_stack_resources(StackName=stack_name)
                resources = [
                    {
                        "logical_resource_id": res.get("LogicalResourceId"),
                        "physical_resource_id": res.get("PhysicalResourceId"),
                        "resource_type": res.get("ResourceType"),
                        "status": res.get("ResourceStatus")
                    }
                    for res in resources_response.get("StackResources", [])
                ]
            except:
                resources = []

            result = {
                "success": True,
                "stack": {
                    "stack_name": stack.get("StackName"),
                    "stack_id": stack.get("StackId"),
                    "status": stack.get("StackStatus"),
                    "creation_time": stack.get("CreationTime").isoformat() if stack.get("CreationTime") else None,
                    "last_updated_time": stack.get("LastUpdatedTime").isoformat() if stack.get("LastUpdatedTime") else None,
                    "description": stack.get("Description"),
                    "parameters": stack.get("Parameters", []),
                    "outputs": outputs,
                    "resources": resources,
                    "tags": {tag["Key"]: tag["Value"] for tag in stack.get("Tags", [])}
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述CloudFormation堆栈失败: {e}")
            return {"success": False, "error": str(e)}

    # RDS操作方法
    async def _list_rds_instances(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """列出RDS实例"""
        rds_client = self._clients.get("rds")
        if not rds_client:
            return {"success": False, "error": "RDS客户端未初始化"}

        try:
            response = rds_client.describe_db_instances()

            instances = []
            for instance in response.get("DBInstances", []):
                instances.append({
                    "db_instance_identifier": instance.get("DBInstanceIdentifier"),
                    "engine": instance.get("Engine"),
                    "engine_version": instance.get("EngineVersion"),
                    "db_instance_class": instance.get("DBInstanceClass"),
                    "status": instance.get("DBInstanceStatus"),
                    "endpoint": {
                        "address": instance.get("Endpoint", {}).get("Address"),
                        "port": instance.get("Endpoint", {}).get("Port")
                    },
                    "allocated_storage": instance.get("AllocatedStorage"),
                    "availability_zone": instance.get("AvailabilityZone"),
                    "multi_az": instance.get("MultiAZ")
                })

            return {
                "success": True,
                "instances": instances,
                "count": len(instances)
            }
        except Exception as e:
            self.logger.error(f"列出RDS实例失败: {e}")
            return {"success": False, "error": str(e)}

    async def _describe_rds_instance(self, instance_id: str) -> Dict[str, Any]:
        """描述RDS实例详情"""
        rds_client = self._clients.get("rds")
        if not rds_client:
            return {"success": False, "error": "RDS客户端未初始化"}

        try:
            response = rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)

            if not response["DBInstances"]:
                return {"success": False, "error": f"RDS实例 {instance_id} 不存在"}

            instance = response["DBInstances"][0]

            result = {
                "success": True,
                "instance": {
                    "db_instance_identifier": instance.get("DBInstanceIdentifier"),
                    "engine": instance.get("Engine"),
                    "engine_version": instance.get("EngineVersion"),
                    "db_instance_class": instance.get("DBInstanceClass"),
                    "status": instance.get("DBInstanceStatus"),
                    "endpoint": {
                        "address": instance.get("Endpoint", {}).get("Address"),
                        "port": instance.get("Endpoint", {}).get("Port")
                    },
                    "allocated_storage": instance.get("AllocatedStorage"),
                    "storage_type": instance.get("StorageType"),
                    "availability_zone": instance.get("AvailabilityZone"),
                    "multi_az": instance.get("MultiAZ"),
                    "vpc_security_groups": [
                        {"vpc_security_group_id": sg.get("VpcSecurityGroupId"), "status": sg.get("Status")}
                        for sg in instance.get("VpcSecurityGroups", [])
                    ],
                    "db_subnet_group": instance.get("DBSubnetGroup", {}).get("DBSubnetGroupName"),
                    "publicly_accessible": instance.get("PubliclyAccessible"),
                    "instance_create_time": instance.get("InstanceCreateTime").isoformat() if instance.get("InstanceCreateTime") else None,
                    "tags": {tag["Key"]: tag["Value"] for tag in instance.get("TagList", [])}
                }
            }

            return result
        except Exception as e:
            self.logger.error(f"描述RDS实例失败: {e}")
            return {"success": False, "error": str(e)}

    # 特定工具实现
    async def _aws_deploy_stack(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """部署CloudFormation堆栈"""
        cf_client = self._clients.get("cloudformation")
        if not cf_client:
            return {"success": False, "error": "CloudFormation客户端未初始化"}

        try:
            stack_name = args["stack_name"]
            template_body = args["template_body"]
            parameters = args.get("parameters", {})
            capabilities = args.get("capabilities", [])

            # 将参数转换为CloudFormation格式
            cf_parameters = []
            for key, value in parameters.items():
                cf_parameters.append({"ParameterKey": key, "ParameterValue": str(value)})

            # 部署堆栈
            response = cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=cf_parameters,
                Capabilities=capabilities,
                OnFailure="ROLLBACK"
            )

            stack_id = response["StackId"]

            self.logger.info(f"CloudFormation堆栈部署成功: {stack_id}")
            return {
                "success": True,
                "stack_id": stack_id,
                "message": f"CloudFormation堆栈 {stack_name} 部署成功"
            }
        except Exception as e:
            self.logger.error(f"部署CloudFormation堆栈失败: {e}")
            return {"success": False, "error": str(e)}

    async def _aws_invoke_lambda(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用Lambda函数"""
        lambda_client = self._clients.get("lambda")
        if not lambda_client:
            return {"success": False, "error": "Lambda客户端未初始化"}

        try:
            function_name = args["function_name"]
            payload = args.get("payload", {})
            invocation_type = args.get("invocation_type", "RequestResponse")

            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,
                Payload=json.dumps(payload).encode()
            )

            result = {
                "success": True,
                "status_code": response["StatusCode"],
                "executed_version": response.get("ExecutedVersion")
            }

            # 如果有响应负载，解析它
            if "Payload" in response:
                try:
                    payload_data = json.loads(response["Payload"].read().decode())
                    result["payload"] = payload_data
                except:
                    result["payload_raw"] = response["Payload"].read().decode()

            # 如果有函数错误
            if "FunctionError" in response:
                result["function_error"] = response["FunctionError"]

            return result
        except Exception as e:
            self.logger.error(f"调用Lambda函数失败: {e}")
            return {"success": False, "error": str(e)}

    async def _aws_upload_to_s3(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """上传文件到S3"""
        s3_client = self._clients.get("s3")
        if not s3_client:
            return {"success": False, "error": "S3客户端未初始化"}

        try:
            bucket = args["bucket"]
            key = args["key"]
            file_path = args["file_path"]
            content_type = args.get("content_type")

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {"success": False, "error": f"文件不存在: {file_path}"}

            # 上传文件
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            s3_client.upload_file(file_path, bucket, key, ExtraArgs=extra_args)

            # 获取对象URL
            object_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            self.logger.info(f"文件上传成功: {object_url}")
            return {
                "success": True,
                "object_url": object_url,
                "bucket": bucket,
                "key": key,
                "message": f"文件上传到S3成功: {object_url}"
            }
        except Exception as e:
            self.logger.error(f"上传文件到S3失败: {e}")
            return {"success": False, "error": str(e)}

    # 辅助方法
    def _format_bytes(self, size_bytes: int) -> str:
        """格式化字节大小为人类可读格式"""
        if size_bytes == 0:
            return "0 B"

        size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1

        return f"{size_bytes:.2f} {size_names[i]}"


def main():
    """主函数：启动AWS MCP服务器"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("🚀 启动AWS云服务MCP服务器...")
    run_cloud_mcp_server(AWSMCP)


if __name__ == "__main__":
    main()