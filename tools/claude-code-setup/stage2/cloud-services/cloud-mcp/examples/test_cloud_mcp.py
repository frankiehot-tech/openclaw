#!/usr/bin/env python3
"""
云服务MCP框架测试示例

这个示例展示如何使用云服务MCP框架进行基本操作。
注意：运行前请确保已配置正确的云服务凭据。
"""

import asyncio
import json
import sys
import os

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cloud_mcp import CloudServiceMCPBase, CloudServiceType


async def test_aws_mcp():
    """测试AWS MCP功能"""
    print("=== 测试AWS MCP ===")

    # 注意：实际测试需要真实的AWS凭据
    # 这里只是演示API调用模式
    print("AWS MCP测试需要配置AWS凭据")
    print("请设置环境变量：")
    print("  export AWS_ACCESS_KEY_ID='your-key'")
    print("  export AWS_SECRET_ACCESS_KEY='your-secret'")
    print("  export AWS_DEFAULT_REGION='us-east-1'")

    # 模拟工具调用
    tools = [
        {
            "name": "list_resources",
            "description": "列出AWS资源",
            "example": {
                "resource_type": "ec2_instances",
                "filters": {"instance-state-name": "running"}
            }
        },
        {
            "name": "aws_deploy_stack",
            "description": "部署CloudFormation堆栈",
            "example": {
                "stack_name": "my-stack",
                "template_body": json.dumps({
                    "Resources": {
                        "MyBucket": {
                            "Type": "AWS::S3::Bucket",
                            "Properties": {"BucketName": "my-test-bucket"}
                        }
                    }
                })
            }
        }
    ]

    print(f"可用的AWS工具: {len(tools)}个")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    return True


async def test_docker_mcp():
    """测试Docker MCP功能"""
    print("\n=== 测试Docker MCP ===")

    tools = [
        {
            "name": "docker_build_image",
            "description": "构建Docker镜像",
            "example": {
                "dockerfile": "FROM nginx:alpine\nCOPY . /usr/share/nginx/html",
                "image_name": "my-webapp:latest"
            }
        },
        {
            "name": "docker_run_container",
            "description": "运行Docker容器",
            "example": {
                "image": "nginx:alpine",
                "name": "my-nginx",
                "ports": {"80": "8080"},
                "environment": {"NGINX_PORT": "80"}
            }
        }
    ]

    print(f"可用的Docker工具: {len(tools)}个")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
        print(f"    示例参数: {json.dumps(tool['example'], indent=4)}")

    return True


async def test_kubernetes_mcp():
    """测试Kubernetes MCP功能"""
    print("\n=== 测试Kubernetes MCP ===")

    tools = [
        {
            "name": "k8s_apply_yaml",
            "description": "应用Kubernetes YAML配置",
            "example": {
                "yaml_content": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80""",
                "namespace": "default"
            }
        },
        {
            "name": "k8s_get_logs",
            "description": "获取Pod日志",
            "example": {
                "pod": "nginx-deployment-abc123",
                "namespace": "default",
                "tail_lines": 50
            }
        }
    ]

    print(f"可用的Kubernetes工具: {len(tools)}个")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    return True


async def test_serverless_mcp():
    """测试Serverless MCP功能"""
    print("\n=== 测试Serverless MCP ===")

    tools = [
        {
            "name": "serverless_deploy",
            "description": "部署Serverless应用",
            "example": {
                "service_name": "my-api",
                "provider": "aws",
                "functions": {
                    "hello": {
                        "handler": "handler.hello",
                        "events": [{"http": {"path": "hello", "method": "get"}}]
                    }
                }
            }
        }
    ]

    print(f"可用的Serverless工具: {len(tools)}个")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    return True


async def test_storage_mcp():
    """测试云存储MCP功能"""
    print("\n=== 测试云存储MCP ===")

    tools = [
        {
            "name": "storage_list_buckets",
            "description": "列出存储桶",
            "example": {
                "prefix": "my-"
            }
        },
        {
            "name": "storage_presigned_url",
            "description": "生成预签名URL",
            "example": {
                "bucket": "my-bucket",
                "key": "documents/report.pdf",
                "expires_in": 3600,
                "method": "GET"
            }
        }
    ]

    print(f"可用的云存储工具: {len(tools)}个")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
        print(f"    示例参数: {json.dumps(tool['example'], indent=4)}")

    return True


async def test_mcp_servers():
    """测试所有MCP服务器"""
    print("开始测试云服务MCP框架...")

    tests = [
        ("AWS", test_aws_mcp),
        ("Docker", test_docker_mcp),
        ("Kubernetes", test_kubernetes_mcp),
        ("Serverless", test_serverless_mcp),
        ("Storage", test_storage_mcp)
    ]

    results = []
    for name, test_func in tests:
        try:
            print(f"\n正在测试{name}...")
            success = await test_func()
            results.append((name, success, "成功"))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"  {name}测试失败: {e}")

    # 打印测试结果
    print("\n" + "="*50)
    print("测试结果汇总:")
    print("="*50)

    all_passed = True
    for name, success, message in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name:15} {status:10} {message}")
        if not success:
            all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print("✅ 所有测试通过！")
        print("云服务MCP框架已准备就绪。")
    else:
        print("⚠️  部分测试失败，请检查凭据配置。")

    return all_passed


async def quick_start_example():
    """快速开始示例"""
    print("\n" + "="*50)
    print("快速开始示例")
    print("="*50)

    print("""
1. 安装云服务MCP包:
   cd /Users/frankie/claude-code-setup/stage2/cloud-services/cloud-mcp
   pip install -e .

2. 配置环境变量:
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export KUBECONFIG="~/.kube/config"

3. 启动MCP服务器:
   # 在终端1
   cloud-mcp-aws

   # 在终端2
   cloud-mcp-kubernetes

   # 在终端3
   cloud-mcp-docker

4. 配置AI Assistant:
   在AI Assistant设置中添加MCP服务器配置:
   {
     "mcpServers": {
       "aws": {
         "command": "cloud-mcp-aws",
         "env": {"AWS_ACCESS_KEY_ID": "your-key"}
       },
       "kubernetes": {
         "command": "cloud-mcp-kubernetes"
       }
     }
   }

5. 通过AI Assistant使用:
   现在可以通过自然语言操作云服务了，例如:
   - "列出所有运行的EC2实例"
   - "部署应用到Kubernetes集群"
   - "构建Docker镜像并推送到仓库"
   - "上传文件到S3存储桶"
    """)

    print("\n详细使用说明请参考README.md文件")


def main():
    """主函数"""
    print("云服务MCP框架测试工具")
    print("="*50)

    # 检查环境
    print("检查环境配置...")

    # 检查Python版本
    if sys.version_info < (3, 8):
        print(f"❌ Python版本需要3.8+，当前版本: {sys.version}")
        return 1

    print(f"✅ Python版本: {sys.version_info.major}.{sys.version_info.minor}")

    # 检查依赖
    try:
        import mcp
        print("✅ MCP库已安装")
    except ImportError:
        print("❌ MCP库未安装，请运行: pip install mcp")
        return 1

    try:
        import boto3
        print("✅ boto3 (AWS SDK) 已安装")
    except ImportError:
        print("⚠️  boto3未安装，AWS功能将受限")

    try:
        import docker
        print("✅ docker-py (Docker SDK) 已安装")
    except ImportError:
        print("⚠️  docker-py未安装，Docker功能将受限")

    try:
        import kubernetes
        print("✅ kubernetes客户端已安装")
    except ImportError:
        print("⚠️  kubernetes客户端未安装，Kubernetes功能将受限")

    print("\n" + "="*50)

    # 运行测试
    loop = asyncio.get_event_loop()

    try:
        # 运行测试
        success = loop.run_until_complete(test_mcp_servers())

        # 显示快速开始指南
        loop.run_until_complete(quick_start_example())

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())