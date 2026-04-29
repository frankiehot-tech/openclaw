#!/usr/bin/env python3
"""
文档格式验证工具
验证Markdown文档是否符合OpenClaw格式规范
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


class DocumentValidator:
    """文档格式验证器"""

    def __init__(self, strict=False):
        self.strict = strict
        self.issues = []

    def validate_file(self, file_path):
        """验证单个文件"""
        file_path = Path(file_path)
        relative_path = (
            file_path.relative_to(Path.cwd()) if file_path.is_relative_to(Path.cwd()) else file_path
        )

        print(f"📄 验证: {relative_path}")

        # 读取文件内容
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.add_issue(file_path, "无法读取文件", str(e))
            return False

        # 执行所有验证规则
        checks = [
            self.check_filename,
            self.check_frontmatter,
            self.check_structure,
            self.check_heading_levels,
            self.check_code_blocks,
            self.check_tables,
            self.check_links,
            self.check_last_updated,
        ]

        passed = True
        for check in checks:
            try:
                if not check(file_path, content):
                    passed = False
            except Exception as e:
                self.add_issue(file_path, f"验证规则失败: {check.__name__}", str(e))
                passed = False

        if passed:
            print("  ✅ 通过验证")
        else:
            print(
                f"  ❌ 发现 {len([i for i in self.issues if i['file'] == str(file_path)])} 个问题"
            )

        return passed

    def check_filename(self, file_path, content):
        """检查文件名规范"""
        filename = file_path.name
        issues = []

        # 规则1: 英文优先，允许中文但推荐英文
        if re.search(r"[\u4e00-\u9fff]", filename):
            issues.append("文件名包含中文字符（推荐使用英文）")

        # 规则2: 短横线分隔
        if "_" in filename and "-" not in filename:
            issues.append("文件名使用下划线分隔（推荐使用短横线）")

        # 规则3: 小写字母
        if filename.lower() != filename:
            issues.append("文件名包含大写字母（推荐全部小写）")

        # 规则4: 扩展名正确
        if not filename.endswith(".md"):
            issues.append("文件扩展名应为.md")

        if issues:
            for issue in issues:
                self.add_issue(file_path, "文件名规范", issue)
            return False

        return True

    def check_frontmatter(self, file_path, content):
        """检查Frontmatter元数据"""
        # 不是所有文档都需要frontmatter，暂时不强制
        return True

    def check_structure(self, file_path, content):
        """检查文档结构"""
        lines = content.split("\n")
        issues = []

        # 规则1: 必须有标题
        has_title = False
        for line in lines:
            if line.startswith("# "):
                has_title = True
                break

        if not has_title:
            issues.append("文档缺少一级标题")

        # 规则2: 标题后应有空行
        for i, line in enumerate(lines):
            if line.startswith("#") and i < len(lines) - 1:
                next_line = lines[i + 1]
                if next_line.strip() and not next_line.startswith("#"):
                    issues.append(f"标题后应添加空行（第{i + 1}行）")
                    break

        # 规则3: 代码块格式正确
        in_code_block = False
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
            elif not in_code_block:
                # 检查列表格式
                if line.strip().startswith("- ") or line.strip().startswith("* "):
                    if len(line) - len(line.lstrip()) > 2:
                        issues.append(f"列表缩进应为2个空格（第{i + 1}行）")

        if issues:
            for issue in issues:
                self.add_issue(file_path, "文档结构", issue)
            return False

        return True

    def check_heading_levels(self, file_path, content):
        """检查标题层级"""
        lines = content.split("\n")
        heading_levels = []
        issues = []

        for i, line in enumerate(lines):
            if line.startswith("#"):
                # 计算标题级别
                level = len(line.split(" ")[0])
                heading_levels.append((i + 1, level, line))

        # 检查标题层级是否连续
        if heading_levels:
            # 第一个标题应为一级标题
            first_line, first_level, first_text = heading_levels[0]
            if first_level > 1:
                issues.append(f"第一个标题应为一级标题（第{first_line}行）")

            # 检查标题跳跃
            for j in range(1, len(heading_levels)):
                prev_line, prev_level, prev_text = heading_levels[j - 1]
                curr_line, curr_level, curr_text = heading_levels[j]

                if curr_level > prev_level + 1:
                    issues.append(f"标题层级跳跃过大：{prev_text} → {curr_text}（第{curr_line}行）")

        if issues:
            for issue in issues:
                self.add_issue(file_path, "标题层级", issue)
            return False

        return True

    def check_code_blocks(self, file_path, content):
        """检查代码块"""
        # 简单的代码块闭合检查
        code_block_pattern = r"```.*?```"
        list(re.finditer(code_block_pattern, content, re.DOTALL))

        # 检查是否每个```都有对应的结束```
        lines = content.split("\n")
        code_block_count = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                code_block_count += 1

        if code_block_count % 2 != 0:
            self.add_issue(file_path, "代码块", "代码块未正确闭合")
            return False

        return True

    def check_tables(self, file_path, content):
        """检查表格格式"""
        # 表格行应包含 | 字符且格式一致
        lines = content.split("\n")
        in_table = False
        table_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "|" in stripped and not stripped.startswith("#"):
                if not in_table:
                    in_table = True
                    table_start = i + 1
            elif in_table and stripped:
                in_table = False
                # 检查表格是否有分隔行
                if i - table_start > 1:
                    has_separator = False
                    for j in range(table_start, i):
                        if (
                            lines[j].strip().replace("-", "").replace("|", "").replace(" ", "")
                            == ""
                        ):
                            has_separator = True
                            break
                    if not has_separator:
                        self.add_issue(
                            file_path, "表格格式", f"表格缺少分隔行（第{table_start}行开始）"
                        )
                        return False

        return True

    def check_links(self, file_path, content):
        """检查链接格式"""
        # 检查是否使用相对链接而非绝对链接
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.finditer(link_pattern, content)

        issues = []
        for match in matches:
            link_text, link_url = match.groups()
            # 检查是否使用绝对路径（以/开头但可能有问题）
            if link_url.startswith("http://") or link_url.startswith("https://"):
                # 外部链接，OK
                continue
            elif link_url.startswith("/"):
                # 绝对路径，检查是否在docs目录内
                if not link_url.startswith("/docs/"):
                    issues.append(f"链接使用绝对路径: {link_url}")

        if issues:
            for issue in issues:
                self.add_issue(file_path, "链接格式", issue)
            return False

        return True

    def check_last_updated(self, file_path, content):
        """检查最后更新日期"""
        # 检查是否包含最后更新信息
        last_updated_patterns = [
            r"最后更新\s*[:：]\s*\d{4}-\d{2}-\d{2}",
            r"Last updated\s*[:：]\s*\d{4}-\d{2}-\d{2}",
            r"Updated\s*[:：]\s*\d{4}-\d{2}-\d{2}",
        ]

        for pattern in last_updated_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # 如果不是严格模式，不强制要求
        if self.strict:
            self.add_issue(file_path, "文档元数据", "缺少最后更新日期")
            return False

        return True

    def add_issue(self, file_path, category, message):
        """添加问题记录"""
        self.issues.append(
            {
                "file": str(file_path),
                "category": category,
                "message": message,
                "severity": "WARNING" if not self.strict else "ERROR",
            }
        )

    def validate_directory(self, directory):
        """验证目录中的所有Markdown文件"""
        directory = Path(directory)
        if not directory.exists():
            print(f"❌ 目录不存在: {directory}")
            return False

        md_files = list(directory.rglob("*.md"))
        if not md_files:
            print(f"📭 目录中未找到Markdown文件: {directory}")
            return True

        print(f"📁 验证目录: {directory}")
        print(f"📄 找到 {len(md_files)} 个Markdown文件")

        passed_count = 0
        for md_file in md_files:
            if self.validate_file(md_file):
                passed_count += 1

        print("\n📊 验证结果:")
        print(f"  ✅ 通过: {passed_count}/{len(md_files)}")
        print(f"  ❌ 失败: {len(md_files) - passed_count}/{len(md_files)}")
        print(f"  ⚠️  问题: {len(self.issues)} 个")

        return passed_count == len(md_files)

    def get_issues_report(self):
        """获取问题报告"""
        if not self.issues:
            return "✅ 所有验证通过，未发现问题"

        report = "# 文档格式验证报告\n\n"
        report += "## 摘要\n"
        report += f"- 发现 {len(self.issues)} 个问题\n"
        report += f"- 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # 按文件分组
        issues_by_file = {}
        for issue in self.issues:
            file_path = issue["file"]
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)

        report += "## 详细问题\n\n"
        for file_path, file_issues in issues_by_file.items():
            report += f"### {file_path}\n\n"
            for issue in file_issues:
                report += f"- **{issue['category']}** ({issue['severity']}): {issue['message']}\n"
            report += "\n"

        return report


def main():
    parser = argparse.ArgumentParser(description="验证文档格式规范")
    parser.add_argument("--file", "-f", help="验证单个文件")
    parser.add_argument("--directory", "-d", help="验证目录（递归）")
    parser.add_argument("--strict", "-s", action="store_true", help="严格模式，强制要求所有规范")
    parser.add_argument("--fix", action="store_true", help="自动修复简单问题（开发中）")
    parser.add_argument("--output", "-o", help="输出报告文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    if not args.file and not args.directory:
        args.directory = "docs/"

    validator = DocumentValidator(strict=args.strict)

    if args.file:
        validator.validate_file(args.file)
    elif args.directory:
        validator.validate_directory(args.directory)

    # 生成报告
    report = validator.get_issues_report()
    print("\n" + "=" * 80)
    print(report)
    print("=" * 80)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📝 报告已保存到: {args.output}")

    # 如果有问题且是严格模式，返回错误码
    if validator.issues and args.strict:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
