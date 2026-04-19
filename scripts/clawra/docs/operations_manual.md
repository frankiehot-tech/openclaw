# MAREF生产系统运维手册

## 1. 系统概述

### 1.1 架构说明
MAREF（Multi-Agent Recursive Evolution Framework）是一个多智能体递归演进框架，基于64卦状态管理系统，实现智能体协同决策和状态转换。

**核心组件**:
- **状态管理器**: 管理64卦状态，强制格雷编码转换约束
- **内存管理器**: 记录状态转换、智能体行动、系统事件
- **智能体系统**: Guardian、Communicator、Learner、Explorer四个核心智能体
- **监控系统**: 实时采集性能指标和系统状态
- **预警系统**: 基于规则触发红/黄预警
- **日报系统**: 生成每日系统状态报告

### 1.2 组件关系图
```
用户请求 → 状态管理器 → 智能体协同 → 决策执行
      ↓                      ↓
监控器采集 → 预警引擎 → 通知系统
      ↓
内存管理器 → 数据库存储
      ↓
日报生成器 → 报告输出
```

### 1.3 数据流程图
1. **状态转换流程**:
   - 触发状态转换请求
   - 验证格雷编码约束（汉明距离=1）
   - 更新当前状态
   - 记录到内存数据库
   - 通知所有智能体

2. **监控数据流程**:
   - 定时采集系统指标
   - 计算控制熵H_c
   - 检查格雷编码合规性
   - 存储到内存数据库
   - 触发预警规则检查

## 2. 日常运维

### 2.1 健康检查

#### 每日检查项目
1. **系统健康状态**
   ```bash
   # 运行环境检查
   python3 check_production_environment.py
   ```
   - 预期结果: 所有检查通过
   - 关键指标: `ROMA_MAREF_AVAILABLE = True`

2. **进程状态检查**
   ```bash
   # 检查运行进程
   ps aux | grep -E "run_maref_daily|maref_monitor"
   
   # 检查进程数量
   pgrep -f "run_maref_daily" | wc -l
   pgrep -f "maref_monitor" | wc -l
   ```

3. **数据库健康检查**
   ```bash
   # 检查数据库连接
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "SELECT COUNT(*) FROM memory_entries;"
   
   # 检查表空间
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "SELECT name, (pgsize/1024.0/1024.0) as size_mb FROM dbstat ORDER BY size_mb DESC LIMIT 5;"
   ```

4. **日志检查**
   ```bash
   # 检查错误日志
   grep -i "error\|exception\|critical" logs/maref_production.log | tail -20
   
   # 检查预警日志
   grep -i "alert\|warning" logs/maref_production.log | tail -10
   ```

#### 每周检查项目
1. **磁盘空间检查**
   ```bash
   # 检查数据库文件大小
   du -h /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   
   # 检查日志目录大小
   du -h logs/
   ```

2. **性能指标趋势分析**
   ```bash
   # 提取关键性能指标
   python3 -c "
   import sqlite3
   conn = sqlite3.connect('/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db')
   cursor = conn.cursor()
   cursor.execute(\"SELECT timestamp, content FROM memory_entries WHERE entry_type='SYSTEM_EVENT' AND content LIKE '%performance_metrics%' ORDER BY timestamp DESC LIMIT 10;\")
   for row in cursor.fetchall():
       print(row[0], row[1][:100])
   conn.close()
   "
   ```

3. **备份完整性检查**
   ```bash
   # 检查最新备份文件
   ls -lh /backup/maref_*.db | tail -5
   
   # 验证备份可读性
   sqlite3 /backup/maref_latest.db "SELECT COUNT(*) FROM memory_entries LIMIT 1;"
   ```

### 2.2 日志管理

#### 日志文件位置
- **主日志**: `logs/maref_production.log`
- **启动日志**: `logs/startup_YYYYMMDD_HHMMSS.log`
- **监控日志**: `logs/monitor_YYYYMMDD_HHMMSS.log`
- **日报日志**: `logs/daily_report_YYYYMMDD.log`

#### 日志轮转策略
1. **自动轮转**: 日志文件达到100MB自动轮转
2. **保留策略**: 保留最近5个轮转文件
3. **压缩策略**: 超过30天的日志自动压缩为.gz格式
4. **清理策略**: 超过90天的日志自动删除

#### 关键日志信息解析

**正常日志示例**:
```
2026-04-15 08:30:00 - maref_monitor - INFO - 监控数据采集完成: system_metrics=..., maref_metrics=...
2026-04-15 08:30:01 - maref_memory_manager - DEBUG - 状态转换记录成功: 000001 → 000011 (ID: abc123)
2026-04-15 08:30:02 - HexagramStateManager - INFO - 状态转换成功: ䷗地雷复 → ䷪泽地萃 (原因: 测试转换)
```

**错误日志示例**:
```
2026-04-15 08:30:03 - maref_memory_manager - ERROR - 数据库连接失败: database is locked
2026-04-15 08:30:04 - HexagramStateManager - WARNING - 状态转换不符合格雷编码约束（汉明距离=2，必须为1）
2026-04-15 08:30:05 - maref_alert_engine - CRITICAL - 预警规则检查失败: division by zero
```

#### 日志查询技巧
```bash
# 实时查看日志
tail -f logs/maref_production.log

# 查看特定时间范围
awk '/2026-04-15 08:/, /2026-04-15 09:/' logs/maref_production.log

# 统计错误类型
grep -o "ERROR\|WARNING\|CRITICAL" logs/maref_production.log | sort | uniq -c

# 查找特定组件日志
grep "HexagramStateManager" logs/maref_production.log | tail -20

# 查找特定错误详情
grep -B5 -A5 "database is locked" logs/maref_production.log

# 使用日志管理脚本
./manage_maref_logs.sh --action status    # 查看日志状态
./manage_maref_logs.sh --action stats     # 查看统计信息
./manage_maref_logs.sh --action rotate    # 手动轮转日志
./manage_maref_logs.sh --action cleanup --days 90  # 清理90天前的日志
```

### 2.3 备份策略

#### 数据库备份
1. **每日自动备份**
   ```bash
   # 使用备份脚本（推荐）
   ./backup_maref_production.sh --mode daily
   
   # 或手动执行
   ./backup_maref_production.sh --mode daily --backup-dir /backup/maref --verbose
   ```

2. **备份验证**
   ```bash
   # 验证备份文件完整性
   sqlite3 $BACKUP_FILE "PRAGMA integrity_check;"
   
   # 验证表结构
   sqlite3 $BACKUP_FILE "SELECT COUNT(*) FROM memory_entries;"
   ```

3. **备份轮转**
   - 保留最近7天每日备份
   - 保留最近4周每周备份
   - 保留最近3个月每月备份
   - 超过保留期限的备份自动删除

#### 配置文件备份
1. **配置备份策略**
   ```bash
   # 备份配置文件
   CONFIG_BACKUP="/backup/maref/config_$(date +%Y%m%d).tar.gz"
   tar -czf $CONFIG_BACKUP config/production_config.py config/layer_config.py config/persona_config.py
   ```

2. **备份频率**
   - 配置变更时立即备份
   - 每周完整备份一次
   - 保留最近10个配置备份

#### 备份查看和管理
```bash
# 查看可用备份
ls -lh /backup/maref/maref_memory_*.db | tail -10

# 查看备份元数据
cat /backup/maref/backup_metadata.json | python3 -m json.tool

# 验证备份完整性
./backup_maref_production.sh --mode daily --verbose
```

#### 恢复流程
1. **数据库恢复**
   ```bash
   # 停止服务
   ./stop_maref_production.sh
   
   # 恢复数据库
   cp /backup/maref/maref_memory_20260415.db /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   
   # 启动服务
   ./start_maref_production.sh
   ```

2. **配置文件恢复**
   ```bash
   # 恢复配置文件
   tar -xzf /backup/maref/config_20260415.tar.gz -C /
   
   # 重启服务使配置生效
   ./stop_maref_production.sh
   ./start_maref_production.sh
   ```

## 3. 故障处理

### 3.1 常见问题

#### 问题1: 数据库连接失败
**症状**:
- 日志中出现 "database is locked" 或 "unable to open database file"
- 状态转换记录失败
- 监控数据无法存储

**解决方案**:
1. **检查文件权限**
   ```bash
   ls -l /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   chmod 644 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   ```

2. **检查文件锁**
   ```bash
   fuser /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   # 如果锁定，重启相关进程
   ```

3. **数据库修复**
   ```bash
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "PRAGMA integrity_check;"
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "VACUUM;"
   ```

#### 问题2: 智能体初始化失败
**症状**:
- `ROMA_MAREF_AVAILABLE = False`
- 智能体实例化时报错
- 集成环境创建失败

**解决方案**:
1. **检查导入路径**
   ```bash
   python3 -c "import sys; sys.path.insert(0, '.'); from external.ROMA.hexagram_state_manager import HexagramStateManager; print('导入成功')"
   ```

2. **检查依赖包**
   ```bash
   python3 -c "import dspy; print(f'dspy版本: {dspy.__version__}')"
   ```

3. **重启服务**
   ```bash
   ./stop_maref_production.sh
   sleep 5
   ./start_maref_production.sh
   ```

#### 问题3: 内存泄漏
**症状**:
- 内存使用持续增长
- 系统响应变慢
- 最终进程崩溃

**解决方案**:
1. **监控内存使用**
   ```bash
   # 查看进程内存
   ps aux | grep -E "run_maref_daily|maref_monitor" | grep -v grep | awk '{print $2, $4, $11}'
   
   # 查看内存趋势
   top -pid $(pgrep -f "run_maref_daily")
   ```

2. **重启服务释放内存**
   ```bash
   # 计划重启
   ./stop_maref_production.sh
   sleep 10
   ./start_maref_production.sh
   ```

3. **内存分析**
   ```bash
   # 使用内存分析工具
   python3 -m memray run run_maref_daily_report.py --mode production
   ```

### 3.2 应急流程

#### 服务重启流程
1. **正常重启**
   ```bash
   ./stop_maref_production.sh
   sleep 10
   ./start_maref_production.sh
   ```

2. **强制重启**
   ```bash
   # 强制停止
   pkill -9 -f "run_maref_daily"
   pkill -9 -f "maref_monitor"
   
   # 清理残留
   rm -f /tmp/maref_*.lock
   
   # 重新启动
   ./start_maref_production.sh
   ```

#### 数据恢复流程
1. **确认问题范围**
   ```bash
   # 检查数据完整性
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "PRAGMA quick_check;"
   ```

2. **选择恢复点**
   ```bash
   # 查看可用备份
   ls -lh /backup/maref/maref_memory_*.db | tail -10
   ```

3. **执行恢复**
   ```bash
   # 停止服务
   ./stop_maref_production.sh
   
   # 备份当前状态
   cp /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db.bak
   
   # 恢复备份
   cp /backup/maref/maref_memory_20260414.db /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   
   # 启动服务
   ./start_maref_production.sh
   ```

#### 回滚操作指南
1. **配置回滚**
   ```bash
   # 恢复旧配置
   tar -xzf /backup/maref/config_20260414.tar.gz -C /
   
   # 重启服务
   ./stop_maref_production.sh
   ./start_maref_production.sh
   ```

2. **代码回滚**
   ```bash
   # 使用git回滚
   git log --oneline -10
   git reset --hard <commit_hash>
   
   # 重启服务
   ./stop_maref_production.sh
   ./start_maref_production.sh
   ```

## 4. 性能优化

### 4.1 监控指标

#### 关键性能指标
1. **响应时间**
   - 状态转换响应时间: <0.5ms
   - 智能体决策时间: <5ms
   - 数据库查询时间: <10ms

2. **吞吐量**
   - 状态转换吞吐量: >100转换/秒
   - 监控数据采集: >1000指标/分钟
   - 内存记录: >1000条目/秒

3. **资源使用**
   - 内存使用率: <80%
   - CPU使用率: <70%
   - 磁盘使用率: <85%

#### 告警阈值设置
```python
# 在config/production_config.py中配置
PERFORMANCE_THRESHOLDS = {
    "state_transition_time_ms": 0.5,
    "agent_decision_time_ms": 5,
    "database_query_time_ms": 10,
    "memory_usage_percent": 80,
    "cpu_usage_percent": 70,
    "disk_usage_percent": 85,
    "throughput_state_transitions": 100,
}
```

#### 优化建议
1. **数据库优化**
   - 确保索引正确创建
   - 定期执行VACUUM
   - 调整cache_size参数
   - 使用WAL模式

2. **内存管理优化**
   - 调整entry_ttl_days减少数据量
   - 启用performance_mode
   - 增加缓存大小

3. **智能体参数调优**
   - 调整智能体决策频率
   - 优化状态同步机制
   - 调整互补对激活条件

### 4.2 调优指南

#### 数据库优化
1. **索引优化**
   ```sql
   -- 创建常用查询索引
   CREATE INDEX IF NOT EXISTS idx_memory_entries_timestamp ON memory_entries(timestamp);
   CREATE INDEX IF NOT EXISTS idx_memory_entries_entry_type ON memory_entries(entry_type);
   CREATE INDEX IF NOT EXISTS idx_memory_entries_source_agent ON memory_entries(source_agent);
   ```

2. **查询优化**
   ```python
   # 使用参数化查询
   cursor.execute("SELECT * FROM memory_entries WHERE entry_type = ? AND timestamp > ?", (entry_type, start_time))
   
   # 限制返回行数
   cursor.execute("SELECT * FROM memory_entries ORDER BY timestamp DESC LIMIT 100")
   ```

3. **连接池优化**
   ```python
   # 在内存管理器配置中
   MEMORY_MANAGER_CONFIG = {
       "max_connections": 20,  # 增加连接数
       "cache_size": 2000,     # 增加缓存大小
       "timeout": 30,          # 增加超时时间
   }
   ```

#### 内存管理优化
1. **缓存策略优化**
   ```python
   # 调整缓存大小
   memory_manager = MAREFMemoryManager(
       memory_dir="/Volumes/1TB-M2/openclaw/memory/maref",
       performance_mode=True,
       cache_size=5000  # 增加缓存条目数
   )
   ```

2. **数据清理优化**
   ```python
   # 调整数据保留策略
   MEMORY_MANAGER_CONFIG = {
       "entry_ttl_days": 7,  # 减少保留天数
       "auto_cleanup": True,
       "cleanup_batch_size": 1000,
   }
   ```

3. **批量操作优化**
   ```python
   # 使用批量插入
   memory_manager.bulk_insert_entries(entries)
   
   # 异步写入
   memory_manager.async_record_state_transition(from_state, to_state, trigger_agent)
   ```

#### 智能体参数调优
1. **决策频率调整**
   ```python
   # 调整智能体决策间隔
   AGENT_CONFIG = {
       "guardian_check_interval": 60,    # 60秒检查一次
       "communicator_sync_interval": 30,  # 30秒同步一次
       "learner_update_interval": 300,   # 5分钟更新一次
       "explorer_scan_interval": 600,    # 10分钟扫描一次
   }
   ```

2. **状态同步优化**
   ```python
   # 优化状态同步机制
   STATE_SYNC_CONFIG = {
       "sync_timeout": 5,      # 5秒超时
       "retry_count": 3,       # 重试3次
       "batch_size": 10,       # 批量同步10个状态
   }
   ```

3. **互补对激活优化**
   ```python
   # 调整互补对激活条件
   COMPLEMENTARY_PAIR_CONFIG = {
       "activation_threshold": 0.7,      # 置信度阈值
       "cooldown_period": 300,           # 冷却时间5分钟
       "max_activations_per_hour": 12,   # 每小时最多激活12次
   }
   ```

## 5. 安全指南

### 5.1 访问控制

#### 权限管理
1. **文件权限设置**
   ```bash
   # 数据库文件权限
   chmod 640 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   chown appuser:appgroup /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   
   # 配置文件权限
   chmod 600 config/production_config.py
   chown appuser:appgroup config/production_config.py
   
   # 日志文件权限
   chmod 644 logs/maref_production.log
   ```

2. **目录权限设置**
   ```bash
   # 主目录权限
   chmod 750 /Volumes/1TB-M2/openclaw/scripts/clawra
   chown -R appuser:appgroup /Volumes/1TB-M2/openclaw/scripts/clawra
   
   # 数据库目录权限
   chmod 700 /Volumes/1TB-M2/openclaw/memory/maref
   chown appuser:appgroup /Volumes/1TB-M2/openclaw/memory/maref
   ```

#### 审计日志
1. **启用操作审计**
   ```python
   # 在配置中启用审计
   SECURITY_CONFIG = {
       "enable_audit_log": True,
       "audit_events": [
           "state_transition",
           "agent_decision",
           "system_config_change",
           "data_access"
       ],
       "audit_retention_days": 365,
   }
   ```

2. **审计日志格式**
   ```json
   {
     "timestamp": "2026-04-15T08:30:00Z",
     "user": "appuser",
     "action": "state_transition",
     "resource": "HexagramStateManager",
     "details": {
       "from_state": "000001",
       "to_state": "000011",
       "trigger_agent": "coordinator"
     },
     "result": "success",
     "ip_address": "192.168.1.100"
   }
   ```

3. **审计日志查询**
   ```bash
   # 查询审计日志
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "SELECT * FROM audit_log WHERE action = 'state_transition' ORDER BY timestamp DESC LIMIT 10;"
   ```

#### 安全配置
1. **输入验证**
   ```python
   # 状态输入验证
   def validate_state_input(state: str) -> bool:
       if len(state) != 6:
           return False
       if not all(bit in '01' for bit in state):
           return False
       if state not in HEXAGRAMS:
           return False
       return True
   ```

2. **输出编码**
   ```python
   # 防止XSS攻击
   import html
   
   def safe_output(text: str) -> str:
       return html.escape(text)
   ```

3. **SQL注入防护**
   ```python
   # 使用参数化查询
   cursor.execute("SELECT * FROM memory_entries WHERE entry_type = ?", (entry_type,))
   # 而不是: cursor.execute(f"SELECT * FROM memory_entries WHERE entry_type = '{entry_type}'")
   ```

### 5.2 数据安全

#### 数据加密
1. **敏感数据加密**
   ```python
   import hashlib
   from cryptography.fernet import Fernet
   
   # 加密敏感数据
   def encrypt_sensitive_data(data: str, key: bytes) -> str:
       fernet = Fernet(key)
       encrypted = fernet.encrypt(data.encode())
       return encrypted.decode()
   
   # 解密数据
   def decrypt_sensitive_data(encrypted_data: str, key: bytes) -> str:
       fernet = Fernet(key)
       decrypted = fernet.decrypt(encrypted_data.encode())
       return decrypted.decode()
   ```

2. **密钥管理**
   ```bash
   # 生成加密密钥
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   
   # 安全存储密钥
   echo "ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> .env
   chmod 600 .env
   ```

#### 备份安全
1. **备份加密**
   ```bash
   # 加密备份文件
   openssl enc -aes-256-cbc -salt -in maref_memory.db -out maref_memory.db.enc -pass pass:strongpassword
   
   # 解密备份文件
   openssl enc -aes-256-cbc -d -in maref_memory.db.enc -out maref_memory.db -pass pass:strongpassword
   ```

2. **备份传输安全**
   ```bash
   # 使用SCP安全传输
   scp -i ~/.ssh/id_rsa maref_memory.db.enc backup-server:/backup/
   
   # 使用SFTP
   sftp -i ~/.ssh/id_rsa user@backup-server <<< "put maref_memory.db.enc /backup/"
   ```

3. **备份存储安全**
   - 存储在多地理位置
   - 使用WORM（一次写入多次读取）存储
   - 定期验证备份完整性
   - 限制备份访问权限

#### 隐私保护
1. **数据脱敏**
   ```python
   # 敏感数据脱敏
   def anonymize_data(data: dict) -> dict:
       anonymized = data.copy()
       if 'user_id' in anonymized:
           anonymized['user_id'] = hash_data(anonymized['user_id'])
       if 'ip_address' in anonymized:
           anonymized['ip_address'] = anonymized['ip_address'][:7] + 'xxx'
       return anonymized
   
   def hash_data(data: str) -> str:
       return hashlib.sha256(data.encode()).hexdigest()[:16]
   ```

2. **数据保留策略**
   ```python
   # 配置数据保留期限
   DATA_RETENTION_CONFIG = {
       "user_data_days": 30,
       "system_logs_days": 90,
       "audit_logs_days": 365,
       "backup_files_days": 730,
   }
   ```

3. **数据清理**
   ```python
   # 自动清理过期数据
   def cleanup_expired_data():
       # 清理用户数据
       cleanup_user_data(retention_days=30)
       
       # 清理系统日志
       cleanup_system_logs(retention_days=90)
       
       # 清理审计日志
       cleanup_audit_logs(retention_days=365)
       
       # 清理备份文件
       cleanup_backup_files(retention_days=730)
   ```

---
**文档版本**: v1.0  
**更新日期**: 2026年4月15日  
**维护团队**: MAREF运维工作组  
**联系方式**: [运维团队邮箱]  
**紧急联系人**: [紧急联系电话]

**更新记录**:
- v1.0: 初始版本，基于生产部署准备计划创建