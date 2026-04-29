#!/usr/bin/env python3
"""
文档快照创建器
创建文档版本快照，用于归档和版本管理
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


class DocumentSnapshotCreator:
    """文档快照创建器"""

    def __init__(self, docs_dir="docs/", verbose=False):
        self.docs_dir = Path(docs_dir)
        self.archive_dir = self.docs_dir / "archive"
        self.verbose = verbose

    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件内容的MD5哈希值"""
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            if self.verbose:
                print(f"    计算哈希失败 {file_path}: {e}")
            return ""

    def collect_document_stats(self, root_path: Path) -> dict:
        """收集文档统计信息"""
        stats = {"total_files": 0, "total_size": 0, "file_types": {}, "categories": {}, "files": []}

        # 查找所有Markdown文件
        md_files = list(root_path.rglob("*.md"))

        for md_file in md_files:
            try:
                rel_path = md_file.relative_to(root_path)
                stats["total_files"] += 1

                # 文件大小
                file_size = md_file.stat().st_size
                stats["total_size"] += file_size

                # 文件类型统计（按扩展名）
                file_ext = md_file.suffix.lower()
                stats["file_types"][file_ext] = stats["file_types"].get(file_ext, 0) + 1

                # 分类统计（按目录）
                category = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
                stats["categories"][category] = stats["categories"].get(category, 0) + 1

                # 文件详细信息
                file_info = {
                    "path": str(rel_path),
                    "size": file_size,
                    "modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(),
                    "hash": self.calculate_file_hash(md_file),
                }
                stats["files"].append(file_info)

            except Exception as e:
                if self.verbose:
                    print(f"    处理文件失败 {md_file}: {e}")

        return stats

    def create_snapshot(
        self,
        version: str,
        output_dir: str | None = None,
        include_patterns: list[str] = None,
        exclude_patterns: list[str] = None,
    ) -> dict:
        """创建文档快照"""
        if output_dir is None:
            output_dir = self.archive_dir / f"v{version}"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"📸 创建文档快照 v{version}")
        print(f"📁 输出目录: {output_path}")

        # 收集当前文档统计
        print("📊 收集文档统计信息...")
        stats = self.collect_document_stats(self.docs_dir)

        print(f"📄 总文档数: {stats['total_files']}")
        print(f"💾 总大小: {stats['total_size']:,} 字节")

        if self.verbose:
            print("📁 分类分布:")
            for category, count in sorted(stats["categories"].items()):
                print(f"  {category}/: {count} 个文件")

        # 创建快照元数据
        metadata = {
            "snapshot_version": version,
            "created_at": datetime.now().isoformat(),
            "source_directory": str(self.docs_dir),
            "document_count": stats["total_files"],
            "total_size": stats["total_size"],
            "file_stats": {"by_category": stats["categories"], "by_type": stats["file_types"]},
            "included_patterns": include_patterns or ["*.md"],
            "excluded_patterns": exclude_patterns or [],
        }

        # 复制文档到快照目录
        print("📋 复制文档文件...")
        copied_files = []
        skipped_files = []

        for file_info in stats["files"]:
            source_path = self.docs_dir / file_info["path"]
            target_path = output_path / file_info["path"]

            # 创建目标目录
            target_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # 检查是否需要排除
                should_skip = False
                if exclude_patterns:
                    for pattern in exclude_patterns:
                        if Path(file_info["path"]).match(pattern):
                            should_skip = True
                            break

                if should_skip:
                    skipped_files.append(str(file_info["path"]))
                    continue

                # 复制文件
                shutil.copy2(source_path, target_path)
                copied_files.append(str(file_info["path"]))

                if self.verbose and len(copied_files) % 10 == 0:
                    print(f"    已复制: {len(copied_files)}/{stats['total_files']}")

            except Exception as e:
                print(f"    ❌ 复制失败 {file_info['path']}: {e}")
                skipped_files.append(str(file_info["path"]))

        # 保存元数据
        metadata_path = output_path / "snapshot_metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"✅ 快照元数据已保存: {metadata_path}")
        except Exception as e:
            print(f"❌ 保存元数据失败: {e}")

        # 保存文件列表
        file_list_path = output_path / "file_list.txt"
        try:
            with open(file_list_path, "w", encoding="utf-8") as f:
                for file_path in copied_files:
                    f.write(f"{file_path}\n")
            print(f"✅ 文件列表已保存: {file_list_path}")
        except Exception as e:
            print(f"❌ 保存文件列表失败: {e}")

        # 生成报告
        result = {
            "success": True,
            "snapshot_version": version,
            "output_directory": str(output_path),
            "document_count": stats["total_files"],
            "copied_files": len(copied_files),
            "skipped_files": len(skipped_files),
            "total_size": stats["total_size"],
            "metadata_file": str(metadata_path.relative_to(output_path)),
            "created_at": datetime.now().isoformat(),
        }

        print("\n📊 快照创建完成:")
        print(f"  ✅ 复制文件: {len(copied_files)}/{stats['total_files']}")
        print(f"  ⏭️  跳过文件: {len(skipped_files)}")
        print(f"  💾 快照大小: {stats['total_size']:,} 字节")
        print(f"  📁 快照位置: {output_path}")

        return result

    def list_snapshots(self) -> list[dict]:
        """列出所有快照"""
        snapshots = []

        if not self.archive_dir.exists():
            return snapshots

        for snapshot_dir in self.archive_dir.iterdir():
            if snapshot_dir.is_dir() and snapshot_dir.name.startswith("v"):
                metadata_path = snapshot_dir / "snapshot_metadata.json"

                if metadata_path.exists():
                    try:
                        with open(metadata_path, encoding="utf-8") as f:
                            metadata = json.load(f)

                        snapshots.append(
                            {
                                "version": snapshot_dir.name[1:],  # 移除'v'前缀
                                "path": str(snapshot_dir),
                                "created_at": metadata.get("created_at", "未知"),
                                "document_count": metadata.get("document_count", 0),
                                "total_size": metadata.get("total_size", 0),
                            }
                        )
                    except Exception as e:
                        if self.verbose:
                            print(f"    读取快照元数据失败 {snapshot_dir}: {e}")
                else:
                    # 没有元数据文件的快照目录
                    snapshots.append(
                        {
                            "version": snapshot_dir.name[1:],
                            "path": str(snapshot_dir),
                            "created_at": "未知",
                            "document_count": 0,
                            "total_size": 0,
                            "no_metadata": True,
                        }
                    )

        return sorted(snapshots, key=lambda x: x["version"], reverse=True)

    def restore_snapshot(
        self,
        version: str,
        snapshot_dir: str | None = None,
        target_dir: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """从快照恢复文档"""
        if snapshot_dir is None:
            snapshot_dir = self.archive_dir / f"v{version}"

        snapshot_path = Path(snapshot_dir)
        if not snapshot_path.exists():
            return {"success": False, "error": f"快照目录不存在: {snapshot_path}"}

        if target_dir is None:
            target_dir = self.docs_dir / f"restored_v{version}"

        target_path = Path(target_dir)

        print(f"🔄 从快照恢复 v{version}")
        print(f"📁 快照目录: {snapshot_path}")
        print(f"🎯 目标目录: {target_path}")

        # 检查快照元数据
        metadata_path = snapshot_path / "snapshot_metadata.json"
        if not metadata_path.exists():
            print("⚠️  快照元数据不存在，将直接复制文件")

        # 查找快照中的所有Markdown文件
        md_files = list(snapshot_path.rglob("*.md"))
        if not md_files:
            print("📭 快照中没有找到Markdown文件")
            md_files = []

        # 恢复文件
        restored_files = []
        failed_files = []

        for md_file in md_files:
            rel_path = md_file.relative_to(snapshot_path)
            target_file = target_path / rel_path

            try:
                # 创建目标目录
                target_file.parent.mkdir(parents=True, exist_ok=True)

                if not dry_run:
                    shutil.copy2(md_file, target_file)

                restored_files.append(str(rel_path))

                if self.verbose and len(restored_files) % 10 == 0:
                    print(f"    已恢复: {len(restored_files)}/{len(md_files)}")

            except Exception as e:
                print(f"    ❌ 恢复失败 {rel_path}: {e}")
                failed_files.append(str(rel_path))

        result = {
            "success": len(failed_files) == 0,
            "version": version,
            "snapshot_directory": str(snapshot_path),
            "target_directory": str(target_path),
            "total_files": len(md_files),
            "restored_files": len(restored_files),
            "failed_files": len(failed_files),
            "dry_run": dry_run,
        }

        print("\n📊 快照恢复完成:")
        print(f"  ✅ 恢复文件: {len(restored_files)}/{len(md_files)}")
        print(f"  ❌ 失败文件: {len(failed_files)}")
        print(f"  📁 目标位置: {target_path}")

        if dry_run:
            print("  🔍 模拟运行，未实际复制文件")

        return result


def main():
    parser = argparse.ArgumentParser(description="文档快照创建器")
    parser.add_argument("--directory", "-d", default="docs/", help="文档目录 (默认: docs/)")
    parser.add_argument("--version", "-v", required=True, help="快照版本号 (如: 1.0, 2.1)")
    parser.add_argument("--output", "-o", help="快照输出目录 (默认: docs/archive/v<版本>)")
    parser.add_argument(
        "--include", "-i", nargs="*", default=["*.md"], help="包含的文件模式 (默认: *.md)"
    )
    parser.add_argument("--exclude", "-e", nargs="*", default=[], help="排除的文件模式")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有快照")
    parser.add_argument("--restore", "-r", action="store_true", help="从快照恢复")
    parser.add_argument("--snapshot-dir", help="要恢复的快照目录 (用于--restore)")
    parser.add_argument("--target-dir", help="恢复目标目录 (用于--restore)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="模拟运行，不实际复制文件")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"❌ 目录不存在: {args.directory}")
        sys.exit(1)

    creator = DocumentSnapshotCreator(docs_dir=args.directory, verbose=args.verbose)

    # 列出快照
    if args.list:
        snapshots = creator.list_snapshots()

        if not snapshots:
            print("📭 没有找到任何快照")
            sys.exit(0)

        print(f"📚 找到 {len(snapshots)} 个快照:")
        for snapshot in snapshots:
            print(f"  v{snapshot['version']}:")
            print(f"    路径: {snapshot['path']}")
            print(f"    创建时间: {snapshot['created_at']}")
            print(f"    文档数: {snapshot['document_count']}")
            print(f"    大小: {snapshot['total_size']:,} 字节")
            if snapshot.get("no_metadata"):
                print("    ⚠️  缺少元数据文件")
            print()

        sys.exit(0)

    # 恢复快照
    elif args.restore:
        if not args.version:
            print("❌ 需要指定快照版本 (--version)")
            sys.exit(1)

        result = creator.restore_snapshot(
            version=args.version,
            snapshot_dir=args.snapshot_dir,
            target_dir=args.target_dir,
            dry_run=args.dry_run,
        )

        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)

    # 创建快照
    else:
        result = creator.create_snapshot(
            version=args.version,
            output_dir=args.output,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
        )

        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
