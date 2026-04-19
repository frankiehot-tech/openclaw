#!/usr/bin/env python3
"""
文档完整性检查工具
检查Markdown文档是否包含必要的结构和元数据
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path


class DocumentCompletenessChecker:
    """文档完整性检查器"""

    def __init__(self, strict=False):
        self.strict = strict
        self.issues = []
        self.metrics = {}

    def check_file(self, file_path):
        """检查单个文件的完整性"""
        file_path = Path(file_path)
        relative_path = (
            file_path.relative_to(Path.cwd()) if file_path.is_relative_to(Path.cwd()) else file_path
        )

        print(f"📄 检查完整性: {relative_path}")

        # 读取文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.add_issue(file_path, "无法读取文件", str(e))
            return False

        lines = content.split("\n")

        # 执行所有完整性检查
        checks = [
            self.check_title,
            self.check_metadata,
            self.check_structure,
            self.check_content_quality,
            self.check_links_section,
        ]

        file_metrics = {
            "file": str(file_path),
            "total_lines": len(lines),
            "checks_passed": 0,
            "total_checks": len(checks),
        }

        passed_checks = 0
        for check in checks:
            try:
                if check(file_path, content, lines):
                    passed_checks += 1
                else:
                    # 检查失败，但继续执行其他检查
                    pass
            except Exception as e:
                self.add_issue(file_path, f"完整性检查失败: {check.__name__}", str(e))

        file_metrics["checks_passed"] = passed_checks
        file_metrics["completeness_score"] = (
            int((passed_checks / len(checks)) * 100) if checks else 0
        )
        self.metrics[str(file_path)] = file_metrics

        if passed_checks == len(checks):
            print(f"  ✅ 完整性检查通过 ({passed_checks}/{len(checks)})")
            return True
        else:
            print(f"  ⚠️  完整性检查部分通过 ({passed_checks}/{len(checks)})")
            return passed_checks >= (len(checks) // 2)  # 通过半数以上检查即可

    def check_title(self, file_path, content, lines):
        """检查文档是否有标题"""
        # 寻找一级标题 (# 标题)
        for line in lines:
            if line.startswith("# "):
                return True

        # 如果没有一级标题，检查是否有其他格式的标题
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and len(stripped) > 1 and stripped[1] != "#":
                self.add_issue(file_path, "标题格式", "建议使用# 作为一级标题（而非#Title）")
                return True

        self.add_issue(file_path, "文档结构", "缺少文档标题（建议以# 标题开头）")
        return False

    def check_metadata(self, file_path, content, lines):
        """检查文档元数据"""
        # 检查最后更新日期
        last_updated_patterns = [
            r"最后更新\s*[:：]\s*\d{4}-\d{2}-\d{2}",
            r"Last updated\s*[:：]\s*\d{4}-\d{2}-\d{2}",
            r"Updated\s*[:：]\s*\d{4}-\d{2}-\d{2}",
            r"最后更新日期\s*[:：]\s*\d{4}-\d{2}-\d{2}",
        ]

        has_metadata = False
        for pattern in last_updated_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_metadata = True
                break

        # 检查版本信息
        version_patterns = [
            r"版本\s*[:：]\s*[\d\.]+",
            r"Version\s*[:：]\s*[\d\.]+",
            r"v[\d\.]+",
        ]

        has_version = False
        for pattern in version_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_version = True
                break

        # 检查维护者信息
        maintainer_patterns = [
            r"维护者\s*[:：]",
            r"Maintainer\s*[:：]",
            r"作者\s*[:：]",
            r"Author\s*[:：]",
        ]

        has_maintainer = False
        for pattern in maintainer_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_maintainer = True
                break

        metadata_items = []
        if has_metadata:
            metadata_items.append("最后更新日期")
        if has_version:
            metadata_items.append("版本信息")
        if has_maintainer:
            metadata_items.append("维护者信息")

        if metadata_items:
            # 至少有一种元数据
            if len(metadata_items) >= 2:
                return True
            else:
                self.add_issue(
                    file_path, "文档元数据", f"缺少完整元数据（当前有：{metadata_items[0]}）"
                )
                return True  # 有元数据但不够完整，仍返回True

        self.add_issue(
            file_path, "文档元数据", "缺少文档元数据（建议添加最后更新日期、版本、维护者）"
        )
        return False

    def check_structure(self, file_path, content, lines):
        """检查文档结构"""
        # 检查是否有章节标题（二级标题及以上）
        heading_count = 0
        for line in lines:
            if line.startswith("##"):
                heading_count += 1

        # 长文档应有章节结构
        if len(lines) > 50:  # 超过50行的文档
            if heading_count >= 2:
                return True
            else:
                self.add_issue(
                    file_path,
                    "文档结构",
                    f"长文档({len(lines)}行)建议添加更多章节标题（当前{heading_count}个）",
                )
                return heading_count > 0  # 至少有1个标题即可
        else:
            # 短文档，章节标题可选
            return True

    def check_content_quality(self, file_path, content, lines):
        """检查内容质量"""
        # 检查是否有实质性内容（非空白行）
        non_empty_lines = [
            line for line in lines if line.strip() and not line.strip().startswith("#")
        ]

        if len(non_empty_lines) < 5:  # 少于5行实质性内容
            self.add_issue(
                file_path,
                "内容质量",
                f"实质性内容较少（{len(non_empty_lines)}行），建议补充详细信息",
            )
            return len(non_empty_lines) > 0  # 至少有内容即可

        # 检查是否有代码示例（代码块）
        code_block_pattern = r"```.*?```"
        code_blocks = re.findall(code_block_pattern, content, re.DOTALL)

        # 检查是否有列表项
        list_items = sum(
            1 for line in lines if line.strip().startswith("- ") or line.strip().startswith("* ")
        )

        # 检查是否有表格
        table_lines = sum(1 for line in lines if "|" in line and not line.startswith("#"))

        # 技术文档应有代码示例或表格
        if file_path.name.endswith(".md"):
            # 判断是否为技术文档（基于文件路径）
            tech_keywords = ["guide", "tutorial", "api", "spec", "config", "setup"]
            if any(keyword in file_path.name.lower() for keyword in tech_keywords):
                if code_blocks or table_lines > 0:
                    return True
                else:
                    self.add_issue(file_path, "内容质量", "技术文档建议添加代码示例或表格")
                    return True  # 不强制要求

        return True

    def check_links_section(self, file_path, content, lines):
        """检查相关链接部分"""
        # 检查是否有相关链接、参考文档或下一步链接
        link_section_patterns = [
            r"##\s*相关文档",
            r"##\s*参考链接",
            r"##\s*下一步",
            r"##\s*References",
            r"##\s*Related",
            r"##\s*See also",
        ]

        # 检查整个内容中是否有链接
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        links = re.findall(link_pattern, content)

        if links:
            # 有链接，检查是否有链接分类部分
            for pattern in link_section_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True

            # 没有专门的链接部分，但至少有链接
            if len(links) >= 3:  # 链接较多时建议有分类
                self.add_issue(file_path, "文档结构", "建议添加'相关文档'或'参考链接'部分组织链接")
            return True

        # 没有链接
        self.add_issue(file_path, "文档结构", "建议添加相关文档链接提高文档互联性")
        return False  # 没有链接时返回False（非强制）

    def add_issue(self, file_path, category, message):
        """添加问题记录"""
        self.issues.append(
            {
                "file": str(file_path),
                "category": category,
                "message": message,
                "severity": "INFO",  # 完整性检查通常为建议性
            }
        )

    def check_directory(self, directory):
        """检查目录中的所有Markdown文件"""
        directory = Path(directory)
        if not directory.exists():
            print(f"❌ 目录不存在: {directory}")
            return False

        md_files = list(directory.rglob("*.md"))
        if not md_files:
            print(f"📭 目录中未找到Markdown文件: {directory}")
            return True

        print(f"📁 检查目录: {directory}")
        print(f"📄 找到 {len(md_files)} 个Markdown文件")

        passed_count = 0
        for md_file in md_files:
            if self.check_file(md_file):
                passed_count += 1

        print(f"\n📊 完整性检查结果:")
        print(f"  ✅ 完全通过: {passed_count}/{len(md_files)}")
        print(f"  ⚠️  部分通过: {len(md_files) - passed_count}/{len(md_files)}")
        print(f"  📝 建议项: {len(self.issues)} 个")

        # 计算平均完整性分数
        total_score = 0
        for metrics in self.metrics.values():
            total_score += metrics.get("completeness_score", 0)

        avg_score = total_score / len(self.metrics) if self.metrics else 0
        print(f"  📈 平均完整性分数: {avg_score:.1f}/100")

        return passed_count == len(md_files)

    def get_issues_report(self):
        """获取问题报告"""
        if not self.issues:
            return "✅ 所有完整性检查通过，文档结构完整"

        report = "# 文档完整性检查报告\n\n"
        report += f"## 摘要\n"
        report += f"- 发现 {len(self.issues)} 个完整性建议\n"
        report += f"- 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # 按文件分组
        issues_by_file = {}
        for issue in self.issues:
            file_path = issue["file"]
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)

        report += "## 详细建议\n\n"
        for file_path, file_issues in issues_by_file.items():
            rel_path = (
                Path(file_path).relative_to(Path.cwd())
                if Path(file_path).is_relative_to(Path.cwd())
                else file_path
            )
            report += f"### {rel_path}\n\n"

            # 显示该文件的完整性分数
            if file_path in self.metrics:
                score = self.metrics[file_path].get("completeness_score", 0)
                report += f"**完整性分数**: {score}/100\n\n"

            for issue in file_issues:
                report += f"- **{issue['category']}** ({issue['severity']}): {issue['message']}\n"
            report += "\n"

        return report

    def get_metrics_summary(self):
        """获取指标摘要"""
        if not self.metrics:
            return {}

        total_files = len(self.metrics)
        total_checks = sum(m.get("total_checks", 0) for m in self.metrics.values())
        passed_checks = sum(m.get("checks_passed", 0) for m in self.metrics.values())
        avg_score = (
            sum(m.get("completeness_score", 0) for m in self.metrics.values()) / total_files
            if total_files > 0
            else 0
        )

        return {
            "total_files": total_files,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "pass_rate": (passed_checks / total_checks * 100) if total_checks > 0 else 0,
            "avg_completeness_score": avg_score,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    parser = argparse.ArgumentParser(description="检查文档完整性")
    parser.add_argument("--file", "-f", help="检查单个文件")
    parser.add_argument("--directory", "-d", help="检查目录（递归）")
    parser.add_argument(
        "--strict", "-s", action="store_true", help="严格模式，强制要求所有完整性规范"
    )
    parser.add_argument("--output", "-o", help="输出报告文件")
    parser.add_argument("--metrics", action="store_true", help="输出JSON格式指标数据")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    if not args.file and not args.directory:
        args.directory = "docs/"

    checker = DocumentCompletenessChecker(strict=args.strict)

    success = True
    if args.file:
        success = checker.check_file(args.file)
    elif args.directory:
        success = checker.check_directory(args.directory)

    # 生成报告
    report = checker.get_issues_report()
    print("\n" + "=" * 80)
    print(report)
    print("=" * 80)

    # 输出指标数据
    if args.metrics:
        metrics = checker.get_metrics_summary()
        import json

        print("\n📊 指标数据:")
        print(json.dumps(metrics, indent=2, ensure_ascii=False))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📝 报告已保存到: {args.output}")

    # 如果有问题且是严格模式，返回错误码
    if checker.issues and args.strict:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
