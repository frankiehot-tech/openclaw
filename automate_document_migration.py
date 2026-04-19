#!/usr/bin/env python3
"""
OpenClaw文档自动迁移脚本

根据MAREF三才六层模型和document_migration_plan.md计划，
自动分类和迁移根目录下的.md文件到docs/目录对应位置。

功能：
1. 扫描根目录所有.md文件（排除docs/和.openclaw/目录）
2. 基于文件名特征和内容分析进行分类
3. 移动文件到对应目录，保留备份
4. 生成迁移报告和日志

使用方法：
python3 automate_document_migration.py [--dry-run] [--verbose] [--force]

作者：OpenClaw文档迁移团队
创建日期：2026-04-19
"""

import argparse
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("document_migration.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class DocumentClassifier:
    """基于MAREF三才六层模型的文档分类器"""

    def __init__(self):
        # 分类规则：关键词 -> 目标目录
        self.classification_rules = {
            # 架构文档 (architecture/)
            "architecture": {
                "keywords": [
                    "cognitive",
                    "dna",
                    "agent",
                    "architecture",
                    "design",
                    "系统设计",
                    "架构",
                    "设计",
                    "system",
                    "framework",
                    "marer",
                    "三才",
                    "模型",
                ],
                "target_dir": "architecture",
            },
            # 技术规范 (technical/specifications/)
            "specifications": {
                "keywords": [
                    "spec",
                    "specification",
                    "规范",
                    "接口",
                    "api",
                    "protocol",
                    "standard",
                    "标准",
                    "技术规范",
                    "specification",
                ],
                "target_dir": "technical/specifications",
            },
            # 部署指南 (technical/deployment/)
            "deployment": {
                "keywords": [
                    "deployment",
                    "deploy",
                    "部署",
                    "安装",
                    "配置",
                    "setup",
                    "install",
                    "环境配置",
                    "环境设置",
                    "staged",
                    "阶段部署",
                    "工程化部署",
                    "production",
                    "生产",
                    "rollback",
                    "回滚",
                ],
                "target_dir": "technical/deployment",
            },
            # 运维文档 (technical/operations/)
            "operations": {
                "keywords": [
                    "operation",
                    "运维",
                    "monitor",
                    "monitoring",
                    "监控",
                    "故障",
                    "troubleshoot",
                    "troubleshooting",
                    "backup",
                    "恢复",
                    "恢复",
                    "maintenance",
                    "维护",
                    "guide",
                    "指南",
                    "操作",
                    "操作指南",
                ],
                "target_dir": "technical/operations",
            },
            # 审计文档 (audit/YYYY-MM/)
            "audit": {
                "keywords": [
                    "audit",
                    "审计",
                    "report",
                    "报告",
                    "分析",
                    "analysis",
                    "检查",
                    "review",
                    "评估",
                    "evaluation",
                    "总结",
                    "summary",
                    "结论",
                    "conclusion",
                    "审计报告",
                    "分析报告",
                ],
                "target_dir": "audit",  # 具体年月目录由日期提取决定
            },
            # 用户文档 (user/)
            "user": {
                "keywords": [
                    "user",
                    "用户",
                    "guide",
                    "指南",
                    "使用",
                    "usage",
                    "getting-started",
                    "快速开始",
                    "配置",
                    "config",
                    "configuration",
                    "manual",
                    "手册",
                    "tutorial",
                    "教程",
                    "reference",
                    "参考",
                ],
                "target_dir": "user",
            },
            # 技能文档 (skills/)
            "skills": {
                "keywords": ["skill", "技能", "能力", "capability", "function", "功能"],
                "target_dir": "skills",
            },
        }

        # 日期正则表达式
        self.date_patterns = [
            r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})",  # YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD
            r"(\d{4})[-_]?(\d{2})",  # YYYY-MM, YYYY_MM
        ]

    def extract_date(self, filename):
        """从文件名中提取日期，返回YYYY-MM格式"""
        for pattern in self.date_patterns:
            match = re.search(pattern, filename)
            if match:
                if len(match.groups()) >= 2:
                    year = match.group(1)
                    month = match.group(2)
                    if len(month) == 2:
                        return f"{year}-{month}"
        return None

    def normalize_filename(self, filename):
        """标准化文件名：英文小写，短横线分隔"""
        # 移除扩展名
        name = os.path.splitext(filename)[0]

        # 替换下划线和中文字符
        name = name.replace("_", "-")
        name = name.replace(" ", "-")

        # 中文转换（简化版）
        chinese_to_pinyin = {
            "系统": "system",
            "设计": "design",
            "架构": "architecture",
            "审计": "audit",
            "报告": "report",
            "分析": "analysis",
            "指南": "guide",
            "部署": "deployment",
            "运维": "operations",
            "规范": "specification",
            "用户": "user",
            "技能": "skill",
            "文档": "document",
        }

        for ch, en in chinese_to_pinyin.items():
            name = name.replace(ch, en)

        # 转换为小写，移除重复短横线
        name = name.lower()
        name = re.sub(r"-+", "-", name)

        # 保留日期格式
        date = self.extract_date(filename)
        if date:
            # 在标准化名称中添加日期
            name_base = re.sub(r"\d{4}[-_]?\d{2}[-_]?\d{0,2}", "", name).strip("-")
            name = f"{name_base}-{date}" if name_base else date

        return f"{name}.md" if not name.endswith(".md") else name

    def classify(self, filepath):
        """分类文档文件，返回目标目录和标准化文件名"""
        filename = os.path.basename(filepath)
        logger.debug(f"分类文件: {filename}")

        # 读取文件前几行内容进行分析
        content_preview = ""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content_preview = f.read(5000)  # 读取前5000字符
        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="gbk") as f:
                    content_preview = f.read(5000)
            except:
                content_preview = ""

        filename_lower = filename.lower()
        content_lower = content_preview.lower()

        # 得分统计
        scores = {category: 0 for category in self.classification_rules}

        # 基于文件名评分
        for category, rule in self.classification_rules.items():
            for keyword in rule["keywords"]:
                if keyword.lower() in filename_lower:
                    scores[category] += 3  # 文件名匹配权重较高
                    logger.debug(f"  {filename}: 文件名匹配关键词 '{keyword}' -> {category}")

        # 基于内容评分
        for category, rule in self.classification_rules.items():
            for keyword in rule["keywords"]:
                if keyword.lower() in content_lower:
                    scores[category] += 1  # 内容匹配权重较低
                    logger.debug(f"  {filename}: 内容匹配关键词 '{keyword}' -> {category}")

        # 特殊规则：日期检测（审计报告通常有日期）
        date = self.extract_date(filename)
        if date:
            scores["audit"] += 2
            logger.debug(f"  {filename}: 检测到日期 {date} -> audit类别加分")

        # 选择最高分
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        # 如果最高分太低（小于2），则归为"未分类"
        if best_score < 2:
            best_category = "unclassified"
            target_dir = "unclassified"
        else:
            target_dir = self.classification_rules[best_category]["target_dir"]

        # 标准化文件名
        normalized_name = self.normalize_filename(filename)

        # 对于审计文档，需要确定年月目录
        final_target_dir = target_dir
        if best_category == "audit" and date:
            # 使用提取的日期创建年月目录
            year_month = date[:7] if len(date) >= 7 else "unknown-date"
            final_target_dir = os.path.join("audit", year_month)
        elif best_category == "audit" and not date:
            # 没有日期，使用文件修改时间的年月
            mtime = os.path.getmtime(filepath)
            mod_date = datetime.fromtimestamp(mtime)
            year_month = mod_date.strftime("%Y-%m")
            final_target_dir = os.path.join("audit", year_month)

        return {
            "original_path": filepath,
            "original_name": filename,
            "normalized_name": normalized_name,
            "category": best_category,
            "target_dir": final_target_dir,
            "score": best_score,
            "date_extracted": date,
        }


class DocumentMigrator:
    """文档迁移器"""

    def __init__(self, project_root, dry_run=False, verbose=False, force=False):
        self.project_root = Path(project_root)
        self.docs_root = self.project_root / "docs"
        self.dry_run = dry_run
        self.verbose = verbose
        self.force = force
        self.classifier = DocumentClassifier()

        # 迁移统计
        self.stats = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "by_category": {}}

        # 迁移记录
        self.migration_log = []

    def scan_md_files(self):
        """扫描根目录下的.md文件（仅根目录一级，排除docs/和.openclaw/目录）"""
        md_files = []

        # 必须保留在根目录的文件（不迁移）
        exclude_files = {
            "README.md",
            "CLAUDE.md",
            ".gitignore",
            "task_plan.md",
            "progress.md",
            "findings.md",  # planning-with-files技能文件
        }

        # 只扫描根目录（一级目录）
        for item in os.listdir(self.project_root):
            # 跳过目录，只处理文件
            item_path = self.project_root / item
            if not item_path.is_file():
                continue

            # 只处理.md文件
            if not item.lower().endswith(".md"):
                continue

            # 排除保留文件
            if item in exclude_files:
                logger.debug(f"跳过保留文件: {item}")
                continue

            # 排除已经在docs目录下的文件（通过符号链接检查）
            try:
                # 检查文件是否在docs目录中（可能是符号链接）
                real_path = item_path.resolve()
                if real_path.is_relative_to(self.docs_root):
                    logger.debug(f"跳过已在docs目录中的文件: {item}")
                    continue
            except:
                pass

            md_files.append(str(item_path))

        # 按文件名排序，便于处理
        md_files.sort()

        logger.info(f"在根目录找到 {len(md_files)} 个.md文件需要迁移")
        for file in md_files[:20]:  # 显示前20个文件
            logger.debug(f"  - {os.path.basename(file)}")
        if len(md_files) > 20:
            logger.debug(f"  ... 还有 {len(md_files) - 20} 个文件")

        return md_files

    def ensure_directory(self, directory):
        """确保目录存在"""
        if not os.path.exists(directory):
            logger.info(f"创建目录: {directory}")
            if not self.dry_run:
                os.makedirs(directory, exist_ok=True)

    def migrate_file(self, file_info):
        """迁移单个文件"""
        original_path = file_info["original_path"]
        target_dir_rel = file_info["target_dir"]
        normalized_name = file_info["normalized_name"]

        # 构建目标路径
        target_dir = self.docs_root / target_dir_rel
        target_path = target_dir / normalized_name

        # 确保目标目录存在
        self.ensure_directory(target_dir)

        # 检查目标文件是否已存在
        if target_path.exists() and not self.force:
            logger.warning(f"目标文件已存在: {target_path}")
            # 添加后缀避免冲突
            base_name = os.path.splitext(normalized_name)[0]
            counter = 1
            while target_path.exists():
                new_name = f"{base_name}-{counter}.md"
                target_path = target_dir / new_name
                counter += 1
            logger.info(f"重命名以避免冲突: {normalized_name} -> {target_path.name}")

        # 执行迁移
        logger.info(f"迁移: {original_path} -> {target_path}")

        if not self.dry_run:
            try:
                # 复制文件（保留原始文件作为备份）
                shutil.copy2(original_path, target_path)

                # 记录迁移
                self.migration_log.append(
                    {
                        "original": original_path,
                        "target": str(target_path),
                        "category": file_info["category"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                return True
            except Exception as e:
                logger.error(f"迁移失败 {original_path}: {e}")
                return False
        else:
            # 模拟模式下，只记录
            self.migration_log.append(
                {
                    "original": original_path,
                    "target": str(target_path),
                    "category": file_info["category"],
                    "timestamp": datetime.now().isoformat(),
                    "dry_run": True,
                }
            )
            return True

    def generate_report(self):
        """生成迁移报告"""
        report_path = self.project_root / "document_migration_report.md"

        report_content = f"""# 文档迁移报告

## 迁移概览
- **执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **模式**: {'模拟运行 (dry-run)' if self.dry_run else '实际迁移'}
- **总文件数**: {self.stats['total']}
- **成功迁移**: {self.stats['migrated']}
- **跳过**: {self.stats['skipped']}
- **失败**: {self.stats['failed']}

## 分类统计
"""

        for category, count in self.stats["by_category"].items():
            report_content += f"- **{category}**: {count} 个文件\n"

        report_content += "\n## 详细迁移记录\n"
        report_content += "| 原文件 | 目标文件 | 分类 | 状态 |\n"
        report_content += "|--------|----------|------|------|\n"

        for log_entry in self.migration_log:
            status = "✅ 成功" if not log_entry.get("dry_run", False) else "🔍 模拟"
            report_content += f"| {log_entry['original']} | {log_entry['target']} | {log_entry['category']} | {status} |\n"

        report_content += f"\n## 未分类文件\n"

        # 查找未分类文件
        unclassified_files = []
        for log_entry in self.migration_log:
            if log_entry["category"] == "unclassified":
                unclassified_files.append(log_entry["original"])

        if unclassified_files:
            for file in unclassified_files:
                report_content += f"- {file}\n"
        else:
            report_content += "无未分类文件\n"

        report_content += f"\n---\n**生成时间**: {datetime.now().isoformat()}\n"
        report_content += "**工具**: automate_document_migration.py\n"

        if not self.dry_run:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"迁移报告已生成: {report_path}")
        else:
            logger.info("模拟运行报告:")
            print(report_content)

        return report_content

    def run(self):
        """执行文档迁移"""
        logger.info("开始文档迁移扫描...")

        # 扫描文件
        md_files = self.scan_md_files()
        self.stats["total"] = len(md_files)

        logger.info(f"找到 {self.stats['total']} 个.md文件需要分类迁移")

        if self.stats["total"] == 0:
            logger.info("没有需要迁移的文件")
            return

        # 分类和迁移
        for filepath in md_files:
            try:
                # 分类
                file_info = self.classifier.classify(filepath)

                # 更新统计
                category = file_info["category"]
                self.stats["by_category"][category] = self.stats["by_category"].get(category, 0) + 1

                logger.debug(f"分类结果: {filepath} -> {category} (分数: {file_info['score']})")

                # 迁移
                if category == "unclassified":
                    logger.warning(f"无法分类，跳过: {filepath}")
                    self.stats["skipped"] += 1
                    continue

                success = self.migrate_file(file_info)

                if success:
                    self.stats["migrated"] += 1
                    if self.verbose:
                        logger.info(
                            f"✅ 已处理: {filepath} -> {file_info['target_dir']}/{file_info['normalized_name']}"
                        )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ 处理失败: {filepath}")

            except Exception as e:
                logger.error(f"处理文件时出错 {filepath}: {e}")
                self.stats["failed"] += 1

        # 生成报告
        self.generate_report()

        # 总结
        logger.info("=" * 60)
        logger.info("文档迁移完成!")
        logger.info(f"总文件数: {self.stats['total']}")
        logger.info(f"成功迁移: {self.stats['migrated']}")
        logger.info(f"跳过: {self.stats['skipped']}")
        logger.info(f"失败: {self.stats['failed']}")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("这是模拟运行，实际文件未移动")
            logger.info("使用 --dry-run 参数查看分类结果，移除该参数执行实际迁移")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw文档自动迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际移动文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--force", "-f", action="store_true", help="强制覆盖已存在的目标文件")
    parser.add_argument("--project-root", default=".", help="项目根目录路径")

    args = parser.parse_args()

    # 设置详细日志
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 运行迁移器
    migrator = DocumentMigrator(
        project_root=args.project_root, dry_run=args.dry_run, verbose=args.verbose, force=args.force
    )

    migrator.run()


if __name__ == "__main__":
    main()
