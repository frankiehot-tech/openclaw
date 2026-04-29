#!/usr/bin/env python3
"""
文档可读性分析工具
分析Markdown文档的可读性指标，包括句子复杂度、段落结构和术语密度
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


class DocumentReadabilityAnalyzer:
    """文档可读性分析器"""

    def __init__(self):
        self.metrics = {}
        self.issues = []

    def analyze_file(self, file_path):
        """分析单个文件的可读性"""
        file_path = Path(file_path)
        relative_path = (
            file_path.relative_to(Path.cwd()) if file_path.is_relative_to(Path.cwd()) else file_path
        )

        print(f"📄 分析可读性: {relative_path}")

        # 读取文件内容
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.add_issue(file_path, "无法读取文件", str(e))
            return None

        lines = content.split("\n")

        # 过滤掉代码块、表格和元数据行
        filtered_content = self._filter_non_text_content(content, lines)

        if not filtered_content.strip():
            self.add_issue(file_path, "内容分析", "文档缺少可分析的文本内容")
            return None

        # 计算各种可读性指标
        file_metrics = {
            "file": str(file_path),
            "analysis_time": datetime.now().isoformat(),
            "basic_stats": self._calculate_basic_stats(filtered_content, lines),
            "readability_scores": self._calculate_readability_scores(filtered_content),
            "structural_metrics": self._calculate_structural_metrics(content, lines),
            "technical_density": self._calculate_technical_density(filtered_content, file_path),
            "overall_score": 0,
        }

        # 计算综合可读性分数
        overall_score = self._calculate_overall_score(file_metrics)
        file_metrics["overall_score"] = overall_score
        file_metrics["readability_level"] = self._get_readability_level(overall_score)

        self.metrics[str(file_path)] = file_metrics

        print(f"  📊 可读性分数: {overall_score:.1f}/100 ({file_metrics['readability_level']})")

        # 生成可读性建议
        suggestions = self._generate_suggestions(file_metrics)
        if suggestions:
            for suggestion in suggestions[:3]:  # 显示前3条建议
                print(f"  💡 建议: {suggestion}")

        return file_metrics

    def _filter_non_text_content(self, content, lines):
        """过滤掉非文本内容（代码块、表格、元数据）"""
        # 移除代码块
        code_block_pattern = r"```.*?```"
        content_no_code = re.sub(code_block_pattern, "", content, flags=re.DOTALL)

        # 移除行内代码
        re.sub(r"`[^`]+`", "", content_no_code)

        # 移除表格（简化处理）
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # 跳过代码块标记行
            if stripped.startswith("```"):
                continue
            # 跳过纯表格分隔行（仅包含|和-）
            if "|" in stripped and re.sub(r"[|\-\s]", "", stripped) == "":
                continue
            # 跳过元数据行（如最后更新、版本等）
            if any(
                keyword in stripped.lower()
                for keyword in [
                    "最后更新",
                    "last updated",
                    "version",
                    "版本",
                    "维护者",
                    "maintainer",
                ]
            ):
                continue

            # 移除行内的表格格式
            line_no_table = re.sub(r"\|\s*", " ", line)  # 移除表格管道符

            filtered_lines.append(line_no_table)

        return "\n".join(filtered_lines)

    def _calculate_basic_stats(self, content, lines):
        """计算基础统计信息"""
        # 段落数（基于空行分割）
        paragraphs = [p for p in content.split("\n\n") if p.strip()]

        # 句子分割（简单的中英文句子分割）
        # 中文句子结束符：。！？；英文句子结束符：.!?;
        sentence_pattern = r"[。！？\.\?!;]+"
        sentences = re.split(sentence_pattern, content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 单词/汉字计数（简化处理）
        # 中文字符
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", content)
        # 英文单词（简单分割）
        english_words = re.findall(r"\b[a-zA-Z]{2,}\b", content)

        # 计算平均句子长度
        avg_sentence_length = 0
        if sentences:
            # 中英文混合计算：中文字符数 + 英文单词数
            total_units = len(chinese_chars) + len(english_words)
            avg_sentence_length = total_units / len(sentences) if sentences else 0

        return {
            "total_lines": len(lines),
            "paragraphs": len(paragraphs),
            "sentences": len(sentences),
            "chinese_chars": len(chinese_chars),
            "english_words": len(english_words),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_paragraph_length": round(len(sentences) / len(paragraphs), 1) if paragraphs else 0,
        }

    def _calculate_readability_scores(self, content):
        """计算可读性分数（基于Flesch-Kincaid等算法调整）"""
        # 简化的可读性评估
        sentences = re.split(r"[。！？\.\?!;]+", content)
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return {
                "flesch_kincaid_adjusted": 0,
                "gunning_fog_adjusted": 0,
                "coleman_liau_adjusted": 0,
            }

        # 计算中文字符和英文单词
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", content)
        english_words = re.findall(r"\b[a-zA-Z]{3,}\b", content)  # 只计算3个字母以上的单词

        total_chars = len(chinese_chars) + sum(len(word) for word in english_words)
        total_words = len(chinese_chars) + len(english_words)  # 将中文字符和英文单词都视为"词"

        # 调整的Flesch-Kincaid分数（适应中英文混合）
        # 基础公式：206.835 - 1.015 * (总词数/总句子数) - 84.6 * (总音节数/总词数)
        # 简化调整：使用字符数代替音节数
        avg_words_per_sentence = total_words / len(sentences)
        avg_chars_per_word = total_chars / total_words if total_words > 0 else 0

        # 调整后的Flesch-Kincaid分数（范围0-100，越高越易读）
        flesch_kincaid = max(
            0, min(100, 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_chars_per_word)
        )

        # 调整的Gunning Fog指数（越高越难读）
        # 计算"复杂词"（这里定义为长度>=4的英文单词或包含技术术语）
        complex_words = sum(1 for word in english_words if len(word) >= 4)
        complex_words += len(chinese_chars) * 0.3  # 中文字符部分复杂度估计

        gunning_fog = (
            0.4 * (avg_words_per_sentence + 100 * (complex_words / total_words))
            if total_words > 0
            else 0
        )

        # 调整的Coleman-Liau指数
        coleman_liau = (
            0.0588 * (total_chars / total_words * 100)
            - 0.296 * (len(sentences) / total_words * 100)
            - 15.8
            if total_words > 0
            else 0
        )

        return {
            "flesch_kincaid_adjusted": round(flesch_kincaid, 1),
            "gunning_fog_adjusted": round(gunning_fog, 1),
            "coleman_liau_adjusted": round(coleman_liau, 1),
            "readability_interpretation": self._interpret_readability_score(flesch_kincaid),
        }

    def _interpret_readability_score(self, score):
        """解释可读性分数"""
        if score >= 90:
            return "非常易读（适合大众）"
        elif score >= 80:
            return "易读（适合普通读者）"
        elif score >= 70:
            return "中等难度（适合有相关知识的读者）"
        elif score >= 60:
            return "较难（适合专业读者）"
        elif score >= 50:
            return "难（需要专业知识）"
        else:
            return "非常难（专家级别）"

    def _calculate_structural_metrics(self, content, lines):
        """计算结构指标"""
        # 标题层级分布
        heading_levels = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                level = len(stripped.split(" ")[0])
                if 1 <= level <= 6:
                    heading_levels[level] += 1

        # 列表项计数
        list_items = sum(1 for line in lines if line.strip().startswith(("- ", "* ", "+ ")))

        # 代码块计数
        code_blocks = len(re.findall(r"```", content)) // 2  # 每对```算一个代码块

        # 表格计数
        table_lines = sum(1 for line in lines if "|" in line and not line.startswith("#"))
        tables = table_lines // 3 if table_lines >= 3 else 0  # 简化：每3行表格行算一个表格

        # 链接计数
        links = len(re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content))

        # 图片计数
        images = len(re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", content))

        return {
            "heading_distribution": heading_levels,
            "list_items": list_items,
            "code_blocks": code_blocks,
            "tables": tables,
            "links": links,
            "images": images,
            "structural_richness": self._calculate_structural_richness(
                heading_levels, list_items, code_blocks, tables
            ),
        }

    def _calculate_structural_richness(self, headings, lists, code_blocks, tables):
        """计算结构丰富度"""
        # 结构元素种类数
        element_types = sum(
            1 for count in [headings[2] + headings[3], lists, code_blocks, tables] if count > 0
        )

        # 结构元素总数
        element_count = sum(headings.values()) + lists + code_blocks + tables

        # 丰富度分数（0-100）
        richness = min(100, element_types * 15 + min(element_count, 10) * 2)
        return round(richness)

    def _calculate_technical_density(self, content, file_path):
        """计算技术术语密度"""
        # 技术术语列表（可根据需要扩展）
        technical_terms = [
            # 编程相关
            "API",
            "SDK",
            "CLI",
            "GUI",
            "UI",
            "UX",
            "JSON",
            "XML",
            "YAML",
            "HTTP",
            "HTTPS",
            "REST",
            "GraphQL",
            "WebSocket",
            "database",
            "server",
            "client",
            "framework",
            "library",
            "dependency",
            "deployment",
            "configuration",
            "authentication",
            "authorization",
            "encryption",
            "compilation",
            "debugging",
            "testing",
            # OpenClaw特定
            "Athena",
            "Codex",
            "OpenHuman",
            "AIplan",
            "queue",
            "task",
            "runner",
            "manifest",
            "orchestrator",
            "contract",
            "MAREF",
            "gstack",
            # 通用技术
            "algorithm",
            "architecture",
            "protocol",
            "interface",
            "implementation",
            "integration",
            "optimization",
            "performance",
            "scalability",
            "reliability",
        ]

        # 转换为小写用于匹配
        term_patterns = [
            re.compile(rf"\b{re.escape(term.lower())}\b", re.IGNORECASE) for term in technical_terms
        ]

        # 计算术语出现次数
        term_count = 0
        found_terms = []
        content_lower = content.lower()

        for i, pattern in enumerate(term_patterns):
            matches = pattern.findall(content_lower)
            if matches:
                term_count += len(matches)
                found_terms.append(technical_terms[i])

        # 计算总词数（近似）
        total_words = len(re.findall(r"\b\w+\b", content)) + len(
            re.findall(r"[\u4e00-\u9fff]", content)
        )

        # 术语密度
        density = (term_count / total_words * 100) if total_words > 0 else 0

        return {
            "technical_term_count": term_count,
            "unique_technical_terms": len(set(found_terms)),
            "technical_density_percent": round(density, 2),
            "found_terms_sample": list(set(found_terms))[:10],  # 只显示前10个
        }

    def _calculate_overall_score(self, metrics):
        """计算综合可读性分数（0-100）"""
        basic = metrics["basic_stats"]
        readability = metrics["readability_scores"]
        structural = metrics["structural_metrics"]
        technical = metrics["technical_density"]

        score = 0

        # 1. 句子长度分数（25%）
        avg_sentence_len = basic["avg_sentence_length"]
        if avg_sentence_len <= 15:
            score += 25
        elif avg_sentence_len <= 25:
            score += 20
        elif avg_sentence_len <= 35:
            score += 15
        elif avg_sentence_len <= 45:
            score += 10
        else:
            score += 5

        # 2. Flesch-Kincaid分数（25%）
        fk_score = readability["flesch_kincaid_adjusted"]
        score += fk_score * 0.25  # 直接按比例计算

        # 3. 结构丰富度分数（25%）
        structure_score = structural["structural_richness"]
        score += structure_score * 0.25

        # 4. 技术术语密度分数（25%）
        tech_density = technical["technical_density_percent"]
        if tech_density <= 5:
            score += 25  # 适合初学者
        elif tech_density <= 10:
            score += 20  # 适合中级
        elif tech_density <= 15:
            score += 15  # 适合高级
        elif tech_density <= 20:
            score += 10  # 适合专家
        else:
            score += 5  # 过于专业

        return min(100, round(score, 1))

    def _get_readability_level(self, score):
        """根据分数获取可读性等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "中等"
        elif score >= 60:
            return "及格"
        else:
            return "需要改进"

    def _generate_suggestions(self, metrics):
        """生成可读性改进建议"""
        suggestions = []
        basic = metrics["basic_stats"]
        readability = metrics["readability_scores"]
        structural = metrics["structural_metrics"]
        technical = metrics["technical_density"]

        # 句子长度建议
        avg_sentence_len = basic["avg_sentence_length"]
        if avg_sentence_len > 30:
            suggestions.append(f"平均句子长度较长({avg_sentence_len:.1f})，建议拆分长句")
        elif avg_sentence_len < 10:
            suggestions.append(f"平均句子长度较短({avg_sentence_len:.1f})，建议合并短句或增加细节")

        # Flesch-Kincaid建议
        fk_score = readability["flesch_kincaid_adjusted"]
        if fk_score < 60:
            suggestions.append(f"可读性分数较低({fk_score:.1f})，建议使用更简单的词汇和短句")

        # 结构建议
        headings = structural["heading_distribution"]
        if headings[2] + headings[3] < 2:
            suggestions.append("章节结构较简单，建议添加更多二级和三级标题")

        if structural["list_items"] < 3:
            suggestions.append("列表项较少，建议使用列表组织相关信息")

        # 技术术语建议
        tech_density = technical["technical_density_percent"]
        if tech_density > 15:
            suggestions.append(f"技术术语密度较高({tech_density:.1f}%)，建议添加术语解释或简化表达")
        elif tech_density < 2 and "guide" in metrics["file"].lower():
            suggestions.append("技术文档术语较少，建议增加关键技术概念的说明")

        return suggestions

    def add_issue(self, file_path, category, message):
        """添加问题记录"""
        self.issues.append(
            {"file": str(file_path), "category": category, "message": message, "severity": "INFO"}
        )

    def analyze_directory(self, directory):
        """分析目录中的所有Markdown文件"""
        directory = Path(directory)
        if not directory.exists():
            print(f"❌ 目录不存在: {directory}")
            return False

        md_files = list(directory.rglob("*.md"))
        if not md_files:
            print(f"📭 目录中未找到Markdown文件: {directory}")
            return True

        print(f"📁 分析目录: {directory}")
        print(f"📄 找到 {len(md_files)} 个Markdown文件")

        analyzed_count = 0
        for md_file in md_files:
            result = self.analyze_file(md_file)
            if result is not None:
                analyzed_count += 1

        print("\n📊 可读性分析完成:")
        print(f"  ✅ 成功分析: {analyzed_count}/{len(md_files)} 个文件")

        # 计算整体统计
        if self.metrics:
            total_score = sum(m.get("overall_score", 0) for m in self.metrics.values())
            avg_score = total_score / len(self.metrics)

            print(f"  📈 平均可读性分数: {avg_score:.1f}/100")

            # 分数分布
            levels = {"优秀": 0, "良好": 0, "中等": 0, "及格": 0, "需要改进": 0}
            for metrics in self.metrics.values():
                level = metrics.get("readability_level", "需要改进")
                if level in levels:
                    levels[level] += 1

            print("  📊 分数分布:")
            for level, count in levels.items():
                if count > 0:
                    percentage = (count / len(self.metrics)) * 100
                    print(f"    - {level}: {count}个 ({percentage:.1f}%)")

        return True

    def get_detailed_report(self):
        """获取详细分析报告"""
        if not self.metrics:
            return "# 文档可读性分析报告\n\n❌ 未分析任何文档"

        report = "# 文档可读性分析报告\n\n"
        report += "## 摘要\n"
        report += f"- 分析文件数: {len(self.metrics)}\n"

        total_score = sum(m.get("overall_score", 0) for m in self.metrics.values())
        avg_score = total_score / len(self.metrics) if self.metrics else 0
        report += f"- 平均可读性分数: {avg_score:.1f}/100\n"
        report += f"- 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # 按分数排序
        sorted_files = sorted(
            self.metrics.items(), key=lambda x: x[1].get("overall_score", 0), reverse=True
        )

        report += "## 详细分析\n\n"
        for file_path, metrics in sorted_files:
            rel_path = (
                Path(file_path).relative_to(Path.cwd())
                if Path(file_path).is_relative_to(Path.cwd())
                else file_path
            )
            report += f"### {rel_path} ({metrics['overall_score']}/100 - {metrics['readability_level']})\n\n"

            # 基础统计
            basic = metrics["basic_stats"]
            report += "**基础统计**:\n"
            report += f"- 总行数: {basic['total_lines']}\n"
            report += f"- 段落数: {basic['paragraphs']}\n"
            report += f"- 句子数: {basic['sentences']}\n"
            report += f"- 平均句子长度: {basic['avg_sentence_length']} (字符+单词)\n\n"

            # 可读性分数
            readability = metrics["readability_scores"]
            report += "**可读性分数**:\n"
            report += f"- 调整Flesch-Kincaid: {readability['flesch_kincaid_adjusted']} ({readability['readability_interpretation']})\n"
            report += f"- 调整Gunning Fog: {readability['gunning_fog_adjusted']}\n"
            report += f"- 调整Coleman-Liau: {readability['coleman_liau_adjusted']}\n\n"

            # 技术术语
            technical = metrics["technical_density"]
            report += "**技术术语**:\n"
            report += f"- 技术术语数: {technical['technical_term_count']}\n"
            report += f"- 唯一术语: {technical['unique_technical_terms']}\n"
            report += f"- 术语密度: {technical['technical_density_percent']}%\n"
            if technical["found_terms_sample"]:
                report += f"- 术语示例: {', '.join(technical['found_terms_sample'])}\n\n"

            # 生成建议
            suggestions = self._generate_suggestions(metrics)
            if suggestions:
                report += "**改进建议**:\n"
                for suggestion in suggestions:
                    report += f"- {suggestion}\n"

            report += "\n---\n\n"

        return report

    def get_summary_json(self):
        """获取JSON格式摘要"""
        if not self.metrics:
            return {}

        summary = {
            "analysis_date": datetime.now().isoformat(),
            "total_files_analyzed": len(self.metrics),
            "overall_score": 0,
            "score_distribution": {"优秀": 0, "良好": 0, "中等": 0, "及格": 0, "需要改进": 0},
            "file_scores": [],
        }

        total_score = 0
        for file_path, metrics in self.metrics.items():
            score = metrics.get("overall_score", 0)
            total_score += score
            level = metrics.get("readability_level", "需要改进")

            summary["score_distribution"][level] = summary["score_distribution"].get(level, 0) + 1

            summary["file_scores"].append(
                {
                    "file": str(
                        Path(file_path).relative_to(Path.cwd())
                        if Path(file_path).is_relative_to(Path.cwd())
                        else file_path
                    ),
                    "score": score,
                    "level": level,
                    "basic_stats": metrics["basic_stats"],
                }
            )

        summary["overall_score"] = round(total_score / len(self.metrics), 1) if self.metrics else 0

        return summary


def main():
    parser = argparse.ArgumentParser(description="分析文档可读性")
    parser.add_argument("--file", "-f", help="分析单个文件")
    parser.add_argument("--directory", "-d", help="分析目录（递归）")
    parser.add_argument("--output", "-o", help="输出报告文件")
    parser.add_argument("--json", action="store_true", help="输出JSON格式摘要")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    if not args.file and not args.directory:
        args.directory = "docs/"

    analyzer = DocumentReadabilityAnalyzer()

    success = True
    if args.file:
        success = analyzer.analyze_file(args.file) is not None
    elif args.directory:
        success = analyzer.analyze_directory(args.directory)

    # 生成报告
    report = analyzer.get_detailed_report()

    if not args.json:
        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)

    if args.json:
        summary = analyzer.get_summary_json()
        import json

        print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            if args.json:
                summary = analyzer.get_summary_json()
                json.dump(summary, f, indent=2, ensure_ascii=False)
            else:
                f.write(report)
        print(f"\n📝 报告已保存到: {args.output}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
