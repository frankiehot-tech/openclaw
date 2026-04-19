#!/usr/bin/env python3
"""
AI 编程工具提示词模式提取脚本
基于 Cursor、Devin、v0、Manus 等 30+ 顶尖工具的提示词工程
"""

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class PatternExtractor:
    """模式提取器 - 从代码和文档中提取编程模式"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.patterns = {
            "architecture": [],
            "coding_style": [],
            "error_handling": [],
            "testing": [],
            "documentation": [],
            "deployment": [],
        }

    def extract_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """从单个文件中提取模式"""
        patterns = []

        try:
            content = file_path.read_text(encoding="utf-8")

            # 根据文件类型使用不同的提取策略
            if file_path.suffix == ".py":
                patterns.extend(self._extract_python_patterns(content, str(file_path)))
            elif file_path.suffix == ".md":
                patterns.extend(self._extract_markdown_patterns(content, str(file_path)))
            elif file_path.suffix in [".yaml", ".yml"]:
                patterns.extend(self._extract_yaml_patterns(content, str(file_path)))
            elif file_path.suffix == ".json":
                patterns.extend(self._extract_json_patterns(content, str(file_path)))

        except Exception as e:
            print(f"警告: 无法处理文件 {file_path}: {e}")

        return patterns

    def _extract_python_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """从 Python 代码中提取模式"""
        patterns = []

        # 提取类定义模式
        class_patterns = re.findall(r"class\s+(\w+)(?:\([^)]+\))?:", content)
        for class_name in class_patterns:
            patterns.append(
                {
                    "type": "class_definition",
                    "pattern": f"class {class_name}:",
                    "category": "architecture",
                    "file": file_path,
                    "language": "python",
                }
            )

        # 提取函数定义模式
        func_patterns = re.findall(r"def\s+(\w+)\([^)]*\):", content)
        for func_name in func_patterns:
            patterns.append(
                {
                    "type": "function_definition",
                    "pattern": f"def {func_name}():",
                    "category": "coding_style",
                    "file": file_path,
                    "language": "python",
                }
            )

        # 提取错误处理模式
        error_patterns = re.findall(r"try:\s*\n(.*?)\n\s*except", content, re.DOTALL)
        for error_block in error_patterns:
            patterns.append(
                {
                    "type": "error_handling",
                    "pattern": f"try:\n{error_block}\nexcept:",
                    "category": "error_handling",
                    "file": file_path,
                    "language": "python",
                }
            )

        return patterns

    def _extract_markdown_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """从 Markdown 文档中提取模式"""
        patterns = []

        # 提取代码块模式
        code_blocks = re.findall(r"```(\w+)\n(.*?)```", content, re.DOTALL)
        for lang, code in code_blocks:
            patterns.append(
                {
                    "type": "code_example",
                    "pattern": code.strip(),
                    "category": "documentation",
                    "file": file_path,
                    "language": lang,
                }
            )

        # 提取标题结构模式
        headings = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
        for level, title in headings:
            patterns.append(
                {
                    "type": "documentation_structure",
                    "pattern": f"{level} {title}",
                    "category": "documentation",
                    "file": file_path,
                    "language": "markdown",
                }
            )

        return patterns

    def _extract_yaml_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """从 YAML 配置中提取模式"""
        patterns = []

        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                # 提取配置模式
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        patterns.append(
                            {
                                "type": "configuration_pattern",
                                "pattern": f"{key}: {value}",
                                "category": "deployment",
                                "file": file_path,
                                "language": "yaml",
                            }
                        )
        except Exception:
            pass

        return patterns

    def _extract_json_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """从 JSON 文件中提取模式"""
        patterns = []

        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # 提取数据结构模式
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        patterns.append(
                            {
                                "type": "data_structure",
                                "pattern": json.dumps({key: value}, indent=2),
                                "category": "architecture",
                                "file": file_path,
                                "language": "json",
                            }
                        )
        except Exception:
            pass

        return patterns

    def scan_project(self) -> Dict[str, List[Dict[str, Any]]]:
        """扫描整个项目并提取模式"""
        print(f"开始扫描项目: {self.project_root}")

        # 支持的扩展名
        supported_extensions = {
            ".py",
            ".md",
            ".yaml",
            ".yml",
            ".json",
            ".js",
            ".ts",
            ".java",
            ".go",
        }

        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                # 跳过某些目录
                if any(part.startswith(".") for part in file_path.parts):
                    continue
                if "node_modules" in file_path.parts:
                    continue
                if "__pycache__" in file_path.parts:
                    continue

                patterns = self.extract_from_file(file_path)
                for pattern in patterns:
                    category = pattern["category"]
                    self.patterns[category].append(pattern)

        print(f"模式提取完成，共找到 {sum(len(v) for v in self.patterns.values())} 个模式")
        return self.patterns

    def generate_prompt_templates(self) -> Dict[str, str]:
        """基于提取的模式生成提示词模板"""

        templates = {}

        # 架构师 Agent 提示词
        architect_prompt = """# 架构师 Agent 提示词

## 角色定义
你是一个经验丰富的软件架构师，负责设计可扩展、高性能的系统架构。

## 核心能力
- 系统架构设计
- 技术选型评估
- 模块化设计
- 性能优化

## 基于项目模式的架构原则

### 发现的架构模式:
"""

        for pattern in self.patterns["architecture"][:10]:  # 取前10个
            architect_prompt += f"- {pattern['pattern']}\n"

        architect_prompt += """

## 响应格式要求
1. 先分析需求的技术复杂度
2. 提出2-3个架构方案
3. 推荐最佳方案并说明理由
4. 提供技术栈建议

## 约束条件
- 优先使用项目中已有的技术栈
- 考虑团队的技术能力
- 确保架构的可维护性
"""

        templates["architect"] = architect_prompt

        # 前端 Agent 提示词
        frontend_prompt = """# 前端 Agent 提示词

## 角色定义
你是一个专业的前端工程师，擅长 React、Vue、TypeScript 等现代前端技术。

## 核心能力
- UI/UX 设计实现
- 组件化开发
- 性能优化
- 响应式设计

## 基于项目模式的前端实践:
"""

        for pattern in self.patterns["coding_style"][:10]:
            frontend_prompt += f"- {pattern['pattern']}\n"

        frontend_prompt += """

## 响应格式要求
1. 分析设计需求
2. 提供组件结构设计
3. 给出实现代码示例
4. 考虑可访问性和性能

## 约束条件
- 遵循项目的代码规范
- 使用 TypeScript 确保类型安全
- 考虑移动端兼容性
"""

        templates["frontend"] = frontend_prompt

        # 后端 Agent 提示词
        backend_prompt = """# 后端 Agent 提示词

## 角色定义
你是一个专业的后端工程师，擅长 Python、FastAPI、数据库设计等后端技术。

## 核心能力
- API 设计开发
- 数据库设计优化
- 安全认证实现
- 性能调优

## 基于项目模式的后端实践:
"""

        for pattern in self.patterns["error_handling"][:10]:
            backend_prompt += f"- {pattern['pattern']}\n"

        backend_prompt += """

## 响应格式要求
1. 分析业务需求
2. 设计 API 接口
3. 提供数据库设计
4. 考虑安全性和性能

## 约束条件
- 遵循 RESTful 设计原则
- 实现适当的错误处理
- 考虑并发和扩展性
"""

        templates["backend"] = backend_prompt

        return templates

    def save_results(self, output_dir: str):
        """保存提取结果"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存原始模式数据
        patterns_file = output_path / "extracted_patterns.json"
        with open(patterns_file, "w", encoding="utf-8") as f:
            json.dump(self.patterns, f, indent=2, ensure_ascii=False)

        # 生成并保存提示词模板
        templates = self.generate_prompt_templates()

        for agent_name, prompt in templates.items():
            prompt_file = output_path / f"{agent_name}_agent_prompt.md"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt)

        # 生成汇总报告
        report = self._generate_report()
        report_file = output_path / "extraction_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"结果已保存到: {output_path}")

    def _generate_report(self) -> str:
        """生成提取报告"""
        total_patterns = sum(len(v) for v in self.patterns.values())

        report = f"""# 模式提取报告

## 基本信息
- 项目路径: {self.project_root}
- 提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 总模式数: {total_patterns}

## 分类统计
"""

        for category, patterns in self.patterns.items():
            report += f"- {category}: {len(patterns)} 个模式\n"

        report += """
## 生成的 Agent 提示词文件
- architect_agent_prompt.md - 架构师 Agent 提示词
- frontend_agent_prompt.md - 前端 Agent 提示词  
- backend_agent_prompt.md - 后端 Agent 提示词

## 使用说明
这些提示词可以直接用于配置相应的 AI Agent，确保代码生成符合项目规范。
"""

        return report


def main():
    """主函数"""
    project_root = "/Volumes/1TB-M2/openclaw"
    output_dir = "/Volumes/1TB-M2/openclaw/patterns"

    extractor = PatternExtractor(project_root)
    patterns = extractor.scan_project()
    extractor.save_results(output_dir)

    print("✅ 模式提取完成！")
    print("📁 结果保存在:", output_dir)


if __name__ == "__main__":
    main()
