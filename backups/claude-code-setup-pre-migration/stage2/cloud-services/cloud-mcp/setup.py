#!/usr/bin/env python3
"""
云服务MCP框架安装脚本

安装命令:
    pip install -e .
或
    python setup.py install
"""

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cloud-mcp",
    version="1.0.0",
    description="AI Assistant云服务MCP框架 - 提供AWS、Docker、Kubernetes等云服务的统一操作接口",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Assistant全栈开发平台",
    author_email="noreply@example.com",
    url="https://github.com/anthropics/claude-code-setup",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords="claude-code, mcp, cloud, aws, docker, kubernetes, serverless, storage",
    entry_points={
        "console_scripts": [
            "cloud-mcp-aws=cloud_mcp.aws:main",
            "cloud-mcp-docker=cloud_mcp.docker:main",
            "cloud-mcp-kubernetes=cloud_mcp.kubernetes:main",
            "cloud-mcp-serverless=cloud_mcp.serverless:main",
            "cloud-mcp-storage=cloud_mcp.storage:main",
        ],
    },
    project_urls={
        "Documentation": "https://github.com/anthropics/claude-code-setup",
        "Source": "https://github.com/anthropics/claude-code-setup",
        "Tracker": "https://github.com/anthropics/claude-code-setup/issues",
    },
)