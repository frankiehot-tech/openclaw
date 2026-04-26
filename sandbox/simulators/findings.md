# Findings & Decisions
<!-- 
  WHAT: Your knowledge base for the task. Stores everything you discover and decide.
  WHY: Context windows are limited. This file is your "external memory" - persistent and unlimited.
  WHEN: Update after ANY discovery, especially after 2 view/browser/search operations (2-Action Rule).
-->

## Requirements
<!-- 
  WHAT: What the user asked for, broken down into specific requirements.
  WHY: Keeps requirements visible so you don't forget what you're building.
  WHEN: Fill this in during Phase 1 (Requirements & Discovery).
-->
- 完成64卦状态系统的完整实现（Phase 22优化）
- 设计MAREF沙箱环境架构（任务#28）
- 实现超稳定性约束（格雷编码、质量边界、转换速率）
- 集成控制论反馈（PID控制器）
- 支持多种演化策略（贪心、模拟退火、遗传算法）
- 提供完整监控和报告功能
- 实现RESTful API和Python SDK
- 准备生产环境部署

## Research Findings
<!-- 
  WHAT: Key discoveries from web searches, documentation reading, or exploration.
  WHY: Multimodal content (images, browser results) doesn't persist. Write it down immediately.
  WHEN: After EVERY 2 view/browser/search operations, update this section (2-Action Rule).
-->
- 64卦系统使用6位二进制表示，每个位对应一个质量维度
- 河图10态（INITIAL、AST_PARSED、DIMENSION_ASSESSING等）映射到64卦
- 格雷编码约束确保状态转换汉明距离为1，满足超稳定性
- PID反馈控制：控制信号 = Kp×质量误差 + Ki×累积误差 + Kd×误差变化率
- 异步质量评估可以将开销从1.5%降低到0.3%（目标）
- 卦象缓存机制包括：汉明距离矩阵、最短路径矩阵、河图映射缓存
- 模拟退火策略允许暂时质量下降以跳出局部最优解

## Technical Decisions
<!-- 
  WHAT: Architecture and implementation choices you've made, with reasoning.
  WHY: You'll forget why you chose a technology or approach. This table preserves that knowledge.
  WHEN: Update whenever you make a significant technical choice.
-->
| Decision | Rationale |
|----------|-----------|
| 使用Python 3.8+作为实现语言 | 开发效率高，生态丰富，适合快速原型开发 |
| 采用模块化架构：管理器、控制器、引擎、监控 | 职责分离，易于测试和维护 |
| 实现异步分析使用ThreadPoolExecutor | 简单有效，避免复杂的async/await改造 |
| 使用二进制字符串表示状态（6位） | 易于计算汉明距离，支持格雷编码约束 |
| 预计算所有64个状态的分析结果 | 牺牲存储空间换取计算性能，适合小规模状态空间 |
| 采用Flask作为RESTful API框架 | 轻量级，学习曲线平缓，与现有代码集成简单 |
| 使用JSON作为主要数据交换格式 | 人类可读，Python原生支持，适合配置文件 |

## Issues Encountered
<!-- 
  WHAT: Problems you ran into and how you solved them.
  WHY: Similar to errors in task_plan.md, but focused on broader issues (not just code errors).
  WHEN: Document when you encounter blockers or unexpected challenges.
-->
| Issue | Resolution |
|-------|------------|
| 状态转换违反格雷编码约束 | 修复候选状态生成逻辑，严格使用max_hamming_distance=1 |
| 质量评估中的类型错误（字符串与整数比较） | 添加显式类型转换和错误处理 |
| 测试中的导入错误（类名不匹配） | 统一使用正确的类名，调整导入语句 |
| 转换速率约束误报（时间间隔为0） | 添加time_since_last > 0条件检查 |

## Resources
<!-- 
  WHAT: URLs, file paths, API references, documentation links you've found useful.
  WHY: Easy reference for later. Don't lose important links in context.
  WHEN: Add as you discover useful resources.
-->
- 设计文档：`maref_sandbox_design.md`
- 工程计划：`/Volumes/1TB-M2/openclaw/.document_recycle_bin/next_phase_engineering_plan_20260419.md`
- 核心实现：`sandbox_manager.py`
- 状态管理器：`integrated_hexagram_state_manager.py`
- 集成测试：`test_sandbox_integration.py`
- 性能测试：`test_async_analysis.py`
- 系统测试：`test_integration_system.py`

## Visual/Browser Findings
<!-- 
  WHAT: Information you learned from viewing images, PDFs, or browser results.
  WHY: CRITICAL - Visual/multimodal content doesn't persist in context. Must be captured as text.
  WHEN: IMMEDIATELY after viewing images or browser results. Don't wait!
-->
- 无

---
<!-- 
  REMINDER: The 2-Action Rule
  After every 2 view/browser/search operations, you MUST update this file.
  This prevents visual information from being lost when context resets.
-->
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*