#!/usr/bin/env python3
"""
修复审计文档链接脚本
解决审计文件命名不一致（下划线vs短横线）的问题
"""

import os
import re
import sys
from pathlib import Path


def find_markdown_files(directory):
    """查找所有Markdown文件"""
    md_files = []
    for root, dirs, files in os.walk(directory):
        # 跳过隐藏目录和排除目录
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["vendor", "node_modules"]]

        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
    return md_files


def audit_file_mapping():
    """创建审计文件映射表（下划线->短横线）"""
    mapping = {
        # 审计索引中的链接 -> 实际文件名
        "deep_audit_report_20260419.md": "deep-audit-report-2026-04.md",
        "audit_executive_summary_20260419.md": "audit-executive-summary-2026-04.md",
        "improvement-implementation-plan-2026-04.md": "improvement-implementation-plan-2026-04.md",
        "next-phase-engineering-plan-2026-04.md": "next-phase-engineering-plan-2026-04.md",
        "maref_audit_report_2026_0418.md": "maref-audit-report-2026-04.md",
        "aiplan_approval_workflow_audit_20260419.md": "aiplan-approval-workflow-audit-2026-04.md",
        "improvement_implementation_plan_20260419.md": "improvement-implementation-plan-2026-04.md",
        # 其他常见映射
        "gstack-integration.md": None,  # 需要创建或移除
        "system-architecture.md": "system-design.md",  # 可能指向system-design.md
    }
    return mapping


def fix_links_in_file(file_path, mapping):
    """修复文件中的链接"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    changes = []

    # 修复审计文件链接
    for old_link, new_link in mapping.items():
        if new_link is None:
            continue

        # 查找所有包含旧链接的模式
        # 标准Markdown链接: [text](url)
        pattern = r"(\[[^\]]+\]\()([^)]*" + re.escape(old_link) + r")(\))"

        def replace_link(match):
            before = match.group(1)  # [text](
            url = match.group(2)  # 链接部分
            after = match.group(3)  # )

            # 替换链接
            new_url = url.replace(old_link, new_link)
            return before + new_url + after

        new_content, count = re.subn(pattern, replace_link, content)
        if count > 0:
            changes.append(f"  - {old_link} -> {new_link}: {count}处")
            content = new_content

    # 修复./开头的相对链接
    # 查找./开头的链接，如果目标文件不存在，尝试查找对应文件
    pattern = r"(\[[^\]]+\]\()(\./[^)]+\.md)(\))"

    def fix_dot_links(match):
        before = match.group(1)
        url = match.group(2)
        after = match.group(3)

        # 获取文件所在目录
        file_dir = os.path.dirname(file_path)
        target_path = os.path.join(file_dir, url[2:])  # 去掉./

        # 如果文件不存在，尝试在audit/2026-04中查找
        if not os.path.exists(target_path):
            # 提取文件名
            filename = os.path.basename(url)

            # 检查是否是下划线格式，尝试转换为短横线
            if "_" in filename:
                # 尝试转换为短横线格式
                # 简单的转换：下划线替换为短横线
                base_name = filename.replace(".md", "")
                # 假设格式为: name_yyyyMMdd.md
                # 转换为: name-yyyy-MM-dd.md 或 name-yyyy-MM.md
                # 这里先简单替换
                new_filename = base_name.replace("_", "-") + ".md"

                # 检查转换后的文件是否存在
                new_target = os.path.join(file_dir, new_filename)
                if os.path.exists(new_target):
                    return before + "./" + new_filename + after

                # 在audit/2026-04目录中查找
                audit_dir = os.path.join(os.path.dirname(file_dir), "..", "audit", "2026-04")
                if os.path.exists(audit_dir):
                    for audit_file in os.listdir(audit_dir):
                        if audit_file.endswith(".md"):
                            # 检查是否匹配（忽略下划线和短横线的差异）
                            audit_base = audit_file.replace(".md", "").replace("-", "_")
                            filename_base = filename.replace(".md", "").replace("-", "_")
                            if audit_base == filename_base:
                                # 找到匹配的文件
                                relative_path = os.path.relpath(
                                    os.path.join(audit_dir, audit_file), file_dir
                                )
                                return before + relative_path + after

        # 没有找到匹配的文件，保持原样
        return before + url + after

    new_content, dot_count = re.subn(pattern, fix_dot_links, content)
    if dot_count > 0:
        changes.append(f"  - 修复./相对链接: {dot_count}处")
        content = new_content

    # 如果内容有变化，保存文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return changes
    else:
        return None


def main():
    """主函数"""
    project_root = Path("/Volumes/1TB-M2/openclaw")
    docs_dir = project_root / "docs"

    if not docs_dir.exists():
        print(f"❌ 文档目录不存在: {docs_dir}")
        sys.exit(1)

    # 获取审计文件映射
    mapping = audit_file_mapping()

    # 查找所有Markdown文件
    md_files = find_markdown_files(docs_dir)
    print(f"📄 找到 {len(md_files)} 个Markdown文件")

    # 修复链接
    total_fixes = 0
    files_modified = []

    for md_file in md_files:
        changes = fix_links_in_file(md_file, mapping)
        if changes:
            files_modified.append({"file": os.path.relpath(md_file, docs_dir), "changes": changes})
            total_fixes += len(changes)

    # 输出结果
    if files_modified:
        print(f"✅ 修复完成: {len(files_modified)} 个文件被修改，共 {total_fixes} 处修复")
        print("\n修改详情:")
        for file_info in files_modified:
            print(f"\n📝 {file_info['file']}:")
            for change in file_info["changes"]:
                print(change)
    else:
        print("ℹ️  没有需要修复的链接")

    # 检查是否需要创建缺失的文件
    print("\n🔍 检查缺失的文件:")
    missing_files = []
    for old_link, new_link in mapping.items():
        if new_link is None:
            print(f"  ⚠️  {old_link}: 文件不存在，需要创建或移除引用")
            missing_files.append(old_link)

    if missing_files:
        print(f"\n💡 建议:")
        print("  1. 创建缺失的文档文件（如gstack-integration.md）")
        print("  2. 或更新文档中的链接指向现有文件")
        print("  3. 或从文档中移除这些无效链接")


if __name__ == "__main__":
    main()
