#!/usr/bin/env python3
"""
批量文档更新工具
批量更新Markdown文档的元数据（最后更新日期、版本等）
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path


class BatchDocumentUpdater:
    """批量文档更新器"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.updated_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.today = datetime.now().strftime("%Y-%m-%d")

    def update_document_metadata(
        self, file_path, update_last_updated=True, update_version=False, dry_run=False
    ):
        """更新单个文档的元数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            updated = False
            new_lines = []

            last_updated_patterns = [
                r"^最后更新\s*[:：]\s*\d{4}-\d{2}-\d{2}",
                r"^Last updated\s*[:：]\s*\d{4}-\d{2}-\d{2}",
                r"^Updated\s*[:：]\s*\d{4}-\d{2}-\d{2}",
            ]

            version_patterns = [
                r"^版本\s*[:：]\s*[\d\.]+",
                r"^Version\s*[:：]\s*[\d\.]+",
                r"^v[\d\.]+\s*$",
            ]

            for line in lines:
                original_line = line
                line_updated = False

                # 更新最后更新日期
                if update_last_updated:
                    for pattern in last_updated_patterns:
                        if re.match(pattern, line):
                            # 替换日期部分
                            new_line = re.sub(r"\d{4}-\d{2}-\d{2}", self.today, line)
                            if new_line != line:
                                line = new_line
                                line_updated = True
                                if self.verbose:
                                    print(f"    更新最后更新日期: {original_line} → {line}")
                            break

                # 更新版本信息（如果需要）
                if update_version and not line_updated:
                    for pattern in version_patterns:
                        if re.match(pattern, line):
                            # 这里可以添加版本更新逻辑，暂时只记录
                            if self.verbose:
                                print(f"    找到版本信息: {line}")
                            break

                new_lines.append(line)
                if line_updated:
                    updated = True

            # 如果文档中没有最后更新日期，在文档末尾添加
            if update_last_updated and not updated:
                # 检查是否已有最后更新日期（可能在文档中间）
                has_last_updated = any(
                    re.search(pattern, content) for pattern in last_updated_patterns
                )

                if not has_last_updated:
                    # 在文档末尾添加最后更新日期
                    if new_lines and new_lines[-1].strip():
                        new_lines.append("")  # 添加空行分隔
                    new_lines.append(f"最后更新: {self.today}")
                    updated = True
                    if self.verbose:
                        print(f"    添加最后更新日期: 最后更新: {self.today}")

            if updated and not dry_run:
                new_content = "\n".join(new_lines)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.updated_count += 1
                return True
            elif dry_run and updated:
                self.updated_count += 1
                return True
            else:
                self.skipped_count += 1
                return False

        except Exception as e:
            print(f"❌ 更新文件失败 {file_path}: {e}")
            self.failed_count += 1
            return False

    def update_documents_by_pattern(
        self, pattern, root_dir=".", update_last_updated=True, update_version=False, dry_run=False
    ):
        """根据模式批量更新文档"""
        root_path = Path(root_dir)
        md_files = list(root_path.rglob(pattern))

        if not md_files:
            print(f"📭 未找到匹配模式 '{pattern}' 的文件")
            return

        print(f"📄 找到 {len(md_files)} 个匹配文件")
        print(f"📅 将更新最后更新日期为: {self.today}")
        if dry_run:
            print("🔍 模拟运行模式，不会实际修改文件")

        for i, md_file in enumerate(md_files):
            if self.verbose:
                print(f"  [{i+1}/{len(md_files)}] 处理: {md_file.relative_to(root_path)}")
            else:
                if (i + 1) % 10 == 0:
                    print(f"  处理进度: {i+1}/{len(md_files)}")

            self.update_document_metadata(md_file, update_last_updated, update_version, dry_run)

        print(f"\n📊 批量更新完成:")
        print(f"  ✅ 更新: {self.updated_count} 个文件")
        print(f"  ⏭️  跳过: {self.skipped_count} 个文件（无需更新）")
        print(f"  ❌ 失败: {self.failed_count} 个文件")

    def run_quality_check(self, file_path, check_type="format"):
        """运行质量检查"""
        try:
            if check_type == "format":
                cmd = ["python3", "scripts/validate_document_format.py", "--file", str(file_path)]
            elif check_type == "links":
                cmd = [
                    "python3",
                    "scripts/check_document_links.py",
                    "--directory",
                    str(file_path.parent),
                ]
            elif check_type == "completeness":
                cmd = [
                    "python3",
                    "scripts/check_document_completeness.py",
                    "--file",
                    str(file_path),
                ]
            else:
                return False

            import subprocess

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

            if result.returncode == 0:
                if self.verbose:
                    print(f"    ✅ {check_type}检查通过")
                return True
            else:
                if self.verbose:
                    print(f"    ⚠️  {check_type}检查发现问题")
                    for line in result.stdout.split("\n")[-5:]:
                        if line.strip():
                            print(f"      {line}")
                return False

        except Exception as e:
            print(f"    ❌ 质量检查失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="批量更新文档元数据")
    parser.add_argument("--pattern", "-p", default="*.md", help="文件匹配模式 (默认: *.md)")
    parser.add_argument("--directory", "-d", default="docs/", help="根目录 (默认: docs/)")
    parser.add_argument(
        "--update-metadata", "-m", action="store_true", help="更新元数据（最后更新日期）"
    )
    parser.add_argument(
        "--update-version", "-v", action="store_true", help="更新版本信息（开发中）"
    )
    parser.add_argument("--run-checks", "-c", action="store_true", help="更新后运行质量检查")
    parser.add_argument("--dry-run", "-n", action="store_true", help="模拟运行，不实际修改文件")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 默认至少更新最后更新日期
    if not args.update_metadata and not args.update_version:
        args.update_metadata = True

    updater = BatchDocumentUpdater(verbose=args.verbose)

    print(f"🚀 开始批量文档更新")
    print(f"📁 目录: {args.directory}")
    print(f"🔍 模式: {args.pattern}")

    updater.update_documents_by_pattern(
        pattern=args.pattern,
        root_dir=args.directory,
        update_last_updated=args.update_metadata,
        update_version=args.update_version,
        dry_run=args.dry_run,
    )

    # 运行质量检查
    if args.run_checks and not args.dry_run:
        print(f"\n🔍 运行质量检查...")
        # 这里可以添加质量检查逻辑，但为了简单起见，只记录
        print("  质量检查功能需要单独运行")

    if args.dry_run:
        print(f"\n💡 模拟运行完成，实际更新 {updater.updated_count} 个文件")
        print("  使用 --dry-run false 或移除 -n 参数执行实际更新")
    else:
        print(f"\n✅ 批量更新完成")
        if updater.failed_count > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
