# 首次团队培训实施指南

## 培训概览
- **目标**: 让团队成员快速上手文档工具链，理解质量标准
- **时长**: 2小时核心培训 + 1小时实操
- **对象**: 新团队成员和常规贡献者
- **时间**: 建议在文档自动化流水线部署后1周内开展

## 培训议程 (2小时)

### 第一部分：文档系统介绍 (30分钟)
1. **欢迎与目标设定** (5分钟)
   - 培训目标：掌握工具链使用，理解质量标准
   - 文档文化："文档优先"的开发理念

2. **文档系统架构** (10分钟)
   - MAREF三才六层分类模型
   - 6大文档目录：architecture/, technical/, audit/, user/, skills/, vendor/
   - 文档生命周期：创建→维护→归档

3. **质量指标体系** (15分钟)
   - 5大核心指标：链接有效性、格式合规率、可读性分数、完整性评分、文档更新率
   - 质量阈值配置 (`.document-quality-thresholds.yaml`)
   - 监控仪表板功能介绍

### 第二部分：工具链实战 (60分钟)
1. **核心工具演示** (20分钟)
   ```bash
   # 1. 格式检查工具
   python3 scripts/validate_document_format.py --file docs/user/getting-started.md --strict
   
   # 2. 链接检查工具  
   python3 scripts/check_document_links.py --file docs/user/user-guide.md
   
   # 3. 可读性分析工具
   python3 scripts/analyze_document_readability.py --file docs/architecture/system-design.md --json
   
   # 4. 完整性检查工具
   python3 scripts/check_document_completeness.py --file docs/user/team-training-plan.md --metrics
   ```

2. **自动化流水线介绍** (20分钟)
   - GitHub Actions工作流：`/.github/workflows/documentation-quality.yml`
   - 4个检查阶段：格式、链接、完整性、可读性
   - 质量门禁：PR检查、每日报告、每周分析
   - 监控仪表板：实时指标查看、告警通知

3. **实操演练：修复常见问题** (20分钟)
   ```bash
   # 案例1：修复格式问题
   python3 scripts/validate_document_format.py --file docs/user/claude-code-config.md --fix
   
   # 案例2：修复损坏链接
   python3 scripts/check_document_links.py --directory docs/user/ --repair
   
   # 案例3：生成质量报告
   python3 scripts/generate_document_quality_report.py --output docs/quality/training_report.json
   ```

### 第三部分：质量标准与最佳实践 (30分钟)
1. **文档质量标准** (15分钟)
   - 格式标准：标题层级、列表格式、代码块、表格
   - 内容标准：句子长度、术语密度、结构丰富度
   - 链接标准：内部引用、外部链接、锚点跳转
   - 元数据标准：最后更新日期、作者、版本

2. **最佳实践分享** (15分钟)
   - 创建新文档：使用模板、遵循命名规范
   - 更新文档：小步提交、质量检查、更新元数据
   - 维护文档：定期检查、修复问题、归档过时内容
   - 协作流程：PR评审、质量门禁、版本控制

## 实操练习 (1小时)

### 练习1：个人文档检查 (20分钟)
每位学员选择一个自己熟悉的文档，运行完整质量检查：
```bash
# 1. 选择文档
DOC_FILE="docs/user/your-chosen-document.md"

# 2. 运行完整检查链
python3 scripts/validate_document_format.py --file $DOC_FILE
python3 scripts/check_document_links.py --file $DOC_FILE
python3 scripts/analyze_document_readability.py --file $DOC_FILE --json
python3 scripts/check_document_completeness.py --file $DOC_FILE --metrics

# 3. 生成个人报告
python3 scripts/generate_document_quality_report.py --file $DOC_FILE --output "个人检查报告_$(date +%Y%m%d).json"
```

### 练习2：团队协作修复 (20分钟)
小组协作修复`docs/user/team-training-plan.md`中的问题：
```bash
# 1. 分析问题
python3 scripts/validate_document_format.py --file docs/user/team-training-plan.md --strict
python3 scripts/check_document_links.py --file docs/user/team-training-plan.md

# 2. 分工修复
# 小组A：修复格式问题
# 小组B：修复链接问题
# 小组C：优化可读性

# 3. 验证修复效果
python3 scripts/validate_document_format.py --file docs/user/team-training-plan.md
python3 scripts/check_document_links.py --file docs/user/team-training-plan.md
```

### 练习3：监控仪表板使用 (20分钟)
1. 启动监控仪表板：
   ```bash
   python3 scripts/documentation-monitor-dashboard.py --port 5002
   ```

2. 访问仪表板：http://127.0.0.1:5002
   - 查看5个核心指标
   - 分析告警信息
   - 查看历史趋势

3. API接口测试：
   ```bash
   curl http://127.0.0.1:5002/api/status
   curl http://127.0.0.1:5002/api/alerts
   curl http://127.0.0.1:5002/api/trends
   ```

## 考核与认证

### 考核标准
1. **知识测试** (20分)
   - 文档分类体系理解
   - 工具链功能掌握
   - 质量标准认知

2. **实操能力** (50分)
   - 独立完成文档质量检查 (20分)
   - 成功修复至少3个问题 (20分)
   - 生成有效质量报告 (10分)

3. **团队协作** (30分)
   - 参与团队修复任务 (15分)
   - 分享最佳实践 (15分)

### 认证要求
- **通过标准**: 总分≥70分
- **优秀认证**: 总分≥90分 + 完成扩展任务
- **扩展任务**:
  - 创建新文档模板
  - 优化现有工具脚本
  - 建立新的质量检查规则

## 培训材料

### 演示材料
1. **PPT演示稿** (已包含在培训计划中)
   - 文档系统架构图
   - 工具链工作流程图
   - 质量指标体系图

2. **实操演示脚本**
   ```bash
   # 完整演示脚本：scripts/training-demo.sh
   ./scripts/training-demo.sh
   ```

3. **参考文档**
   - [文档工具使用教程](documentation-tools-tutorial.md)
   - [文档写作指南](documentation-writing-guide.md)
   - [质量评估标准](../../technical/specifications/document-quality-standards.md)

### 学员材料
1. **培训手册** (可打印)
2. **快速参考卡** (工具命令速查)
3. **练习答案示例**

## 后续行动计划

### 培训后1周内
1. **实践作业**：每位学员提交一个文档改进PR
2. **答疑会议**：每周固定时间解答工具使用问题
3. **质量竞赛**：评选最佳文档改进案例

### 培训后1个月内
1. **进阶培训**：针对文档维护者和评审员
2. **工具优化**：收集反馈，改进工具链
3. **文化建立**：定期分享文档最佳实践

### 长期维护
1. **持续改进**：每季度更新培训内容
2. **知识传承**：建立师徒制，老带新
3. **质量监控**：定期回顾质量指标趋势

---

**培训准备清单**：
- [ ] 确认培训时间和参会人员
- [ ] 准备演示环境（Python 3.9+、Flask、依赖包）
- [ ] 打印培训材料
- [ ] 测试所有演示命令
- [ ] 准备实操练习的示例文档
- [ ] 设置监控仪表板演示环境

**培训联系人**：
- 主讲人：[团队负责人]
- 技术支持：[文档维护者]
- 问题反馈：[GitHub Issues]

**版本信息**：
- 创建日期：2026-04-19
- 版本：1.0
- 更新记录：首次创建