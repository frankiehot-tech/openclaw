#!/usr/bin/env python3
"""
旧文档归档工具
将长时间未更新的文档移动到归档目录，保持主文档目录的活跃性
"""

import argparse
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


class OldDocumentArchiver:
    """旧文档归档器"""

    def __init__(self, docs_dir="docs/", archive_dir="docs/archive/", verbose=False):
        self.docs_dir = Path(docs_dir)
        self.archive_dir = Path(archive_dir)
        self.verbose = verbose
        self.today = datetime.now()

        # 确保归档目录存在
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def find_old_documents(
        self, days_threshold: int = 30, categories: list[str] = None
    ) -> list[dict]:
        """查找超过指定天数的旧文档"""
        print(f"🔍 查找 {days_threshold} 天前修改的文档...")

        cutoff_date = self.today - timedelta(days=days_threshold)
        old_docs = []

        # 构建搜索路径列表
        search_paths = []
        if categories:
            for category in categories:
                category_path = self.docs_dir / category
                if category_path.exists():
                    search_paths.append(category_path)
        else:
            search_paths = [self.docs_dir]

        for search_path in search_paths:
            # 查找所有Markdown文件
            md_files = list(search_path.rglob("*.md"))

            for md_file in md_files:
                try:
                    stats = md_file.stat()
                    modified_time = datetime.fromtimestamp(stats.st_mtime)
                    rel_path = md_file.relative_to(self.docs_dir)

                    # 排除归档目录中的文件
                    if "archive" in rel_path.parts:
                        continue

                    # 检查是否超过阈值
                    if modified_time < cutoff_date:
                        days_old = (self.today - modified_time).days

                        doc_info = {
                            "path": md_file,
                            "rel_path": str(rel_path),
                            "modified_date": modified_time.strftime("%Y-%m-%d"),
                            "days_old": days_old,
                            "size": stats.st_size,
                            "category": rel_path.parts[0] if len(rel_path.parts) > 1 else "root",
                        }

                        old_docs.append(doc_info)

                        if self.verbose:
                            print(f"  📅 找到旧文档: {rel_path} ({days_old} 天前)")

                except Exception as e:
                    print(f"    ❌ 处理文件失败 {md_file}: {e}")

        # 按修改时间排序（最旧的在前）
        old_docs.sort(key=lambda x: x["days_old"], reverse=True)

        print(f"📄 找到 {len(old_docs)} 个超过 {days_threshold} 天的文档")
        return old_docs

    def archive_document(
        self, doc_info: dict, archive_period: str = "quarterly", dry_run: bool = False
    ) -> tuple[bool, str]:
        """归档单个文档"""
        try:
            source_path = doc_info["path"]
            rel_path = doc_info["rel_path"]

            # 确定归档目录结构
            if archive_period == "quarterly":
                # 按季度归档: docs/archive/2026-Q1/
                modified_date = datetime.strptime(doc_info["modified_date"], "%Y-%m-%d")
                quarter = (modified_date.month - 1) // 3 + 1
                archive_subdir = f"{modified_date.year}-Q{quarter}"
            elif archive_period == "monthly":
                # 按月归档: docs/archive/2026-04/
                modified_date = datetime.strptime(doc_info["modified_date"], "%Y-%m-%d")
                archive_subdir = modified_date.strftime("%Y-%m")
            elif archive_period == "yearly":
                # 按年归档: docs/archive/2026/
                modified_date = datetime.strptime(doc_info["modified_date"], "%Y-%m-%d")
                archive_subdir = str(modified_date.year)
            else:
                # 自定义归档目录
                archive_subdir = archive_period

            # 构建目标路径
            archive_path = self.archive_dir / archive_subdir / rel_path
            archive_path.parent.mkdir(parents=True, exist_ok=True)

            # 检查目标文件是否已存在
            if archive_path.exists():
                # 添加时间戳后缀避免冲突
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_path = archive_path.with_stem(f"{archive_path.stem}_{timestamp}")

            if not dry_run:
                # 复制文件到归档目录
                shutil.copy2(source_path, archive_path)

                # 可选：在源位置创建占位符或删除源文件
                # 这里我们选择移动文件（复制后删除）
                source_path.unlink()

                # 在源位置创建符号链接或占位符文件
                placeholder_path = source_path.with_suffix(".md.archived")
                with open(placeholder_path, "w", encoding="utf-8") as f:
                    f.write("# 本文档已归档\n\n")
                    f.write(
                        f"原始文档已移动到归档目录: {archive_path.relative_to(self.docs_dir)}\n"
                    )
                    f.write(f"归档日期: {self.today.strftime('%Y-%m-%d')}\n")
                    f.write(f"归档原因: 超过{doc_info['days_old']}天未更新\n\n")
                    f.write(
                        f"如需访问原始文档，请前往: `{archive_path.relative_to(self.docs_dir)}`\n"
                    )

                action = f"移动 {rel_path} → {archive_path.relative_to(self.docs_dir)}"
            else:
                action = f"[模拟] 将移动 {rel_path} → {archive_path.relative_to(self.docs_dir)}"

            return True, action

        except Exception as e:
            return False, f"归档失败 {doc_info['rel_path']}: {e}"

    def archive_documents(
        self,
        days_threshold: int = 30,
        archive_period: str = "quarterly",
        categories: list[str] = None,
        limit: int = 0,
        dry_run: bool = False,
    ) -> dict:
        """批量归档文档"""
        print(f"🗂️  开始归档文档 (阈值: {days_threshold}天, 周期: {archive_period})")

        # 查找旧文档
        old_docs = self.find_old_documents(days_threshold, categories)

        if not old_docs:
            print("📭 没有找到需要归档的文档")
            return {"total_found": 0, "archived": 0, "failed": 0, "dry_run": dry_run}

        # 限制处理数量
        if limit > 0 and len(old_docs) > limit:
            print(f"📏 限制处理前 {limit} 个文档")
            old_docs = old_docs[:limit]

        # 归档文档
        archived_count = 0
        failed_count = 0
        archive_actions = []

        for i, doc_info in enumerate(old_docs):
            if self.verbose or (i + 1) % 10 == 0:
                print(f"  处理进度: {i + 1}/{len(old_docs)}")

            success, action = self.archive_document(doc_info, archive_period, dry_run)

            if success:
                archived_count += 1
                archive_actions.append(action)

                if self.verbose:
                    print(f"    ✅ {action}")
            else:
                failed_count += 1
                if self.verbose:
                    print(f"    ❌ {action}")

        # 生成报告
        result = {
            "total_found": len(old_docs),
            "archived": archived_count,
            "failed": failed_count,
            "days_threshold": days_threshold,
            "archive_period": archive_period,
            "dry_run": dry_run,
            "archive_date": self.today.strftime("%Y-%m-%d"),
        }

        print("\n📊 归档完成:")
        print(f"  🔍 找到文档: {len(old_docs)}")
        print(f"  ✅ 成功归档: {archived_count}")
        print(f"  ❌ 归档失败: {failed_count}")

        if dry_run:
            print("  🔍 模拟运行，未实际移动文件")

        # 显示归档的文档统计
        if archived_count > 0:
            print("\n📁 归档统计:")
            categories_summary = {}
            total_size = 0

            for doc_info in old_docs[:archived_count]:
                category = doc_info["category"]
                categories_summary[category] = categories_summary.get(category, 0) + 1
                total_size += doc_info["size"]

            for category, count in categories_summary.items():
                print(f"  {category}/: {count} 个文档")

            print(f"  💾 总大小: {total_size:,} 字节")

        return result

    def create_archive_report(self, archive_result: dict, output_file: str | None = None):
        """创建归档报告"""
        print("📝 生成归档报告...")

        report_date = self.today.strftime("%Y-%m-%d")
        report_content = f"""# 文档归档报告

## 📊 归档摘要

| 项目 | 数值 |
|------|------|
| 归档日期 | {report_date} |
| 归档阈值 | {archive_result["days_threshold"]} 天 |
| 归档周期 | {archive_result["archive_period"]} |
| 找到文档 | {archive_result["total_found"]} |
| 成功归档 | {archive_result["archived"]} |
| 归档失败 | {archive_result["failed"]} |
| 运行模式 | {"模拟运行" if archive_result["dry_run"] else "实际执行"} |

## 📁 归档详情

"""

        if archive_result.get("archive_actions"):
            report_content += "### 归档操作记录\n\n"
            for action in archive_result["archive_actions"][:50]:  # 只显示前50个
                report_content += f"- {action}\n"

            if len(archive_result["archive_actions"]) > 50:
                report_content += (
                    f"\n... 还有 {len(archive_result['archive_actions']) - 50} 个操作记录\n"
                )

        report_content += f"""

## 💡 后续建议

1. **更新文档索引**: 运行 `python3 scripts/update_document_index.py` 更新主文档索引
2. **更新归档索引**: 运行 `python3 scripts/update_archive_index.py` 更新归档目录索引
3. **验证归档完整性**: 检查归档目录中的文件可访问性
4. **清理占位符文件**: 可选择性删除 `.archived` 占位符文件

## 🔧 归档配置

- **源目录**: {self.docs_dir}
- **归档目录**: {self.archive_dir}
- **归档策略**: {archive_result["archive_period"]}
- **阈值天数**: {archive_result["days_threshold"]}

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
*使用脚本: archive_old_documents.py*
"""

        # 保存报告
        if output_file is None:
            report_dir = self.archive_dir / "reports"
            report_dir.mkdir(exist_ok=True)
            output_file = report_dir / f"archive_report_{report_date}.md"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_content)

            print(f"✅ 归档报告已保存: {output_file}")
            return str(output_file)
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="旧文档归档工具")
    parser.add_argument("--days", "-d", type=int, default=30, help="归档阈值天数 (默认: 30)")
    parser.add_argument(
        "--period",
        "-p",
        default="quarterly",
        choices=["quarterly", "monthly", "yearly", "custom"],
        help="归档周期 (默认: quarterly)",
    )
    parser.add_argument("--custom-period", "-c", help="自定义归档目录名 (用于--period custom)")
    parser.add_argument("--categories", nargs="*", help="限制归档的文档类别 (如: technical audit)")
    parser.add_argument(
        "--limit", "-l", type=int, default=0, help="限制归档的文档数量 (0表示无限制)"
    )
    parser.add_argument("--report", "-r", action="store_true", help="生成归档报告")
    parser.add_argument("--report-output", help="报告输出文件路径")
    parser.add_argument("--dry-run", "-n", action="store_true", help="模拟运行，不实际移动文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists("docs/"):
        print("❌ 文档目录不存在: docs/")
        sys.exit(1)

    # 确定归档周期
    archive_period = args.period
    if args.period == "custom" and args.custom_period:
        archive_period = args.custom_period
    elif args.period == "custom" and not args.custom_period:
        print("❌ 使用 --period custom 时需要指定 --custom-period")
        sys.exit(1)

    # 创建归档器
    archiver = OldDocumentArchiver(verbose=args.verbose)

    print("🚀 开始文档归档")
    print(f"📁 源目录: {archiver.docs_dir}")
    print(f"🗂️  归档目录: {archiver.archive_dir}")
    print(f"📅 归档阈值: {args.days} 天")
    print(f"📊 归档周期: {archive_period}")

    if args.categories:
        print(f"📋 限制类别: {', '.join(args.categories)}")

    if args.limit > 0:
        print(f"📏 数量限制: {args.limit} 个文档")

    if args.dry_run:
        print("🔍 模拟运行模式，不会实际移动文件")

    # 执行归档
    result = archiver.archive_documents(
        days_threshold=args.days,
        archive_period=archive_period,
        categories=args.categories,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    # 生成报告
    if args.report and not args.dry_run:
        report_file = archiver.create_archive_report(result, args.report_output)
        if report_file:
            print(f"📄 归档报告: {report_file}")

    # 后续建议
    print("\n💡 后续建议:")
    print("  1. 更新主文档索引: python3 scripts/update_document_index.py")
    print("  2. 更新归档索引: python3 scripts/update_archive_index.py")

    if args.dry_run:
        print(f"\n🔍 模拟运行完成，实际将归档 {result['archived']} 个文档")
        print("  移除 --dry-run 参数执行实际归档")
        sys.exit(0)
    else:
        if result["failed"] == 0:
            print("\n✅ 归档完成")
            sys.exit(0)
        else:
            print(f"\n⚠️  归档完成，但有 {result['failed']} 个失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
