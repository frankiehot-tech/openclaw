#!/usr/bin/env python3
"""修复validate_build_preflight函数中的变量作用域bug"""

import re


def fix_preflight_function(content):
    """修复validate_build_preflight函数中的变量作用域问题"""

    # 查找函数开始位置
    func_start = content.find("def validate_build_preflight(")
    if func_start == -1:
        print("❌ 未找到validate_build_preflight函数")
        return content

    # 找到函数体的开始（第一个冒号后的换行）
    func_body_start = content.find(":", func_start) + 1

    # 查找函数文档字符串的结束位置
    docstring_end = content.find('"""', func_body_start + 3)
    if docstring_end == -1:
        print("❌ 未找到函数文档字符串")
        return content

    # 文档字符串结束后找到第一个非空白字符
    func_code_start = docstring_end + 3
    while func_code_start < len(content) and content[func_code_start] in ["\n", " ", "\t"]:
        func_code_start += 1

    # 查找基因管理审计任务例外部分
    gene_management_pattern = r"# 例外规则：对于基因管理审计任务，放宽预检要求 \(P0修复\)"
    gene_management_match = re.search(gene_management_pattern, content[func_start:])

    if not gene_management_match:
        print("❌ 未找到基因管理审计任务例外部分")
        return content

    # 计算基因管理例外块的实际开始位置
    gene_exception_start = func_start + gene_management_match.start()

    # 找到例外块的结束（下一个注释或函数结尾）
    gene_exception_end = gene_exception_start
    while (
        gene_exception_end < len(content)
        and not content[gene_exception_end : gene_exception_end + 4] == "    #"
    ):
        gene_exception_end += 1

    # 现在检查例外块中是否有lines变量定义
    exception_block = content[gene_exception_start:gene_exception_end]

    # 检查是否已修复
    if "lines = instruction_text.splitlines()" in exception_block:
        print("✅ 基因管理例外块已包含lines变量定义")
        return content

    # 在基因管理例外块中添加lines变量定义
    # 找到合适的位置插入（在检查lines长度之前）
    lines_check_pattern = r"if len\(lines\) < 600:"
    lines_check_match = re.search(lines_check_pattern, exception_block)

    if not lines_check_match:
        print("❌ 未找到lines长度检查行")
        return content

    # 在lines长度检查前添加lines变量定义
    check_pos = lines_check_match.start()

    # 构建修复后的例外块
    fixed_block = exception_block[:check_pos]
    fixed_block += "            lines = instruction_text.splitlines()\n            "
    fixed_block += exception_block[check_pos:]

    # 替换原始内容
    fixed_content = content[:gene_exception_start] + fixed_block + content[gene_exception_end:]

    print("✅ 已修复基因管理例外块中的lines变量定义")

    # 检查并修复epic变量作用域问题
    # 查找所有使用epic变量的地方
    epic_pattern = r'epic == "gene_management"'
    epic_matches = list(re.finditer(epic_pattern, fixed_content[func_start:]))

    if epic_matches:
        print(f"✅ 找到{len(epic_matches)}处epic变量使用")

        # 检查第一处epic使用前是否有定义
        first_epic_use = func_start + epic_matches[0].start()

        # 回溯查找epic变量定义
        epic_def_found = False
        search_pos = first_epic_use - 1
        while search_pos > func_start:
            if "epic =" in fixed_content[search_pos - 100 : search_pos]:
                epic_def_found = True
                break
            search_pos -= 1

        if not epic_def_found:
            print("⚠️  epic变量可能在部分路径中未定义")
            # 在基因管理例外块中添加epic变量定义（如果不存在）
            if "epic = str(metadata.get" not in exception_block:
                # 在检查title之前添加epic定义
                metadata_pattern = r'metadata = item\.get\("metadata", \{\}\)'
                metadata_match = re.search(metadata_pattern, exception_block)

                if metadata_match:
                    metadata_pos = metadata_match.end()
                    # 在metadata定义后添加epic定义
                    new_exception_block = (
                        exception_block[:metadata_pos]
                        + '\n            epic = str(metadata.get("epic", "") or "").strip()'
                        + exception_block[metadata_pos:]
                    )

                    # 需要更新fixed_content
                    fixed_content = (
                        fixed_content[:gene_exception_start]
                        + new_exception_block
                        + fixed_content[gene_exception_end:]
                    )
                    print("✅ 已添加epic变量定义到基因管理例外块")

    return fixed_content


def main():
    """主函数"""
    file_path = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"

    print(f"🔧 修复 {file_path} 中的预检函数bug...")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return

    # 备份原始文件
    import shutil

    backup_path = file_path + ".backup_preflight_fix"
    shutil.copy2(file_path, backup_path)
    print(f"📂 已创建备份: {backup_path}")

    # 修复函数
    fixed_content = fix_preflight_function(content)

    if fixed_content == content:
        print("ℹ️  无需修复，函数可能已经正确")
        return

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    print("✅ 修复完成！")
    print("📋 主要修复内容:")
    print("   1. 在基因管理审计任务例外中添加lines变量定义")
    print("   2. 确保epic变量在需要的地方都有定义")
    print("   3. 修复变量作用域问题导致的NameError异常")

    # 验证修复
    print("\n🔍 验证修复效果...")
    if "lines = instruction_text.splitlines()" in fixed_content:
        # 检查是否在基因管理例外块中
        gene_management_section = re.search(
            r"# 例外规则：对于基因管理审计任务.*?# 1\. 基础校验", fixed_content, re.DOTALL
        )
        if gene_management_section:
            section_text = gene_management_section.group(0)
            if "lines = instruction_text.splitlines()" in section_text:
                print("✅ 验证通过：lines变量定义已添加到基因管理例外块")
            else:
                print("⚠️  警告：lines变量定义不在基因管理例外块中")
        else:
            print("⚠️  警告：未找到基因管理例外块")

    print(f"\n🚀 修复完成。需要重启队列运行器进程以应用更改。")


if __name__ == "__main__":
    main()
