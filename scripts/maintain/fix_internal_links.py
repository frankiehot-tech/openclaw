#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
内部链接修复工具
修复文档迁移后的内部引用链接，将旧路径更新为新路径
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path


class InternalLinkFixer:
    """内部链接修复器"""

    def __init__(self, docs_dir="docs/", verbose=False):
        self.docs_dir = Path(docs_dir)
        self.verbose = verbose

        # 旧路径到新路径的映射（基于文档迁移的规则）
        self.path_mappings = self._build_path_mappings()

    def _build_path_mappings(self) -> dict[str, str]:
        """构建路径映射表"""
        mappings = {
            # 根目录文件映射到对应分类
            "COGNITIVE_DNA.md": "architecture/cognitive_dna.md",
            "AGENTS.md": "architecture/agents.md",
            "system_architecture.md": "architecture/system_architecture.md",
            # 审计文档映射
            r"audit_executive_summary_\d{8}\.md": "audit/2026-04/audit_executive_summary_20260419.md",
            r"deep_audit_report_\d{8}\.md": "audit/2026-04/deep_audit_report_20260419.md",
            # 技术文档映射
            r"athena_.*\.md": "technical/specifications/",
            r"deployment_.*\.md": "technical/deployment/",
            r"operations_.*\.md": "technical/operations/",
            # 用户文档映射
            "USER.md": "user/contributing.md",  # 注意：USER.md内容已合并到contributing.md
            "TOOLS.md": "user/tools-reference.md",
            "IDENTITY.md": "user/claude-code-config.md",
            "HEARTBEAT.md": "user/getting-started.md",
            # 通用模式
            r"(\d{4}-\d{2}-\d{2})_.*\.md": r"audit/\1/",  # 日期前缀的审计文档
            r"(\d{4}\d{2}\d{2})_.*\.md": r"audit/\1/",  # 日期数字格式
        }

        return mappings

    def find_markdown_links(self, content: str) -> list[tuple[str, str, int, int]]:
        """查找Markdown格式的链接"""
        # Markdown链接模式: [文本](链接 "可选标题")
        link_pattern = r'\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)'

        links = []
        for match in re.finditer(link_pattern, content):
            link_text = match.group(1)
            link_url = match.group(2)
            start_pos = match.start()
            end_pos = match.end()

            # 跳过外部链接（http/https开头）
            if link_url.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # 跳过锚点链接（只包含#）
            if link_url.startswith("#") and len(link_url) > 1:
                continue

            links.append((link_text, link_url, start_pos, end_pos))

        return links

    def should_fix_link(self, link_url: str) -> bool:
        """判断链接是否需要修复"""
        # 检查是否为相对路径的.md文件链接
        if not link_url.endswith(".md"):
            return False

        # 检查是否为外部链接
        if link_url.startswith(("http://", "https://", "//")):
            return False

        # 检查链接文件是否存在
        link_path = self.docs_dir / link_url
        return not link_path.exists()

    def find_best_mapping(self, old_path: str) -> str:
        """为旧路径寻找最佳映射"""
        # 首先尝试精确匹配
        if old_path in self.path_mappings:
            return self.path_mappings[old_path]

        # 尝试正则匹配
        for pattern, replacement in self.path_mappings.items():
            if pattern.startswith("r"):  # 正则表达式模式
                pattern = pattern[1:]  # 移除开头的'r'
                try:
                    if re.match(pattern, old_path):
                        if replacement.endswith("/"):
                            # 保留文件名，只替换目录部分
                            filename = Path(old_path).name
                            return replacement + filename
                        else:
                            return replacement
                except re.error:
                    continue

        # 没有找到映射，返回原路径（将尝试在docs目录中查找）
        return old_path

    def search_file_in_docs(self, filename: str) -> str:
        """在docs目录中搜索文件"""
        # 递归搜索所有.md文件
        for md_file in self.docs_dir.rglob("*.md"):
            if md_file.name == filename:
                # 返回相对于docs目录的路径
                return str(md_file.relative_to(self.docs_dir))

        # 未找到文件
        return ""

    def fix_links_in_file(self, file_path: Path, dry_run: bool = False) -> dict:
        """修复单个文件中的链接"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            links = self.find_markdown_links(content)

            if not links:
                return {
                    "file": str(file_path.relative_to(self.docs_dir)),
                    "links_found": 0,
                    "links_fixed": 0,
                    "changes": [],
                }

            # 从文件末尾开始修复，避免位置偏移问题
            links.sort(key=lambda x: x[3], reverse=True)  # 按结束位置降序排序

            fixed_links = []
            changes = []

            for link_text, link_url, start_pos, end_pos in links:
                if not self.should_fix_link(link_url):
                    continue

                # 寻找最佳映射
                new_url = self.find_best_mapping(link_url)

                # 如果映射没有改变，但文件不存在，尝试在docs目录中搜索
                if new_url == link_url:
                    # 文件不存在，尝试搜索
                    found_path = self.search_file_in_docs(Path(link_url).name)
                    if found_path:
                        new_url = found_path

                if new_url != link_url:
                    # 替换链接
                    before = content[:start_pos]
                    after = content[end_pos:]
                    new_link = f"[{link_text}]({new_url})"
                    content = before + new_link + after

                    fixed_links.append((link_url, new_url))
                    changes.append(f"{link_url} → {new_url}")

                    if self.verbose:
                        print(f"    🔗 修复链接: {link_url} → {new_url}")

            # 如果文件在docs目录外，还需要修复指向docs目录的链接
            if str(file_path).startswith(str(self.docs_dir)):
                # 已经是docs目录内的文件
                pass

            if fixed_links and not dry_run:
                # 写入修复后的内容
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            return {
                "file": str(file_path.relative_to(self.docs_dir)),
                "links_found": len(links),
                "links_fixed": len(fixed_links),
                "changes": changes,
                "dry_run": dry_run,
            }

        except Exception as e:
            return {
                "file": str(file_path.relative_to(self.docs_dir)),
                "error": str(e),
                "links_found": 0,
                "links_fixed": 0,
            }

    def fix_links_in_directory(
        self, directory: str = None, pattern: str = "*.md", dry_run: bool = False
    ) -> dict:
        """修复目录中所有文件的链接"""
        if directory is None:
            directory = self.docs_dir
        else:
            directory = Path(directory)

        print("🔗 开始修复内部链接")
        print(f"📁 目录: {directory}")
        print(f"🔍 模式: {pattern}")

        if dry_run:
            print("🔍 模拟运行模式，不会实际修改文件")

        # 查找所有Markdown文件
        md_files = list(directory.rglob(pattern))

        if not md_files:
            print(f"📭 未找到匹配模式 '{pattern}' 的文件")
            return {"total_files": 0, "fixed_files": 0}

        print(f"📄 找到 {len(md_files)} 个Markdown文件")

        results = []
        total_links_found = 0
        total_links_fixed = 0

        for i, md_file in enumerate(md_files):
            if self.verbose or (i + 1) % 10 == 0:
                print(f"  处理进度: {i + 1}/{len(md_files)}")

            result = self.fix_links_in_file(md_file, dry_run)
            results.append(result)

            total_links_found += result.get("links_found", 0)
            total_links_fixed += result.get("links_fixed", 0)

        # 生成报告
        files_with_fixes = [r for r in results if r.get("links_fixed", 0) > 0]

        print("\n📊 链接修复完成:")
        print(f"  📄 处理文件: {len(md_files)}")
        print(f"  🔗 找到链接: {total_links_found}")
        print(f"  🔧 修复链接: {total_links_fixed}")
        print(f"  📝 修复文件: {len(files_with_fixes)}")

        if files_with_fixes and self.verbose:
            print("\n📋 修复详情:")
            for result in files_with_fixes[:10]:  # 只显示前10个
                print(f"  {result['file']}: {result['links_fixed']} 个链接")
                for change in result.get("changes", [])[:3]:  # 只显示前3个更改
                    print(f"    - {change}")
                if len(result.get("changes", [])) > 3:
                    print(f"    ... 还有 {len(result.get('changes', [])) - 3} 个更改")

        if dry_run:
            print(f"\n🔍 模拟运行完成，实际将修复 {total_links_fixed} 个链接")

        return {
            "total_files": len(md_files),
            "files_with_fixes": len(files_with_fixes),
            "total_links_found": total_links_found,
            "total_links_fixed": total_links_fixed,
            "dry_run": dry_run,
            "results": results[:20],  # 只保留前20个结果避免过大
        }

    def generate_mapping_report(self, output_file: str = None):
        """生成路径映射报告"""
        print("📋 生成路径映射报告...")

        report_content = f"""# 文档路径映射报告

> 生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 映射统计

- **总映射规则**: {len(self.path_mappings)}
- **精确匹配**: {sum(1 for k in self.path_mappings if not k.startswith("r"))}
- **正则匹配**: {sum(1 for k in self.path_mappings if k.startswith("r"))}

## 🔧 映射规则

### 精确匹配
| 旧路径 | 新路径 |
|--------|--------|
"""

        # 精确匹配
        exact_mappings = {k: v for k, v in self.path_mappings.items() if not k.startswith("r")}
        for old_path, new_path in exact_mappings.items():
            report_content += f"| `{old_path}` | `{new_path}` |\n"

        report_content += "\n### 正则匹配\n| 模式 | 替换 |\n|------|------|\n"

        # 正则匹配
        regex_mappings = {k: v for k, v in self.path_mappings.items() if k.startswith("r")}
        for pattern, replacement in regex_mappings.items():
            report_content += f"| `{pattern}` | `{replacement}` |\n"

        report_content += """

## 💡 使用说明

### 修复单个文件
```bash
python3 scripts/fix_internal_links.py --file docs/user/guide.md
```

### 修复整个目录
```bash
python3 scripts/fix_internal_links.py --directory docs/
```

### 模拟运行（不实际修改）
```bash
python3 scripts/fix_internal_links.py --directory docs/ --dry-run
```

### 自定义映射文件
```bash
# 创建自定义映射文件
python3 scripts/fix_internal_links.py --generate-mapping custom_mappings.json
```

## 📝 注意事项

1. **备份文件**: 建议在运行前备份重要文档
2. **手动验证**: 修复后请验证关键链接的正确性
3. **外部链接**: 不会修改http/https等外部链接
4. **锚点链接**: 不会修改页面内锚点链接 (#anchor)

---

*本报告由 fix_internal_links.py 生成*
"""

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report_content)
                print(f"✅ 映射报告已保存: {output_file}")
            except Exception as e:
                print(f"❌ 保存报告失败: {e}")
        else:
            print(report_content)


def main():
    parser = argparse.ArgumentParser(description="修复文档内部链接")
    parser.add_argument("--directory", "-d", help="要修复的目录 (默认: docs/)")
    parser.add_argument("--file", "-f", help="要修复的单个文件")
    parser.add_argument("--pattern", "-p", default="*.md", help="文件匹配模式 (默认: *.md)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="模拟运行，不实际修改文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    parser.add_argument("--generate-report", "-r", action="store_true", help="生成路径映射报告")
    parser.add_argument("--report-output", help="报告输出文件路径")

    args = parser.parse_args()

    # 默认目录为docs/
    directory = args.directory if args.directory else "docs/"

    # 检查目录是否存在
    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        sys.exit(1)

    fixer = InternalLinkFixer(docs_dir=directory, verbose=args.verbose)

    # 生成报告
    if args.generate_report:
        fixer.generate_mapping_report(args.report_output)
        sys.exit(0)

    # 修复单个文件
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            sys.exit(1)

        result = fixer.fix_links_in_file(file_path, args.dry_run)

        if "error" in result:
            print(f"❌ 修复失败: {result['error']}")
            sys.exit(1)
        else:
            print("\n📊 文件修复结果:")
            print(f"  文件: {result['file']}")
            print(f"  找到链接: {result['links_found']}")
            print(f"  修复链接: {result['links_fixed']}")

            if result["changes"]:
                print("  更改:")
                for change in result["changes"]:
                    print(f"    - {change}")

            if args.dry_run:
                print("\n🔍 模拟运行完成")

            sys.exit(0)

    # 修复整个目录
    else:
        result = fixer.fix_links_in_directory(directory, args.pattern, args.dry_run)

        if args.dry_run:
            print(f"\n🔍 模拟运行完成，实际将修复 {result['total_links_fixed']} 个链接")
            print("  移除 --dry-run 参数执行实际修复")
        else:
            if result["total_links_fixed"] > 0:
                print("\n✅ 链接修复完成")
            else:
                print("\n📭 未找到需要修复的链接")

        sys.exit(0)


if __name__ == "__main__":
    main()
