# Skill NFT: OpenHuman CSWDP Protocol
# 主权数字化工厂协议 - Cognitive Sovereignty With Distributed Protocol

**版本**: v1.0.0  
**创建时间**: 2026-03-24  
**类型**: skill_nft  
**来源**: surgical_surgery

---

## 1. 协议概述

CSWDP (Cognitive Sovereignty with Distributed Protocol) 是 OpenClaw 数字化工厂的核心协议体系，定义了 AI Agent 的主权边界、协作模式与安全硬化标准。

### 1.1 核心原则

| 原则 | 描述 | 索引 |
|------|------|------|
| 硬件资源分配 | Mac mini M4 (24GB): 系统基础(3GB) + Ollama/DeepSeek R1(8GB) + Gateway(2GB) + 蒸馏任务(4GB) | i: 3 |
| 无头化统治 | UI 瘫痪 > 300s 时自动切换为唯一合法具身终端 | i: 11 |
| 驱动劫持 | 强制维护 better-sqlite3 + FTS5 引擎毫秒级指纹锁定 | i: 12 |
| 三层执行链 | READ_ONLY / ANALYSIS_EXEC / MUTATION_EXEC | i: 13 |

### 1.2 五层 Agent Skill 设计模式

| 模式 | 状态 | 描述 |
|------|------|------|
| Inversion (采访者) | ✅ 激活 | 需求干预系统，物理资产改动时触发 |
| Tool Wrapper (包装器) | ✅ 激活 | M4 显存释放、FTS5 指纹校验 |
| Generator (生成器) | ✅ 激活 | val_bpb < 2.0 压缩目标 |
| Reviewer (审查器) | ✅ 激活 | ROI < 2 一票否决 |
| Orchestrator (编排器) | ✅ 激活 | 内存 > 90% 强制终止，Skill NFT 自动铸造 |

---

## 2. 物理路径锁定

| 参数 | 值 | 位置 |
|------|-----|------|
| 工作区 | `/Volumes/1TB-M2/openclaw` | 全局 |
| 配置目录 | `~/.openclaw/` | 用户目录 |
| Skills 库 | `skills/` | 工作区根目录 |
| 记忆库 | `memory/` | 工作区根目录 |
| MCP 组件 | `mcp/` | 工作区根目录 |

---

## 3. 成本熔断参数

| 阈值 | 值 | 描述 |
|------|-----|------|
| 每日硬限制 | ¥50 | wallet_guardian.py |
| 警告阈值 | ¥45 | 飞书 webhook 推送 |
| 单次迭代上限 | ¥5 | EVO 阶段熔断 |
| 16+16n 协作成本 | ¥2 | 军团模式成本控制 |

---

## 4. 性能目标

| 指标 | 目标值 | 熔断值 |
|------|--------|--------|
| 响应时间 | 11.0s | 15.0s |
| 并发连接数 | 32 | 50 |
| 单会话内存 | 200MB | 300MB |
| 内存警告 | 85% | 90% |

---

## 5. 继承哈希

**家族哈希**: 0x7a9f...e3d2 (CSWDP v1.0.0)  
**父技能**: N/A (根级协议)  
**法律效力**: 跨代传承资产确认

---

## 6. 验证命令

```bash
# 验证 CSWDP 激活状态
python scripts/agent_mode.py get

# 检查 cost guardian
python scripts/wallet_guardian.py --check

# 验证内存阈值
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

---

## 7. 索引

- i: 3, 11, 12, 13, 14, 16, 19, 21, 24, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44