#!/usr/bin/env python3
"""
归档索引更新器
更新docs/archive/目录的索引文件，便于查找和浏览归档文档
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


class ArchiveIndexUpdater:
    """归档索引更新器"""

    def __init__(self, archive_dir="docs/archive/", verbose=False):
        self.archive_dir = Path(archive_dir)
        self.verbose = verbose
        self.index_data = {
            "updated_at": datetime.now().isoformat(),
            "total_snapshots": 0,
            "total_files": 0,
            "total_size": 0,
            "snapshots": [],
            "quarterly_archives": [],
            "yearly_summary": {},
        }

    def scan_archive_structure(self):
        """扫描归档目录结构"""
        print(f"📁 扫描归档目录: {self.archive_dir}")

        if not self.archive_dir.exists():
            print(f"📭 归档目录不存在，将创建: {self.archive_dir}")
            self.archive_dir.mkdir(parents=True, exist_ok=True)

        # 扫描快照目录 (v1.0, v2.0 等)
        snapshots = []
        for item in self.archive_dir.iterdir():
            if item.is_dir():
                if item.name.startswith("v") and item.name[1:].replace(".", "").isdigit():
                    snapshot_info = self._analyze_snapshot(item)
                    if snapshot_info:
                        snapshots.append(snapshot_info)

        # 扫描按时间归档的目录 (2026-Q1, 2026-04 等)
        quarterly_archives = []
        for item in self.archive_dir.iterdir():
            if item.is_dir() and not item.name.startswith("v"):
                # 检查是否为时间格式目录
                if self._is_time_based_directory(item.name):
                    archive_info = self._analyze_time_archive(item)
                    if archive_info:
                        quarterly_archives.append(archive_info)

        # 按版本排序快照
        snapshots.sort(key=lambda x: self._parse_version(x["version"]), reverse=True)

        # 按时间排序归档
        quarterly_archives.sort(key=lambda x: x["period"], reverse=True)

        self.index_data["snapshots"] = snapshots
        self.index_data["quarterly_archives"] = quarterly_archives
        self.index_data["total_snapshots"] = len(snapshots)

        # 计算总统计
        total_files = 0
        total_size = 0
        for snapshot in snapshots:
            total_files += snapshot.get("file_count", 0)
            total_size += snapshot.get("total_size", 0)

        for archive in quarterly_archives:
            total_files += archive.get("file_count", 0)
            total_size += archive.get("total_size", 0)

        self.index_data["total_files"] = total_files
        self.index_data["total_size"] = total_size

        # 生成年度摘要
        self._generate_yearly_summary()

        print("📊 归档统计:")
        print(f"  📁 快照数量: {len(snapshots)}")
        print(f"  📅 时间归档: {len(quarterly_archives)}")
        print(f"  📄 总文件数: {total_files}")
        print(f"  💾 总大小: {total_size:,} 字节")

        return total_files

    def _parse_version(self, version_str: str) -> tuple:
        """解析版本号为可排序的元组"""
        parts = version_str.split(".")
        # 将每部分转换为整数，支持最多4部分
        return tuple(int(part) if part.isdigit() else 0 for part in parts[:4])

    def _is_time_based_directory(self, dir_name: str) -> bool:
        """检查是否为基于时间的目录名"""
        patterns = [
            r"^\d{4}-Q[1-4]$",  # 2026-Q1
            r"^\d{4}-\d{2}$",  # 2026-04
            r"^\d{4}$",  # 2026
        ]

        import re

        return any(re.match(pattern, dir_name) for pattern in patterns)

    def _analyze_snapshot(self, snapshot_dir: Path) -> dict | None:
        """分析快照目录"""
        try:
            # 检查是否有元数据文件
            metadata_file = snapshot_dir / "snapshot_metadata.json"
            file_list_file = snapshot_dir / "file_list.txt"

            snapshot_info = {
                "name": snapshot_dir.name,
                "version": snapshot_dir.name[1:],  # 移除'v'前缀
                "path": str(snapshot_dir.relative_to(self.archive_dir)),
                "has_metadata": metadata_file.exists(),
                "has_file_list": file_list_file.exists(),
                "file_count": 0,
                "total_size": 0,
                "created_at": "未知",
            }

            # 如果有元数据文件，读取详细信息
            if metadata_file.exists():
                try:
                    with open(metadata_file, encoding="utf-8") as f:
                        metadata = json.load(f)

                    snapshot_info.update(
                        {
                            "created_at": metadata.get("created_at", "未知"),
                            "file_count": metadata.get("document_count", 0),
                            "total_size": metadata.get("total_size", 0),
                            "source_directory": metadata.get("source_directory", "未知"),
                            "included_patterns": metadata.get("included_patterns", []),
                        }
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"    读取元数据失败 {metadata_file}: {e}")

            # 如果没有元数据，手动统计
            if snapshot_info["file_count"] == 0:
                md_files = list(snapshot_dir.rglob("*.md"))
                snapshot_info["file_count"] = len(md_files)

                total_size = 0
                for md_file in md_files:
                    total_size += md_file.stat().st_size
                snapshot_info["total_size"] = total_size

            # 获取目录修改时间作为创建时间
            if snapshot_info["created_at"] == "未知":
                stats = snapshot_dir.stat()
                snapshot_info["created_at"] = datetime.fromtimestamp(stats.st_mtime).isoformat()

            if self.verbose:
                print(
                    f"  📸 快照 v{snapshot_info['version']}: {snapshot_info['file_count']} 个文件, {snapshot_info['total_size']:,} 字节"
                )

            return snapshot_info

        except Exception as e:
            if self.verbose:
                print(f"    分析快照失败 {snapshot_dir}: {e}")
            return None

    def _analyze_time_archive(self, archive_dir: Path) -> dict | None:
        """分析时间归档目录"""
        try:
            # 统计目录中的Markdown文件
            md_files = list(archive_dir.rglob("*.md"))
            file_count = len(md_files)

            total_size = 0
            for md_file in md_files:
                total_size += md_file.stat().st_size

            # 分析目录结构
            categories = {}
            for md_file in md_files:
                rel_path = md_file.relative_to(archive_dir)
                if len(rel_path.parts) > 1:
                    category = rel_path.parts[0]
                    categories[category] = categories.get(category, 0) + 1

            # 获取目录信息
            stats = archive_dir.stat()
            modified_at = datetime.fromtimestamp(stats.st_mtime).isoformat()

            archive_info = {
                "name": archive_dir.name,
                "path": str(archive_dir.relative_to(self.archive_dir)),
                "period": archive_dir.name,
                "file_count": file_count,
                "total_size": total_size,
                "categories": categories,
                "modified_at": modified_at,
                "directory_count": len(list(archive_dir.rglob("*"))) - file_count,
            }

            if self.verbose:
                print(f"  📅 归档 {archive_dir.name}: {file_count} 个文件, {total_size:,} 字节")

            return archive_info

        except Exception as e:
            if self.verbose:
                print(f"    分析归档目录失败 {archive_dir}: {e}")
            return None

    def _generate_yearly_summary(self):
        """生成年度摘要"""
        yearly_data = {}

        # 统计快照
        for snapshot in self.index_data["snapshots"]:
            if "created_at" in snapshot and snapshot["created_at"] != "未知":
                try:
                    year = snapshot["created_at"][:4]  # 提取年份
                    if year not in yearly_data:
                        yearly_data[year] = {"snapshots": 0, "files": 0, "size": 0}

                    yearly_data[year]["snapshots"] += 1
                    yearly_data[year]["files"] += snapshot.get("file_count", 0)
                    yearly_data[year]["size"] += snapshot.get("total_size", 0)
                except Exception:
                    pass

        # 统计时间归档
        for archive in self.index_data["quarterly_archives"]:
            period = archive["period"]
            if "-" in period:
                year = period.split("-")[0]
                if year.isdigit():
                    if year not in yearly_data:
                        yearly_data[year] = {"snapshots": 0, "files": 0, "size": 0}

                    yearly_data[year]["files"] += archive.get("file_count", 0)
                    yearly_data[year]["size"] += archive.get("total_size", 0)

        self.index_data["yearly_summary"] = yearly_data

    def generate_readme_index(self):
        """生成归档README.md索引"""
        readme_path = self.archive_dir / "README.md"

        try:
            # 创建README内容
            content = f"""# 文档归档目录

> 最后更新: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 归档统计

| 项目 | 数量 |
|------|------|
| 版本快照 | {self.index_data["total_snapshots"]} |
| 时间归档 | {len(self.index_data["quarterly_archives"])} |
| 总文件数 | {self.index_data["total_files"]} |
| 总大小 | {self._format_size(self.index_data["total_size"])} |

## 📸 版本快照

"""

            if self.index_data["snapshots"]:
                content += "| 版本 | 文档数 | 大小 | 创建时间 | 元数据 |\n"
                content += "|------|--------|------|----------|--------|\n"

                for snapshot in self.index_data["snapshots"]:
                    version = snapshot["version"]
                    file_count = snapshot.get("file_count", 0)
                    size = self._format_size(snapshot.get("total_size", 0))
                    created_at = snapshot.get("created_at", "未知")[:10]  # 只取日期部分
                    has_metadata = "✅" if snapshot.get("has_metadata") else "❌"

                    content += f"| [{version}]({snapshot['path']}/) | {file_count} | {size} | {created_at} | {has_metadata} |\n"
            else:
                content += "暂无版本快照。\n\n"

            content += "\n## 📅 时间归档\n\n"

            if self.index_data["quarterly_archives"]:
                content += "| 期间 | 文档数 | 大小 | 最后更新 | 分类数 |\n"
                content += "|------|--------|------|----------|--------|\n"

                for archive in self.index_data["quarterly_archives"]:
                    period = archive["period"]
                    file_count = archive.get("file_count", 0)
                    size = self._format_size(archive.get("total_size", 0))
                    modified_at = archive.get("modified_at", "未知")[:10]
                    category_count = len(archive.get("categories", {}))

                    content += f"| [{period}]({archive['path']}/) | {file_count} | {size} | {modified_at} | {category_count} |\n"
            else:
                content += "暂无时间归档。\n\n"

            content += "\n## 📈 年度摘要\n\n"

            if self.index_data["yearly_summary"]:
                content += "| 年份 | 快照数 | 文档数 | 总大小 |\n"
                content += "|------|--------|--------|--------|\n"

                for year, data in sorted(self.index_data["yearly_summary"].items(), reverse=True):
                    snapshots = data.get("snapshots", 0)
                    files = data.get("files", 0)
                    size = self._format_size(data.get("size", 0))

                    content += f"| {year} | {snapshots} | {files} | {size} |\n"
            else:
                content += "暂无年度摘要数据。\n\n"

            content += """

## 🔧 使用方法

### 创建新快照
```bash
python3 scripts/create_document_snapshot.py --version 1.0
```

### 恢复快照
```bash
python3 scripts/create_document_snapshot.py --restore --version 1.0
```

### 归档旧文档
```bash
# 将30天前的文档移动到归档目录
python3 scripts/archive_old_documents.py --days 30
```

### 更新本索引
```bash
python3 scripts/update_archive_index.py
```

## 📝 归档策略

1. **版本快照**: 重要版本发布时创建完整快照
2. **季度归档**: 每季度归档过时文档
3. **年度汇总**: 每年生成归档统计报告

---

*本索引自动生成，最后更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            # 写入文件
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"✅ 已生成归档索引: {readme_path}")
            return True

        except Exception as e:
            print(f"❌ 生成归档索引失败: {e}")
            return False

    def _format_size(self, bytes_size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    def generate_json_index(self, output_file: str | None = None):
        """生成JSON格式的索引文件"""
        if output_file is None:
            output_file = self.archive_dir / "archive_index.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.index_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 已生成JSON索引: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 生成JSON索引失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="更新归档索引")
    parser.add_argument(
        "--directory", "-d", default="docs/archive/", help="归档目录 (默认: docs/archive/)"
    )
    parser.add_argument("--update-readme", "-r", action="store_true", help="生成归档README.md索引")
    parser.add_argument("--generate-json", "-j", action="store_true", help="生成JSON格式索引文件")
    parser.add_argument("--json-output", "-o", help="JSON索引输出文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 检查目录是否存在，不存在则创建
    if not os.path.exists(args.directory):
        print(f"📭 归档目录不存在，将创建: {args.directory}")
        os.makedirs(args.directory, exist_ok=True)

    updater = ArchiveIndexUpdater(archive_dir=args.directory, verbose=args.verbose)

    # 扫描归档结构
    total_files = updater.scan_archive_structure()

    if total_files == 0:
        print("📭 归档目录为空，没有找到文档")
        print("💡 建议: 使用 create_document_snapshot.py 创建第一个快照")

    success = True

    # 更新README.md索引
    if args.update_readme and not updater.generate_readme_index():
        success = False

    # 生成JSON索引
    if args.generate_json:
        output_file = args.json_output if args.json_output else None
        if not updater.generate_json_index(output_file):
            success = False

    # 如果没有指定任何操作，默认更新README
    if not args.update_readme and not args.generate_json:
        print("\n💡 未指定操作，默认更新README.md索引")
        if updater.generate_readme_index():
            print("✅ 归档索引更新完成")
        else:
            success = False

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
