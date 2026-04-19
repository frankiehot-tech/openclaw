#!/usr/bin/env python3
"""
Completed 任务蒸馏回流与递归改进闭环。

扫描 memory 中的 completed 任务，根据规则判定是否应蒸馏，
并生成回流候选：memory backfill、skill candidate、policy/update candidate、workflow insight。

执行方式：
1. 作为独立脚本运行：python3 scripts/distill_completed.py
2. 由 athena_ai_plan_runner.py 在任务完成时触发。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 运行时根目录
try:
    from openclaw_roots import RUNTIME_ROOT
except ImportError:
    # fallback
    RUNTIME_ROOT = Path("/Volumes/1TB-M2/openclaw")

MEMORY_DIR = RUNTIME_ROOT / "memory"
CANDIDATES_DIR = RUNTIME_ROOT / "candidates"
SKILLS_DIR = CANDIDATES_DIR / "skills"
POLICIES_DIR = CANDIDATES_DIR / "policies"
WORKFLOWS_DIR = CANDIDATES_DIR / "workflows"
LONGTERM_MEMORY = RUNTIME_ROOT / "MEMORY.md"

# 确保目录存在
for d in (SKILLS_DIR, POLICIES_DIR, WORKFLOWS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def load_today_memory() -> List[Dict[str, Any]]:
    """加载当天的 memory 文件，提取 completed 任务条目。"""
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = MEMORY_DIR / f"{today}.md"
    if not memory_file.exists():
        return []

    content = memory_file.read_text(encoding="utf-8")
    entries = []

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("## ") and "任务完成" in line:
            title = line[3:].replace("任务完成", "").strip()
            entry = {"title": title, "status": "unknown", "queue_item_id": ""}
            i += 1
            # 跳过空行
            while i < len(lines) and not lines[i].strip():
                i += 1
            # 解析属性行，直到遇到下一个标题或文件结束
            while i < len(lines) and lines[i].strip().startswith("- "):
                item_line = lines[i].strip()
                if item_line.startswith("- 状态："):
                    entry["status"] = item_line.split("：", 1)[1].strip()
                elif item_line.startswith("- root_task_id："):
                    entry["root_task_id"] = item_line.split("：", 1)[1].strip()
                elif item_line.startswith("- queue_item_id："):
                    entry["queue_item_id"] = item_line.split("：", 1)[1].strip()
                elif item_line.startswith("- 阶段："):
                    entry["stage"] = item_line.split("：", 1)[1].strip()
                elif item_line.startswith("- 说明文档："):
                    entry["instruction_path"] = item_line.split("：", 1)[1].strip()
                elif item_line.startswith("- 摘要："):
                    entry["summary"] = item_line.split("：", 1)[1].strip()
                # 忽略预检提醒
                i += 1
                # 跳过可能存在的空行
                while i < len(lines) and not lines[i].strip():
                    i += 1
            if entry.get("status") == "completed":
                entries.append(entry)
            # 继续循环，i 已经指向下一个非属性行
        else:
            i += 1
    return entries


def should_distill(entry: Dict[str, Any]) -> Tuple[bool, str]:
    """
    判定是否应对该任务进行蒸馏。
    返回 (should_distill, reason)
    """
    status = entry.get("status", "")
    if status != "completed":
        return False, f"状态不是 completed: {status}"

    summary = entry.get("summary", "").lower()
    title = entry.get("title", "").lower()

    # 负面关键词：重复、已被吸收、无实质内容
    negative_keywords = [
        "已被现有",
        "重复造卡",
        "已被吸收",
        "不应再重复",
        "继续拆分只会",
        "保留为参考",
        "不直接进入自动执行",
    ]
    for kw in negative_keywords:
        if kw in summary or kw in title:
            return False, f"摘要或标题包含负面关键词: {kw}"

    # 正面关键词：表明有可重用知识
    positive_keywords = [
        "实现",
        "添加",
        "修复",
        "优化",
        "升级",
        "重构",
        "建立",
        "完成",
        "收敛",
        "对齐",
        "硬化",
    ]
    positive_count = sum(1 for kw in positive_keywords if kw in summary or kw in title)
    if positive_count == 0:
        return False, "摘要中未发现可重用知识关键词"

    # 阶段筛选：build 阶段的任务更可能包含可技能化操作
    stage = entry.get("stage", "")
    if stage not in ("build", "review", "plan", "research"):
        # 未知阶段，谨慎处理
        pass

    # 如果摘要过短（小于10字符），可能信息不足
    if len(summary) < 10:
        return False, "摘要过短，信息不足"

    return True, "符合蒸馏条件"


def distill_to_memory_backfill(entry: Dict[str, Any]) -> Optional[str]:
    """
    将任务重要摘要写入长期记忆 MEMORY.md。
    返回写入的路径或 None。
    """
    if not LONGTERM_MEMORY.exists():
        # 创建初始文件
        LONGTERM_MEMORY.write_text("# MEMORY.md - 长期记忆\n\n", encoding="utf-8")

    content = LONGTERM_MEMORY.read_text(encoding="utf-8")

    # 检查是否已存在相同 queue_item_id 的记录
    queue_item_id = entry.get("queue_item_id", "")
    if queue_item_id and f"queue_item_id: {queue_item_id}" in content:
        return None  # 幂等跳过

    # 构建新条目
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = f"""
## {entry.get("title", "未命名任务")} (蒸馏于 {timestamp})

- **queue_item_id**: {queue_item_id}
- **root_task_id**: {entry.get("root_task_id", "")}
- **阶段**: {entry.get("stage", "")}
- **摘要**: {entry.get("summary", "")}
- **源文档**: {entry.get("instruction_path", "")}

"""
    # 追加到文件末尾
    with LONGTERM_MEMORY.open("a", encoding="utf-8") as f:
        f.write(new_entry)

    return str(LONGTERM_MEMORY)


def distill_to_skill_candidate(entry: Dict[str, Any]) -> Optional[str]:
    """
    生成技能候选文件。
    返回文件路径或 None。
    """
    skill_id = f"skill_{entry.get('queue_item_id', entry.get('root_task_id', 'unknown')).replace('-', '_')}"
    title = entry.get("title", "未命名任务")
    summary = entry.get("summary", "")

    # 简单提取关键动词和对象
    verbs = [
        "实现",
        "添加",
        "修复",
        "优化",
        "升级",
        "重构",
        "建立",
        "完成",
        "收敛",
        "对齐",
    ]
    objects = []
    for verb in verbs:
        if verb in summary:
            # 尝试提取动词后的名词短语
            pass

    # 生成技能描述
    skill_content = f"""# {title} (技能候选)

**Skill ID**: `{skill_id}`
**来源任务**: {entry.get("queue_item_id", "")}
**生成时间**: {datetime.now().isoformat()}

## 描述

{summary}

## 适用场景

- 类似问题的修复或优化
- 相同技术栈的增量开发

## 操作要点

1. 回顾任务摘要：{summary}
2. 参考源文档：{entry.get("instruction_path", "")}
3. 检查相关 artifact（如有）

## 注意事项

- 此为自动生成的技能候选，需人工验证后正式入库。
- 确保不重复已有技能。

---
*Generated by distill_completed.py*
"""
    skill_path = SKILLS_DIR / f"{skill_id}.md"
    skill_path.write_text(skill_content, encoding="utf-8")
    return str(skill_path)


def distill_to_policy_candidate(entry: Dict[str, Any]) -> Optional[str]:
    """
    生成策略更新候选。
    返回文件路径或 None。
    """
    policy_id = f"policy_{entry.get('queue_item_id', entry.get('root_task_id', 'unknown')).replace('-', '_')}"
    title = entry.get("title", "未命名任务")
    summary = entry.get("summary", "")

    # 分析摘要，看是否涉及策略、规则、门禁等
    policy_keywords = ["规则", "策略", "门禁", "预检", "验收", "纪律", "约束", "优先级"]
    has_policy = any(kw in summary for kw in policy_keywords)
    if not has_policy:
        return None

    policy_content = f"""# {title} (策略候选)

**Policy ID**: `{policy_id}`
**来源任务**: {entry.get("queue_item_id", "")}
**生成时间**: {datetime.now().isoformat()}

## 问题背景

{summary}

## 建议策略更新

1. TODO: 根据任务内容提炼具体策略调整

## 验证方法

- 在类似任务中应用新策略
- 观察执行效率与成功率变化

## 风险提示

- 策略变更可能影响现有流程
- 需小范围测试后再全量推广

---
*Generated by distill_completed.py*
"""
    policy_path = POLICIES_DIR / f"{policy_id}.md"
    policy_path.write_text(policy_content, encoding="utf-8")
    return str(policy_path)


def distill_to_workflow_insight(entry: Dict[str, Any]) -> Optional[str]:
    """
    生成工作流洞察。
    返回文件路径或 None。
    """
    insight_id = f"workflow_{entry.get('queue_item_id', entry.get('root_task_id', 'unknown')).replace('-', '_')}"
    title = entry.get("title", "未命名任务")
    summary = entry.get("summary", "")
    stage = entry.get("stage", "")

    insight_content = f"""# {title} (工作流洞察)

**Insight ID**: `{insight_id}`
**来源任务**: {entry.get("queue_item_id", "")}
**阶段**: {stage}
**生成时间**: {datetime.now().isoformat()}

## 执行总结

{summary}

## 模式识别

- 任务类型: {stage}
- 关键动作: TODO: 提取重复模式

## 改进建议

1. TODO: 基于任务执行提炼工作流优化点

## 关联任务

- 可参考类似任务: {entry.get("root_task_id", "")}

---
*Generated by distill_completed.py*
"""
    insight_path = WORKFLOWS_DIR / f"{insight_id}.md"
    insight_path.write_text(insight_content, encoding="utf-8")
    return str(insight_path)


def distill_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    对单个任务条目进行蒸馏。
    返回蒸馏结果摘要。
    """
    should, reason = should_distill(entry)
    result = {
        "entry": entry,
        "should_distill": should,
        "reason": reason,
        "generated": [],
    }

    if not should:
        return result

    # 依次尝试各回流目标
    # 1. memory backfill
    mem_path = distill_to_memory_backfill(entry)
    if mem_path:
        result["generated"].append({"target": "memory_backfill", "path": mem_path})

    # 2. skill candidate
    skill_path = distill_to_skill_candidate(entry)
    if skill_path:
        result["generated"].append({"target": "skill_candidate", "path": skill_path})

    # 3. policy candidate
    policy_path = distill_to_policy_candidate(entry)
    if policy_path:
        result["generated"].append({"target": "policy_candidate", "path": policy_path})

    # 4. workflow insight
    workflow_path = distill_to_workflow_insight(entry)
    if workflow_path:
        result["generated"].append({"target": "workflow_insight", "path": workflow_path})

    return result


def distill_all() -> List[Dict[str, Any]]:
    """蒸馏所有今天的 completed 任务。"""
    entries = load_today_memory()
    results = []
    for entry in entries:
        result = distill_entry(entry)
        results.append(result)
    return results


def main():
    """命令行入口"""
    print("🧠 Completed 任务蒸馏回流启动")
    print(f"   扫描目录: {MEMORY_DIR}")
    print("-" * 50)

    results = distill_all()

    distilled_count = sum(1 for r in results if r["should_distill"])
    generated_total = sum(len(r["generated"]) for r in results)

    print(f"   发现 completed 任务: {len(results)} 个")
    print(f"   符合蒸馏条件: {distilled_count} 个")
    print(f"   生成候选文件: {generated_total} 个")

    for result in results:
        entry = result["entry"]
        if result["should_distill"]:
            print(f"\n   ✅ {entry.get('title', '未命名')}")
            print(f"      原因: {result['reason']}")
            for gen in result["generated"]:
                print(f"      → {gen['target']}: {gen['path']}")
        else:
            print(f"\n   ⏭️  {entry.get('title', '未命名')}")
            print(f"      跳过: {result['reason']}")

    print("-" * 50)
    print(f"📦 蒸馏完成")

    # 将本次蒸馏摘要写入 memory 文件（可选）
    if results:
        today = datetime.now().strftime("%Y-%m-%d")
        distill_summary = f"\n## 蒸馏回流摘要 ({datetime.now().strftime('%H:%M:%S')})\n"
        distill_summary += f"- 扫描任务: {len(results)} 个\n"
        distill_summary += f"- 符合蒸馏: {distilled_count} 个\n"
        distill_summary += f"- 生成候选: {generated_total} 个\n"
        memory_file = MEMORY_DIR / f"{today}.md"
        if memory_file.exists():
            with memory_file.open("a", encoding="utf-8") as f:
                f.write(distill_summary)

    return results


if __name__ == "__main__":
    main()
