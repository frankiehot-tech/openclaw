#!/usr/bin/env python3
"""
文档版本管理器
实现语义化版本控制和文档版本历史管理
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


class DocumentVersionManager:
    """文档版本管理器"""

    def __init__(self, docs_dir="docs/", verbose=False):
        self.docs_dir = Path(docs_dir)
        self.verbose = verbose
        self.version_pattern = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

    def parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """解析版本字符串为(major, minor, patch)元组"""
        match = self.version_pattern.match(version_str)
        if not match:
            raise ValueError(f"无效的版本格式: {version_str}。应使用语义化版本格式 (如 1.0.0)")

        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def format_version(self, major: int, minor: int, patch: int) -> str:
        """格式化版本号为字符串"""
        return f"{major}.{minor}.{patch}"

    def increment_version(self, current_version: str, increment_type: str = "patch") -> str:
        """递增版本号"""
        major, minor, patch = self.parse_version(current_version)

        if increment_type == "major":
            return self.format_version(major + 1, 0, 0)
        elif increment_type == "minor":
            return self.format_version(major, minor + 1, 0)
        elif increment_type == "patch":
            return self.format_version(major, minor, patch + 1)
        else:
            raise ValueError(f"无效的递增类型: {increment_type}。可选: major, minor, patch")

    def extract_version_history(self, content: str) -> List[Dict]:
        """从文档内容中提取版本历史表"""
        version_history = []

        # 查找版本历史部分
        lines = content.split("\n")
        in_version_history = False
        in_table = False

        for i, line in enumerate(lines):
            # 查找"## 版本历史"或"## Version History"
            if line.strip().startswith("## ") and ("版本历史" in line or "Version History" in line):
                in_version_history = True
                continue

            if in_version_history:
                # 查找表格开始（包含表头分隔符）
                if "|" in line and "---" in line:
                    in_table = True
                    continue

                if in_table:
                    # 表格结束条件：空行或下一章节开始
                    if not line.strip() or line.startswith("#"):
                        break

                    # 解析表格行
                    if "|" in line:
                        # 移除首尾管道符号，分割单元格
                        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
                        if len(cells) >= 4:
                            version_entry = {
                                "version": cells[0],
                                "date": cells[1],
                                "description": cells[2],
                                "contributor": cells[3],
                            }
                            version_history.append(version_entry)

        return version_history

    def add_version_entry(
        self, content: str, version: str, description: str, contributor: str = "文档团队"
    ) -> str:
        """向文档添加版本历史条目"""
        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"| {version} | {today} | {description} | {contributor} |"

        lines = content.split("\n")
        new_lines = []

        version_history_section = -1
        table_start = -1

        # 查找版本历史部分
        for i, line in enumerate(lines):
            new_lines.append(line)

            if line.strip().startswith("## ") and ("版本历史" in line or "Version History" in line):
                version_history_section = i

                # 检查是否已有表格
                has_table = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "|" in lines[j] and "---" in lines[j]:
                        table_start = j
                        has_table = True
                        break

                if not has_table:
                    # 创建版本历史表格
                    new_lines.append("")
                    new_lines.append("| 版本 | 日期 | 更改说明 | 贡献者 |")
                    new_lines.append("|------|------|----------|--------|")
                    new_lines.append(new_entry)

        # 如果找到表格起始行，在表格后插入新条目
        if table_start != -1:
            # 查找表格结束位置（空行或下一章节）
            table_end = table_start
            for i in range(table_start + 1, len(lines)):
                if not lines[i].strip() or lines[i].startswith("#"):
                    table_end = i - 1
                    break
                table_end = i

            # 重新构建内容
            new_lines = []
            for i, line in enumerate(lines):
                if i == table_end + 1:
                    # 在表格后插入新条目
                    new_lines.append(new_entry)
                new_lines.append(line)

        return "\n".join(new_lines)

    def check_version_compatibility(self, old_version: str, new_version: str) -> Dict:
        """检查版本兼容性"""
        old_major, old_minor, old_patch = self.parse_version(old_version)
        new_major, new_minor, new_patch = self.parse_version(new_version)

        result = {
            "backward_compatible": True,
            "forward_compatible": True,
            "migration_needed": False,
            "compatibility_level": "full",
        }

        # 主版本变更通常不向后兼容
        if new_major > old_major:
            result["backward_compatible"] = False
            result["migration_needed"] = True
            result["compatibility_level"] = "major"

        # 次版本变更通常向前兼容（新功能不影响旧功能）
        elif new_minor > old_minor:
            result["backward_compatible"] = True
            result["forward_compatible"] = True
            result["compatibility_level"] = "minor"

        # 修订版本完全兼容
        elif new_patch > old_patch:
            result["compatibility_level"] = "patch"

        return result

    def analyze_document_versions(self, doc_path: Path) -> Dict:
        """分析文档的版本信息"""
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 提取版本历史
            version_history = self.extract_version_history(content)

            # 查找文档中的版本号引用
            version_refs = []
            version_patterns = [
                r"版本[:：]\s*(\d+\.\d+(?:\.\d+)?)",
                r"Version[:：]\s*(\d+\.\d+(?:\.\d+)?)",
                r"v(\d+\.\d+(?:\.\d+)?)\b",
            ]

            for pattern in version_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                version_refs.extend(matches)

            # 确定当前版本
            current_version = None
            if version_history:
                current_version = version_history[0]["version"]  # 假设最新版本在第一行

            return {
                "file_path": str(doc_path.relative_to(self.docs_dir)),
                "current_version": current_version,
                "version_history_count": len(version_history),
                "version_references": list(set(version_refs)),
                "has_version_history": len(version_history) > 0,
                "version_history": version_history[:3],  # 只返回前3个条目
            }

        except Exception as e:
            return {"file_path": str(doc_path.relative_to(self.docs_dir)), "error": str(e)}

    def generate_version_report(self, output_file: Optional[str] = None) -> Dict:
        """生成文档版本报告"""
        print("📊 分析文档版本信息...")

        # 查找所有Markdown文件
        md_files = list(self.docs_dir.rglob("*.md"))

        version_data = {
            "generated_at": datetime.now().isoformat(),
            "total_documents": len(md_files),
            "documents_with_version": 0,
            "version_summary": {},
            "documents": [],
        }

        for i, md_file in enumerate(md_files):
            if self.verbose and (i + 1) % 10 == 0:
                print(f"  分析进度: {i+1}/{len(md_files)}")

            doc_analysis = self.analyze_document_versions(md_file)
            version_data["documents"].append(doc_analysis)

            if doc_analysis.get("has_version_history"):
                version_data["documents_with_version"] += 1

                # 统计版本分布
                version = doc_analysis.get("current_version")
                if version:
                    version_data["version_summary"][version] = (
                        version_data["version_summary"].get(version, 0) + 1
                    )

        # 生成摘要
        print(f"📄 总文档数: {version_data['total_documents']}")
        print(
            f"📋 有版本历史的文档: {version_data['documents_with_version']} ({version_data['documents_with_version']/max(version_data['total_documents'], 1)*100:.1f}%)"
        )

        if version_data["version_summary"]:
            print("📈 版本分布:")
            for version, count in sorted(
                version_data["version_summary"].items(), key=lambda x: self.parse_version(x[0])
            ):
                print(f"  v{version}: {count} 个文档")

        # 保存报告
        if output_file:
            output_path = Path(output_file)
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(version_data, f, indent=2, ensure_ascii=False)
                print(f"✅ 版本报告已保存: {output_path}")
            except Exception as e:
                print(f"❌ 保存报告失败: {e}")

        return version_data

    def update_document_version(
        self,
        file_path: str,
        increment_type: str = "patch",
        description: str = "文档更新",
        contributor: str = "文档团队",
        dry_run: bool = False,
    ) -> Dict:
        """更新文档版本"""
        doc_path = Path(file_path)
        if not doc_path.is_absolute():
            doc_path = self.docs_dir / file_path

        if not doc_path.exists():
            return {"success": False, "error": f"文件不存在: {doc_path}"}

        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 分析当前版本
            analysis = self.analyze_document_versions(doc_path)
            current_version = analysis.get("current_version")

            if not current_version:
                current_version = "1.0.0"
                print(f"🔍 文档没有版本历史，将创建初始版本 {current_version}")

            # 递增版本
            new_version = self.increment_version(current_version, increment_type)

            print(f"🔄 更新版本: {current_version} → {new_version} ({increment_type})")
            print(f"📝 更新说明: {description}")

            # 检查版本兼容性
            if current_version != "1.0.0":
                compatibility = self.check_version_compatibility(current_version, new_version)
                if compatibility.get("migration_needed"):
                    print(f"⚠️  注意: 主版本变更可能需要迁移指南")

            # 添加版本历史条目
            new_content = self.add_version_entry(content, new_version, description, contributor)

            if not dry_run:
                # 备份原文件
                backup_path = doc_path.with_suffix(".md.backup")
                import shutil

                shutil.copy2(doc_path, backup_path)

                # 写入新内容
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                result = {
                    "success": True,
                    "file": str(doc_path.relative_to(self.docs_dir)),
                    "old_version": current_version,
                    "new_version": new_version,
                    "increment_type": increment_type,
                    "backup_file": str(backup_path.relative_to(self.docs_dir)),
                    "description": description,
                }

                print(f"✅ 文档版本更新成功")
                if self.verbose:
                    print(f"   备份文件: {result['backup_file']}")

                return result
            else:
                print(f"🔍 模拟运行: 将更新 {doc_path} 到版本 {new_version}")
                return {
                    "success": True,
                    "dry_run": True,
                    "file": str(doc_path.relative_to(self.docs_dir)),
                    "old_version": current_version,
                    "new_version": new_version,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="文档版本管理器")
    parser.add_argument("--directory", "-d", default="docs/", help="文档目录 (默认: docs/)")
    parser.add_argument("--report", "-r", action="store_true", help="生成文档版本报告")
    parser.add_argument("--report-output", "-o", help="报告输出文件路径")
    parser.add_argument("--update", "-u", help="更新指定文档的版本")
    parser.add_argument(
        "--increment",
        "-i",
        default="patch",
        choices=["major", "minor", "patch"],
        help="版本递增类型 (默认: patch)",
    )
    parser.add_argument("--description", "-m", default="文档更新", help="版本更新说明")
    parser.add_argument("--contributor", "-c", default="文档团队", help="贡献者名称")
    parser.add_argument("--dry-run", "-n", action="store_true", help="模拟运行，不实际修改文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"❌ 目录不存在: {args.directory}")
        sys.exit(1)

    manager = DocumentVersionManager(docs_dir=args.directory, verbose=args.verbose)

    # 生成版本报告
    if args.report:
        report_data = manager.generate_version_report(output_file=args.report_output)

        # 如果有文档没有版本历史，显示建议
        total = report_data["total_documents"]
        with_version = report_data["documents_with_version"]
        if with_version < total:
            print(f"\n💡 建议: {total - with_version} 个文档没有版本历史")
            print("  可使用以下命令添加版本历史:")
            print(
                "  python3 scripts/document_version_manager.py --update <文档路径> --description '初始版本'"
            )

        sys.exit(0)

    # 更新文档版本
    elif args.update:
        result = manager.update_document_version(
            file_path=args.update,
            increment_type=args.increment,
            description=args.description,
            contributor=args.contributor,
            dry_run=args.dry_run,
        )

        if result.get("success"):
            if not args.dry_run:
                print(f"✅ 版本更新成功: {result['old_version']} → {result['new_version']}")
            sys.exit(0)
        else:
            print(f"❌ 版本更新失败: {result.get('error', '未知错误')}")
            sys.exit(1)

    else:
        # 默认显示帮助信息
        print("📚 文档版本管理器")
        print("\n使用方法:")
        print("  生成版本报告: python3 scripts/document_version_manager.py --report")
        print(
            "  更新文档版本: python3 scripts/document_version_manager.py --update <文档路径> --description '更新说明'"
        )
        print("\n示例:")
        print(
            "  python3 scripts/document_version_manager.py --report --report-output version_report.json"
        )
        print(
            "  python3 scripts/document_version_manager.py --update docs/user/guide.md --description '添加新功能说明' --increment minor"
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
