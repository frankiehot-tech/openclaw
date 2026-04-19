# MAREF Coding审计系统集成指南

## 概述

本文档提供完整的MAREF Coding审计系统集成指南，帮助您将全域认知对齐和强制审计机制集成到现有项目中。

## 系统架构

```
├── maref_memory_manager.py      # 核心内存管理器
├── coding_audit_system.py       # Coding审计系统
├── maref_memory_integration.py  # 内存集成模块
├── demo_audit_system.py         # 完整演示脚本
├── test_audit_system.py         # 综合测试套件
└── run_maref_daily_report.py    # 集成示例
```

## 快速开始

### 1. 安装依赖
```bash
# 系统依赖
python3 -m pip install sqlite3
```

### 2. 基本集成
```python
from coding_audit_system import CodingAuditSystem, require_audit

# 初始化审计系统
audit_system = CodingAuditSystem()

# 注册您的coding agent
audit_system.register_agent(
    agent_id="your_agent_id",
    agent_type="your_agent_type",  # claude_code, vscode, trae_cn等
    capabilities=["code_generation", "refactoring"],
    metadata={"version": "1.0.0"}
)

# 包装您的代码生成函数
@audit_system.audit_decorator("your_agent_id", "your_agent_type")
def generate_code(prompt: str, context: dict = None) -> str:
    # 您的代码生成逻辑
    return generated_code
```

## 集成到现有MAREF系统

### 步骤1：修改MAREF主程序
```python
# 在现有的run_maref_daily_report.py中集成
from maref_memory_integration import init_memory_manager, wrap_state_manager_transition

# 初始化内存管理器
memory_manager = init_memory_manager()

# 包装现有组件
state_manager = wrap_state_manager_transition(state_manager, memory_manager)
```

### 步骤2：集成智能体行动记录
```python
from maref_memory_integration import record_agent_action, record_agent_decision

class YourAgent:
    agent_id = "your_agent"
    agent_type = "your_type"
    current_context = {}
    
    @record_agent_action(action_type="your_action")
    def perform_action(self, params):
        # 您的行动逻辑
        pass
    
    @record_agent_decision(decision_type="your_decision")
    def make_decision(self, options):
        # 您的决策逻辑
        pass
```

## 多平台Coding Agent集成

### Claude Code适配器
```python
# 为Claude Code创建适配器
claude_adapter = audit_system.create_claude_code_adapter("claude_agent_001")

@claude_adapter
def claude_generate(prompt: str, context: dict = None) -> str:
    # Claude Code生成的代码
    return f"# Claude Code生成\n# {prompt}"
```

### VSCode适配器
```python
# VSCode智能提示适配器
vscode_adapter = audit_system.create_vscode_adapter("vscode_agent_001")

# 使用适配器生成代码
code, context_id, record_id = vscode_adapter.generate_with_audit(
    prompt="测试VSCode生成",
    file_path="/path/to/file.js",
    project_path="/project"
)
```

### trae cn适配器（中文环境）
```python
# trae cn适配器（专为中文环境优化）
trae_adapter = audit_system.create_trae_cn_adapter("trae_cn_001")

@trae_adapter
def trae_generate(prompt: str, context: dict = None) -> str:
    # trae cn生成的代码（中文）
    return f"# trae cn生成\n# {prompt}\nprint('你好，世界！')"
```

### 自定义平台适配器
```python
# 为其他平台创建自定义适配器
def create_custom_adapter(audit_system, agent_id, platform_name):
    """创建自定义平台适配器"""
    audit_system.register_agent(
        agent_id=agent_id,
        agent_type=platform_name,
        capabilities=["code_generation"],
        metadata={"platform": platform_name, "custom": True}
    )
    
    def adapter_decorator(generation_func):
        @audit_system.audit_decorator(agent_id, platform_name)
        def wrapped_generate(prompt: str, context: dict = None, **kwargs):
            # 平台特定的预处理
            processed_prompt = f"[{platform_name}] {prompt}"
            return generation_func(processed_prompt, context, **kwargs)
        return wrapped_generate
    
    return adapter_decorator
```

## 审计策略配置

### 强制审计级别
```python
from coding_audit_system import GenerationReason

# 配置审计策略
AUDIT_POLICIES = {
    "critical_projects": ["/production", "/core"],
    "required_reasons": [
        GenerationReason.USER_REQUEST,
        GenerationReason.BUG_FIX,
        GenerationReason.REFACTORING
    ],
    "memory_required": True,  # 是否要求查询记忆
    "context_required": True,  # 是否要求提供上下文
}
```

### 项目特定策略
```python
def configure_project_audit(audit_system, project_path):
    """为特定项目配置审计策略"""
    if "/production/" in project_path:
        # 生产项目：严格审计
        audit_system.force_audit = True
        audit_system.require_memory = True
        audit_system.audit_trail_days = 90  # 保留90天审计记录
    elif "/test/" in project_path:
        # 测试项目：宽松审计
        audit_system.force_audit = False
        audit_system.audit_trail_days = 7
```

## 审计追踪和回滚

### 查询审计记录
```python
# 查询特定项目的审计记录
trail = audit_system.get_audit_trail(
    project_path="/my/project",
    hours=24,  # 过去24小时
    limit=50,  # 最多50条记录
    agent_id="claude_agent",  # 可选：特定agent
    file_path="/my/project/main.py"  # 可选：特定文件
)

# 分析审计记录
for entry in trail:
    print(f"时间: {entry['timestamp']}")
    print(f"Agent: {entry['agent_id']}")
    print(f"文件: {entry['file_path']}")
    print(f"原因: {entry['generation_reason']}")
    print(f"引用记忆: {len(entry['referenced_memories'])} 条")
    print(f"代码长度: {len(entry['generation_result']['code'])} 字符")
```

### 代码回滚
```python
# 回滚到特定审计版本
try:
    original_code, rollback_id = audit_system.rollback_code(
        audit_id="mem_cod_1234567890abcdef",  # 审计记录ID
        rollback_agent_id="admin",
        rollback_reason="bug_fix",
        # 可选：自定义回滚更改
        rollback_changes={
            "error_type": "syntax_error",
            "severity": "high",
            "fixed_by": "admin"
        }
    )
    print(f"✅ 回滚成功，恢复 {len(original_code)} 字符代码")
    print(f"回滚记录ID: {rollback_id}")
except Exception as e:
    print(f"❌ 回滚失败: {e}")
```

## 认知对齐验证

### 记忆查询验证
```python
def verify_cognitive_alignment(audit_entry):
    """验证认知对齐：检查生成的代码是否基于正确的记忆"""
    referenced_memories = audit_entry['referenced_memories']
    pre_context = audit_entry['pre_generation_context']
    
    # 检查是否有查询记忆
    if not referenced_memories:
        print("⚠️  警告：代码生成未引用任何记忆")
        return False
    
    # 检查记忆是否相关
    query_memories = pre_context.get('relevant_memories', [])
    memory_ids = [mem.get('id') for mem in query_memories]
    
    # 验证引用的记忆都在查询结果中
    for ref_mem in referenced_memories:
        if ref_mem not in memory_ids:
            print(f"⚠️  警告：引用了未查询的记忆: {ref_mem}")
            return False
    
    return True
```

### 自动对齐检查
```python
def auto_check_alignment(audit_system, project_path, hours=24):
    """自动检查项目的认知对齐情况"""
    trail = audit_system.get_audit_trail(
        project_path=project_path,
        hours=hours,
        limit=100
    )
    
    aligned = 0
    misaligned = 0
    
    for entry in trail:
        if verify_cognitive_alignment(entry):
            aligned += 1
        else:
            misaligned += 1
            print(f"❌ 认知未对齐: {entry['timestamp']} - {entry['file_path']}")
    
    alignment_rate = aligned / len(trail) if trail else 1.0
    print(f"📊 认知对齐率: {alignment_rate:.1%} ({aligned}/{len(trail)})")
    return alignment_rate >= 0.95  # 95%对齐率阈值
```

## 部署最佳实践

### 1. 分阶段部署
```python
# 第一阶段：只记录不强制
audit_system.force_audit = False
audit_system.log_only = True

# 第二阶段：测试模式
audit_system.force_audit = True
audit_system.test_mode = True  # 允许跳过某些检查

# 第三阶段：完全强制
audit_system.force_audit = True
audit_system.test_mode = False
```

### 2. 性能监控
```python
def monitor_audit_performance(audit_system):
    """监控审计系统性能"""
    stats = audit_system.get_audit_statistics()
    
    print("📈 审计系统性能报告:")
    print(f"  总审计记录: {stats['total_audits']}")
    print(f"  平均审计时间: {stats['avg_audit_time_ms']:.1f}ms")
    print(f"  记忆查询率: {stats['memory_query_rate']:.1%}")
    print(f"  认知对齐率: {stats['cognitive_alignment_rate']:.1%}")
    
    # 性能警告
    if stats['avg_audit_time_ms'] > 100:
        print("⚠️  警告：审计时间过长，考虑优化")
    if stats['memory_query_rate'] < 0.8:
        print("⚠️  警告：记忆查询率过低，可能影响认知对齐")
```

### 3. 数据备份和恢复
```python
# 定期备份审计数据库
def backup_audit_database(audit_system, backup_dir="/backup/audit"):
    """备份审计数据库"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/audit_backup_{timestamp}.db"
    
    # 复制数据库文件
    shutil.copy2(audit_system.memory_manager.db_path, backup_file)
    print(f"✅ 审计数据库已备份到: {backup_file}")
    
    # 保留最近7天的备份
    import glob
    import os
    
    backups = sorted(glob.glob(f"{backup_dir}/audit_backup_*.db"))
    if len(backups) > 7:
        for old_backup in backups[:-7]:
            os.remove(old_backup)
            print(f"🗑️  删除旧备份: {old_backup}")
```

## 故障排除

### 常见问题

#### 1. 审计失败：记忆查询超时
```python
# 解决方案：增加查询超时时间
audit_system.memory_manager.query_timeout = 10.0  # 10秒超时
```

#### 2. 数据库锁问题
```python
# 解决方案：使用连接池或重试机制
import sqlite3
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def safe_audit_code_generation(audit_system, **kwargs):
    """安全的代码生成审计（带重试）"""
    return audit_system.audit_code_generation(**kwargs)
```

#### 3. 内存使用过高
```python
# 解决方案：定期清理旧记录
def cleanup_old_audit_records(audit_system, days_to_keep=30):
    """清理超过指定天数的旧审计记录"""
    from datetime import datetime, timedelta
    
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    
    # 清理旧记录
    deleted = audit_system.memory_manager.cleanup_old_entries(
        entry_types=["CODE_GENERATION_AUDIT", "CODE_CONTEXT_QUERY"],
        before_date=cutoff_date
    )
    
    print(f"🗑️  清理 {deleted} 条超过 {days_to_keep} 天的旧审计记录")
```

## 完整示例

查看以下文件获取完整示例：
1. `demo_audit_system.py` - 完整功能演示
2. `test_audit_system.py` - 综合测试套件
3. `run_maref_daily_report.py` - MAREF系统集成示例

## 支持和维护

### 监控和报警
```python
# 设置监控和报警
def setup_audit_monitoring(audit_system):
    """设置审计系统监控"""
    
    # 每日报告
    def generate_daily_report():
        stats = audit_system.get_audit_statistics()
        trail = audit_system.get_audit_trail(hours=24, limit=1000)
        
        report = f"""
        📊 MAREF Coding审计系统日报
        时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        统计信息:
        - 总审计记录: {stats['total_audits']}
        - 成功审计: {stats['successful_audits']}
        - 失败审计: {stats['failed_audits']}
        - 平均时间: {stats['avg_audit_time_ms']:.1f}ms
        - 认知对齐率: {stats['cognitive_alignment_rate']:.1%}
        
        今日亮点:
        - 最多审计文件: {max(trail, key=lambda x: x.get('count', 0)) if trail else '无'}
        - 最活跃Agent: {max(set([e['agent_id'] for e in trail]), key=lambda x: [e['agent_id'] for e in trail].count(x)) if trail else '无'}
        """
        
        return report
    
    # 设置定时任务
    schedule.every().day.at("09:00").do(generate_daily_report)
```

### 更新和维护
```python
# 检查系统更新
def check_for_updates():
    """检查MAREF审计系统更新"""
    import requests
    
    try:
        response = requests.get("https://api.github.com/repos/your-repo/maref-audit/releases/latest")
        latest_version = response.json()['tag_name']
        
        current_version = "1.0.0"  # 从配置读取
        
        if latest_version != current_version:
            print(f"🔄 有新版本可用: {latest_version} (当前: {current_version})")
            print("运行以下命令更新:")
            print("  git pull origin main")
            print("  python3 -m pip install -r requirements.txt --upgrade")
    except Exception as e:
        print(f"⚠️  检查更新失败: {e}")
```

## 总结

MAREF Coding审计系统提供了完整的全域认知对齐解决方案：

1. **强制审计** - 确保所有代码生成都有完整记录
2. **记忆查询** - 生成前查询相关记忆确保认知对齐  
3. **多平台支持** - Claude Code、VSCode、trae cn等
4. **完整追溯** - 审计追踪和代码回滚
5. **非侵入式** - 装饰器和包装器模式

通过集成此系统，您可以：
- 确保所有coding agent认知对齐
- 实现代码生成的可审计和可追溯
- 快速回滚到之前的代码版本
- 监控和分析代码生成模式
- 提高代码质量和系统稳定性

开始集成吧！ 🚀
