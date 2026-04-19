#!/usr/bin/env python3
"""
性能基线季度审查脚本
每季度运行一次，审查性能基线是否需要更新
"""

import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_baseline():
    """加载性能基线配置"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from config.performance_baseline import PERFORMANCE_BASELINE

        return PERFORMANCE_BASELINE
    except ImportError as e:
        print(f"❌ 无法加载性能基线配置: {e}")
        return None


def collect_current_performance():
    """收集当前性能数据（简化版）"""
    # 这里可以扩展为实际收集性能数据
    # 目前返回模拟数据用于演示
    return {
        "collection_time": datetime.now().isoformat(),
        "system_resources": {
            "cpu_usage": {"average": 2.1, "minimum": 0.5, "maximum": 45.3},  # 模拟数据
            "memory_usage": {"average": 59.8, "minimum": 55.2, "maximum": 78.1},
        },
        "maref_metrics": {"control_entropy_h_c": 0.0, "gray_code_compliance_rate": 1.0},
    }


def compare_with_baseline(baseline, current_data):
    """比较当前性能与基线"""
    print("=== 性能基线季度审查 ===\n")

    baseline_time = baseline.get("24_hour_monitoring", {}).get("start_time", "未知")
    print(f"基线建立时间: {baseline_time}")
    print(f"当前审查时间: {datetime.now().isoformat()}")

    print(f"\n1. 系统资源比较:")

    # CPU使用率比较
    baseline_cpu = baseline["system_resources"]["cpu_usage"]
    current_cpu = current_data["system_resources"]["cpu_usage"]

    print(f"   CPU使用率:")
    print(
        f"     基线: {baseline_cpu['average']:.1f}% (平均), {baseline_cpu['maximum']:.1f}% (最大)"
    )
    print(f"     当前: {current_cpu['average']:.1f}% (平均), {current_cpu['maximum']:.1f}% (最大)")

    cpu_change = (
        ((current_cpu["average"] - baseline_cpu["average"]) / baseline_cpu["average"] * 100)
        if baseline_cpu["average"] > 0
        else 0
    )
    if abs(cpu_change) > 20:
        print(f"     ⚠️  CPU使用率变化较大: {cpu_change:+.1f}%")

    # 内存使用率比较
    baseline_mem = baseline["system_resources"]["memory_usage"]
    current_mem = current_data["system_resources"]["memory_usage"]

    print(f"   内存使用率:")
    print(
        f"     基线: {baseline_mem['average']:.1f}% (平均), {baseline_mem['maximum']:.1f}% (最大)"
    )
    print(f"     当前: {current_mem['average']:.1f}% (平均), {current_mem['maximum']:.1f}% (最大)")

    mem_change = (
        ((current_mem["average"] - baseline_mem["average"]) / baseline_mem["average"] * 100)
        if baseline_mem["average"] > 0
        else 0
    )
    if abs(mem_change) > 15:
        print(f"     ⚠️  内存使用率变化较大: {mem_change:+.1f}%")

    print(f"\n2. MAREF指标比较:")

    # 控制熵比较
    baseline_entropy = baseline["maref_metrics"]["control_entropy_h_c"]["average"]
    current_entropy = current_data["maref_metrics"]["control_entropy_h_c"]

    print(f"   控制熵H_c:")
    print(f"     基线: {baseline_entropy:.3f}")
    print(f"     当前: {current_entropy:.3f}")

    # 格雷编码合规率比较
    baseline_gray = baseline["maref_metrics"]["gray_code_compliance_rate"]
    current_gray = current_data["maref_metrics"]["gray_code_compliance_rate"]

    print(f"   格雷编码合规率:")
    print(f"     基线: {baseline_gray*100:.1f}%")
    print(f"     当前: {current_gray*100:.1f}%")

    print(f"\n3. 审查结论:")

    # 判断是否需要更新基线
    changes_detected = []

    if abs(cpu_change) > 20:
        changes_detected.append(f"CPU使用率变化 {cpu_change:+.1f}%")
    if abs(mem_change) > 15:
        changes_detected.append(f"内存使用率变化 {mem_change:+.1f}%")
    if abs(current_entropy - baseline_entropy) > 0.1:
        changes_detected.append(f"控制熵变化 {current_entropy - baseline_entropy:+.3f}")
    if abs(current_gray - baseline_gray) > 0.05:
        changes_detected.append(f"格雷编码合规率变化 {(current_gray - baseline_gray)*100:+.1f}%")

    if changes_detected:
        print(f"   ⚠️  检测到显著变化:")
        for change in changes_detected:
            print(f"     - {change}")
        print(f"   建议: 考虑更新性能基线配置")
        return False
    else:
        print(f"   ✅ 性能指标稳定，与基线一致")
        print(f"   建议: 保持当前基线配置")
        return True


def generate_review_report(baseline, current_data, is_stable):
    """生成审查报告"""
    report_dir = Path("logs/baseline_reviews")
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"baseline_review_{timestamp}.json"

    report = {
        "review_timestamp": datetime.now().isoformat(),
        "baseline_timestamp": baseline.get("24_hour_monitoring", {}).get("start_time", ""),
        "current_performance": current_data,
        "is_performance_stable": is_stable,
        "recommendation": "keep_baseline" if is_stable else "update_baseline",
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n4. 报告生成:")
    print(f"   审查报告已保存: {report_file}")

    return report_file


def main():
    """主函数"""
    print("开始性能基线季度审查...\n")

    # 1. 加载基线
    baseline = load_baseline()
    if not baseline:
        return 1

    # 2. 收集当前性能数据
    current_data = collect_current_performance()

    # 3. 比较分析
    is_stable = compare_with_baseline(baseline, current_data)

    # 4. 生成报告
    report_file = generate_review_report(baseline, current_data, is_stable)

    # 5. 下一步建议
    print(f"\n5. 后续步骤:")
    if is_stable:
        print(f"   ✅ 性能稳定，无需立即更新基线")
        print(f"   建议: 继续使用当前基线，下一季度再次审查")
    else:
        print(f"   ⚠️  检测到显著变化，建议更新性能基线")
        print(f"   更新步骤:")
        print(f"     1. 运行24小时监控收集新数据")
        print(f"     2. 分析新数据: python3 analyze_long_term_monitor.py")
        print(f"     3. 更新配置文件: config/performance_baseline.py")
        print(f"     4. 验证更新: python3 validate_performance_baseline.py")

    print(f"\n✅ 季度审查完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
