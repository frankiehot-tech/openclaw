#!/usr/bin/env python3
"""
文档索引更新工具
扫描docs目录并更新文档索引文件
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


class DocumentIndexUpdater:
    """文档索引更新器"""

    def __init__(self, docs_dir="docs/", verbose=False):
        self.docs_dir = Path(docs_dir)
        self.verbose = verbose
        self.index_data = {
            "generated_at": datetime.now().isoformat(),
            "total_files": 0,
            "categories": {},
            "file_index": [],
        }

    def scan_document_structure(self):
        """扫描文档目录结构"""
        print(f"📁 扫描文档目录: {self.docs_dir}")

        categories = {
            "architecture": "架构文档",
            "technical": "技术文档",
            "audit": "审计文档",
            "user": "用户文档",
            "skills": "技能文档",
            "vendor": "第三方文档",
        }

        total_files = 0

        for category, description in categories.items():
            category_path = self.docs_dir / category
            category_files = []

            if category_path.exists() and category_path.is_dir():
                # 查找所有Markdown文件
                md_files = list(category_path.rglob("*.md"))
                total_files += len(md_files)

                for md_file in md_files:
                    rel_path = md_file.relative_to(self.docs_dir)
                    stats = md_file.stat()

                    file_info = {
                        "path": str(rel_path),
                        "name": md_file.name,
                        "size": stats.st_size,
                        "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        "category": category,
                    }

                    category_files.append(file_info)
                    self.index_data["file_index"].append(file_info)

                if self.verbose:
                    print(f"  {category} ({description}): {len(md_files)} 个文件")

                self.index_data["categories"][category] = {
                    "description": description,
                    "file_count": len(md_files),
                    "files": category_files[:20],  # 只保留前20个文件用于显示
                }

        self.index_data["total_files"] = total_files
        print(f"📄 总计: {total_files} 个Markdown文件")

        return total_files

    def update_readme_index(self):
        """更新docs/README.md索引"""
        readme_path = self.docs_dir / "README.md"

        if not readme_path.exists():
            print(f"❌ README.md文件不存在: {readme_path}")
            return False

        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read()

            # 查找## 文档结构部分之后的部分
            lines = content.split("\n")
            new_lines = []
            in_structure_section = False
            structure_section_end = False

            for line in lines:
                if line.startswith("## 文档结构"):
                    in_structure_section = True
                    new_lines.append(line)
                    new_lines.append("")  # 空行
                elif in_structure_section and line.startswith("## "):
                    # 遇到下一个章节，插入自动生成的文件列表
                    if not structure_section_end:
                        self._append_auto_generated_index(new_lines)
                        structure_section_end = True
                    in_structure_section = False
                    new_lines.append(line)
                elif in_structure_section:
                    # 跳过原有内容，我们将用新的索引替换
                    continue
                else:
                    new_lines.append(line)

            # 如果文档中没有其他章节，在末尾添加索引
            if in_structure_section and not structure_section_end:
                self._append_auto_generated_index(new_lines)

            # 更新最后更新日期
            for i in range(len(new_lines) - 1, -1, -1):
                if new_lines[i].startswith("**最后更新**:"):
                    new_lines[i] = f"**最后更新**: {datetime.now().strftime('%Y-%m-%d')}"
                    break

            new_content = "\n".join(new_lines)

            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"✅ 已更新文档索引: {readme_path}")
            return True

        except Exception as e:
            print(f"❌ 更新README.md失败: {e}")
            return False

    def _append_auto_generated_index(self, lines):
        """添加自动生成的索引到README"""
        lines.append("### 📊 文档统计")
        lines.append(f"- **总文档数**: {self.index_data['total_files']} 个Markdown文件")
        lines.append(f"- **索引生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 按类别显示统计
        lines.append("### 📁 按类别统计")
        for category, data in self.index_data["categories"].items():
            lines.append(f"#### {data['description']} (`{category}/`)")
            lines.append(f"- **文件数**: {data['file_count']}")

            # 显示部分文件
            if data["files"]:
                lines.append("- **部分文件**:")
                for file_info in data["files"][:10]:  # 只显示前10个
                    lines.append(f"  - [{file_info['name']}]({file_info['path']})")
                if data["file_count"] > 10:
                    lines.append(f"  - ... 还有 {data['file_count'] - 10} 个文件")
            lines.append("")

        lines.append("### 🔍 快速查找")
        lines.append('- 使用 `find docs/ -name "*.md" | grep <关键词>` 查找文档')
        lines.append('- 按年月查找审计报告: `find docs/audit -name "*.md"`')
        lines.append("- 查看技术规范: `ls docs/technical/specifications/`")
        lines.append("")

    def generate_json_index(self, output_file=None):
        """生成JSON格式的索引文件"""
        if output_file is None:
            output_file = self.docs_dir / "document_index.json"

        try:
            import json

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.index_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 已生成JSON索引: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 生成JSON索引失败: {e}")
            return False

    def check_missing_metadata(self):
        """检查缺失元数据的文档"""
        print("\n🔍 检查文档元数据...")

        missing_metadata = []
        for file_info in self.index_data["file_index"][:50]:  # 只检查前50个文件
            file_path = self.docs_dir / file_info["path"]

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # 检查是否包含最后更新日期
                if (
                    "最后更新" not in content
                    and "Last updated" not in content
                    and "Updated" not in content
                ):
                    missing_metadata.append(
                        {"file": file_info["path"], "reason": "缺少最后更新日期"}
                    )

            except Exception as e:
                missing_metadata.append({"file": file_info["path"], "reason": f"读取失败: {e}"})

        if missing_metadata:
            print(f"⚠️  发现 {len(missing_metadata)} 个文档缺少元数据:")
            for item in missing_metadata[:10]:  # 只显示前10个
                print(f"  - {item['file']}: {item['reason']}")
            if len(missing_metadata) > 10:
                print(f"    ... 还有 {len(missing_metadata) - 10} 个文档")

            # 生成修复建议
            print("\n💡 修复建议:")
            print('  python3 scripts/batch_update_documents.py --pattern "*.md" --update-metadata')
            return False
        else:
            print("✅ 所有检查的文档都包含元数据")
            return True


def main():
    parser = argparse.ArgumentParser(description="更新文档索引")
    parser.add_argument("--directory", "-d", default="docs/", help="文档目录 (默认: docs/)")
    parser.add_argument("--update-readme", "-r", action="store_true", help="更新docs/README.md索引")
    parser.add_argument("--generate-json", "-j", action="store_true", help="生成JSON格式索引文件")
    parser.add_argument("--json-output", "-o", help="JSON索引输出文件路径")
    parser.add_argument("--check-metadata", "-m", action="store_true", help="检查缺失的文档元数据")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"❌ 目录不存在: {args.directory}")
        sys.exit(1)

    updater = DocumentIndexUpdater(docs_dir=args.directory, verbose=args.verbose)

    # 扫描文档结构
    total_files = updater.scan_document_structure()

    if total_files == 0:
        print("⚠️  未找到Markdown文件，请检查目录路径")
        sys.exit(0)

    success = True

    # 更新README.md索引
    if args.update_readme and not updater.update_readme_index():
        success = False

    # 生成JSON索引
    if args.generate_json:
        output_file = args.json_output if args.json_output else None
        if not updater.generate_json_index(output_file):
            success = False

    # 检查元数据
    if args.check_metadata and not updater.check_missing_metadata():
        success = False

    # 如果没有指定任何操作，默认更新README
    if not args.update_readme and not args.generate_json and not args.check_metadata:
        print("\n💡 未指定操作，默认更新README.md索引")
        if updater.update_readme_index():
            print("✅ 索引更新完成")
        else:
            success = False

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
