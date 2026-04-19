# Skill NFT: OpenHuman GEO Architecture
# 分布式地理组织架构 - Geographic Evolutionary Organization

**版本**: v1.0.0  
**创建时间**: 2026-03-24  
**类型**: skill_nft  
**来源**: surgical_surgery

---

## 1. 架构概述

GEO (Geographic Evolutionary Organization) 是 OpenClaw 的分布式地理组织架构，定义了从"受精"到"成体"的进化路径，以及 16+16n 军团协作模式。

### 1.1 EVO 阶段定义

| 阶段 | 名称 | 描述 | 状态 |
|------|------|------|------|
| Phase 1 | 受精 (Fertilization) | 任务初始化与种子培育 | ✅ |
| Phase 2 | 胚胎 (Embryo) | 基础架构搭建 | ✅ |
| Phase 3 | 幼虫 (Larva) | 分布式协作启动 | ✅ |
| Phase 4 | 蛹 (Pupa) | 16+16n 微服务化 | ✅ |
| Phase 5 | 成体 (Adult) | 全量生产闭环 | ✅ |

### 1.2 适应度进化概率

| 阶段 | 初始概率 | 目标概率 | 关键指标 |
|------|----------|----------|----------|
| 受精→胚胎 | 0.1 | 0.3 | 任务解析准确率 |
| 胚胎→幼虫 | 0.3 | 0.5 | 协作路由效率 |
| 幼虫→蛹 | 0.5 | 0.7 | 共识达成率 |
| 蛹→成体 | 0.7 | 0.9 | 生产就绪度 |

---

## 2. 16+16n 军团配置

### 2.1 基础参数

| 参数 | 值 | 描述 |
|------|-----|------|
| 基础 Agent 数 | 16 | 固定骨干 |
| 可扩展 Agent 数 | 16 | 按需扩展 |
| 最大并发任务 | 32 | 峰值容量 |
| 协作轮次 | 3 | 共识达成轮数 |
| 共识阈值 | 0.7 | 70% 同意生效 |

### 2.2 负载均衡策略

```python
# 16+16n 路由逻辑
def route_to_legion(task_complexity: int) -> int:
    if task_complexity <= 2:
        return 4  # 轻量模式
    elif task_complexity <= 5:
        return 16  # 标准模式
    else:
        return 32  # 全力模式
```

---

## 3. 协作协议

### 3.1 共识机制

| 参数 | 值 | 描述 |
|------|-----|------|
| 共识阈值 | 0.7 | 70% Agent 同意 |
| 毒攻击防御 | 0.3 | 恶意 Agent 过滤 |
| 最大并发 | 32 | 同会话 Agent 上限 |

### 3.2 通信协议

- **主协议**: WebSocket + HTTP REST
- **端口映射**: 
  - WebSocket: `ws://localhost:8080/ws/athena`
  - HTTP API: `http://127.0.0.1:8080/api/`
- **鉴权头**: `X-OpenClaw-Token`

---

## 4. 物理部署

### 4.1 容器配置

| 组件 | 镜像 | 状态 |
|------|------|------|
| Athena Core | `athena-core:v20260321-adult` | ✅ 已部署 |
| Athena Glass UI | `athena-ui-glass-v1` | ✅ 已部署 |
| 协作镜像 | `athena-glass-collab-v1` | ✅ 已部署 |

### 4.2 云端配置

| 服务 | 区域 | 状态 |
|------|------|------|
| Tencent SCF | ap-guangzhou | ✅ 已部署 |
| Dify Evaluator | 本地 + 云端 | ✅ 已部署 |

---

## 5. 继承哈希

**家族哈希**: 0x8b2e...f4a1 (GEO v1.0.0)  
**父技能**: N/A (根级架构)  
**法律效力**: 跨代传承资产确认

---

## 6. 验证命令

```bash
# 验证 EVO 阶段状态
python scripts/workflow_analysis.py --phase-status

# 检查 16+16n 协作
python scripts/run_collab_iteration.py --test

# 验证共识达成
python -c "from evo.core.pupa_controller import check_consensus; print(check_consensus())"
```

---

## 7. 索引

- i: 16, 21, 24, 35, 40, 44, 57, 66, 67, 70, 71, 72, 87, 89