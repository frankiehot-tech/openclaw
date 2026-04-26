# MAREF生产系统故障排除指南

## 概述

本文档提供MAREF生产系统常见问题的诊断和解决方案。问题按优先级和紧急程度分类，提供逐步排查指导。

## 紧急故障（红色告警）

### 1. 系统无法启动

#### 症状
- 启动脚本执行失败
- 无MAREF相关进程运行
- 日志文件无新内容

#### 排查步骤
1. **检查环境配置**
   ```bash
   # 运行环境检查
   python3 check_production_environment.py
   
   # 检查配置文件
   ls -la config/production_config.py
   python3 -c "import sys; sys.path.insert(0, '.'); from config.production_config import DATABASE_CONFIG; print('数据库配置:', DATABASE_CONFIG)"
   ```

2. **检查日志**
   ```bash
   # 查看启动日志
   tail -f logs/startup_*.log
   
   # 查看错误日志
   grep -i "error\|exception\|traceback" logs/*.log | tail -20
   ```

3. **手动启动测试**
   ```bash
   # 单独测试集成环境
   python3 -c "
   import sys
   sys.path.insert(0, '.')
   try:
       from run_maref_daily_report import create_integration_environment
       env = create_integration_environment()
       print('✅ 集成环境创建成功')
       print(f'当前状态: {env.state_manager.current_state}')
   except Exception as e:
       print(f'❌ 集成环境创建失败: {e}')
       import traceback
       traceback.print_exc()
   "
   ```

#### 常见解决方案
- **数据库连接失败**: 检查数据库文件权限和路径
- **智能体初始化失败**: 检查ROMA智能体导入路径
- **配置文件错误**: 验证production_config.py格式

### 2. 数据库连接失败

#### 症状
- 数据库操作超时或失败
- 内存管理器初始化失败
- 状态获取返回错误

#### 排查步骤
1. **检查数据库文件**
   ```bash
   # 检查文件存在性和权限
   DB_PATH="/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
   ls -la "$DB_PATH"
   test -r "$DB_PATH" && echo "可读" || echo "不可读"
   test -w "$DB_PATH" && echo "可写" || echo "不可写"
   
   # 检查文件大小
   du -h "$DB_PATH"
   ```

2. **检查数据库完整性**
   ```bash
   sqlite3 "$DB_PATH" "PRAGMA integrity_check;"
   sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table';"
   ```

3. **测试数据库连接**
   ```python
   # 保存为 test_db_connection.py
   import sqlite3
   import sys
   
   db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
   
   try:
       conn = sqlite3.connect(db_path)
       cursor = conn.cursor()
       cursor.execute("SELECT COUNT(*) FROM memory_entries;")
       count = cursor.fetchone()[0]
       print(f"✅ 数据库连接成功，记录数: {count}")
       conn.close()
   except Exception as e:
       print(f"❌ 数据库连接失败: {e}")
       sys.exit(1)
   ```

#### 常见解决方案
- **权限问题**: `chmod 644 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db`
- **文件损坏**: 从备份恢复数据库
- **磁盘空间不足**: 清理日志文件或扩展磁盘空间

### 3. 智能体系统故障

#### 症状
- 智能体实例化失败
- 智能体无响应
- 协同决策异常

#### 排查步骤
1. **检查智能体状态**
   ```bash
   # 检查智能体导入
   python3 -c "
   import sys
   sys.path.insert(0, '.')
   try:
       from external.ROMA.hexagram_state_manager import HexagramStateManager
       print('✅ HexagramStateManager 导入成功')
   except Exception as e:
       print(f'❌ HexagramStateManager 导入失败: {e}')
   
   try:
       from maref_roma_integration import MAREF_AGENTS_AVAILABLE
       print(f'✅ MAREF智能体可用: {MAREF_AGENTS_AVAILABLE}')
   except Exception as e:
       print(f'❌ MAREF智能体检查失败: {e}')
   "
   ```

2. **测试智能体实例化**
   ```python
   # 保存为 test_agents.py
   import sys
   sys.path.insert(0, '.')
   
   try:
       from maref_roma_integration import create_integration_environment
       
       print("创建集成环境...")
       env = create_integration_environment()
       
       print("检查智能体...")
       agents = ['guardian', 'communicator', 'learner', 'explorer']
       for agent_name in agents:
           if hasattr(env, agent_name):
               agent = getattr(env, agent_name)
               print(f"✅ {agent_name}: {type(agent).__name__}")
           else:
               print(f"❌ {agent_name}: 缺失")
               
   except Exception as e:
       print(f"❌ 智能体测试失败: {e}")
       import traceback
       traceback.print_exc()
   ```

#### 常见解决方案
- **导入路径问题**: 检查external/ROMA目录结构
- **依赖包缺失**: 重新安装roma_dspy
- **配置错误**: 检查AGENT_CONFIG配置

## 性能问题（黄色告警）

### 1. 响应时间变慢

#### 症状
- 状态转换响应时间>0.5ms
- 智能体决策时间>10ms
- 数据库查询时间>15ms

#### 排查步骤
1. **检查当前性能**
   ```bash
   # 运行性能测试
   python3 -c "
   import time
   import sys
   sys.path.insert(0, '.')
   from run_maref_daily_report import create_integration_environment
   
   env = create_integration_environment()
   state_manager = env.state_manager
   
   # 测试状态转换性能
   start_time = time.perf_counter()
   for _ in range(100):
       current_state = state_manager.current_state
   elapsed = (time.perf_counter() - start_time) * 1000 / 100
   print(f'状态读取平均时间: {elapsed:.3f}ms')
   "
   ```

2. **分析系统资源**
   ```bash
   # 查看系统资源使用
   top -n 1 | grep -E "python|maref"
   
   # 检查内存使用
   ps aux | grep -E "run_maref_daily|maref_monitor" | grep -v grep | awk '{print $2, $4, $5}'
   
   # 检查磁盘I/O
   iostat -d 1 3
   ```

3. **检查数据库性能**
   ```bash
   # 检查数据库性能
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db <<EOF
   -- 检查查询性能
   EXPLAIN QUERY PLAN SELECT * FROM memory_entries WHERE entry_type='state_transition' ORDER BY timestamp DESC LIMIT 100;
   
   -- 检查表大小
   SELECT name, (pgsize/1024.0/1024.0) as size_mb FROM dbstat ORDER BY size_mb DESC LIMIT 5;
   
   -- 检查索引
   SELECT name FROM sqlite_master WHERE type='index';
   EOF
   ```

#### 常见解决方案
- **数据库优化**: 为常用查询创建索引
- **内存清理**: 清理旧的内存记录
- **配置调整**: 调整性能模式参数

### 2. 内存使用过高

#### 症状
- 内存使用率>70%
- 系统响应变慢
- 可能的内存泄漏

#### 排查步骤
1. **检查内存使用**
   ```bash
   # 检查Python进程内存
   ps aux | grep python | grep -v grep | sort -nrk 4 | head -5
   
   # 检查内存泄漏模式
   python3 -c "
   import sys
   sys.path.insert(0, '.')
   from maref_memory_manager import MAREFMemoryManager
   
   # 测试内存管理器
   manager = MAREFMemoryManager()
   print(f'内存管理器初始化完成')
   
   # 检查内存记录数量
   import sqlite3
   conn = sqlite3.connect('/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db')
   cursor = conn.cursor()
   cursor.execute('SELECT entry_type, COUNT(*) FROM memory_entries GROUP BY entry_type')
   for row in cursor.fetchall():
       print(f'{row[0]}: {row[1]} 条记录')
   conn.close()
   "
   ```

2. **检查日志轮转**
   ```bash
   # 检查日志文件大小
   find logs/ -name "*.log" -type f -exec du -h {} \; | sort -hr
   
   # 检查日志配置
   grep -A5 "LOGGING_CONFIG" config/production_config.py
   ```

#### 常见解决方案
- **清理旧数据**: 运行数据清理脚本
- **调整日志级别**: 减少DEBUG日志
- **优化内存配置**: 调整内存管理器参数

### 3. 日报生成失败

#### 症状
- 日报未按时生成
- 日报内容不完整
- 生成过程中出现错误

#### 排查步骤
1. **检查日报系统状态**
   ```bash
   # 检查cron任务
   crontab -l | grep -i maref
   
   # 检查日报生成日志
   tail -f logs/maref_daily_report_cron.log
   tail -f logs/maref_daily_report.log
   
   # 检查输出目录
   ls -la "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox/" | grep maref-daily
   ```

2. **手动测试日报生成**
   ```bash
   # 手动运行日报生成
   python3 run_maref_daily_report.py --mode production --verbose
   
   # 测试集成模式
   python3 run_maref_daily_report.py --mode integration --verbose
   ```

3. **检查依赖组件**
   ```bash
   # 检查所有依赖组件
   python3 -c "
   import sys
   sys.path.insert(0, '.')
   
   components = [
       ('run_maref_daily_report', '日报主模块'),
       ('maref_daily_reporter', '日报生成器'),
       ('maref_monitor', '监控器'),
       ('maref_roma_integration', '集成模块'),
   ]
   
   for module_name, description in components:
       try:
           __import__(module_name)
           print(f'✅ {description}: 导入成功')
       except Exception as e:
           print(f'❌ {description}: 导入失败 - {e}')
   "
   ```

#### 常见解决方案
- **cron任务配置**: 重新配置cron任务
- **输出目录权限**: 检查输出目录写入权限
- **数据源问题**: 检查数据源连接状态

## 数据问题

### 1. 数据不一致

#### 症状
- 状态转换记录不完整
- 智能体行动记录缺失
- 监控数据异常

#### 排查步骤
1. **检查数据完整性**
   ```bash
   # 检查关键数据表
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db <<EOF
   -- 检查各类型记录数量
   SELECT entry_type, COUNT(*) as count, 
          MIN(timestamp) as earliest,
          MAX(timestamp) as latest
   FROM memory_entries 
   GROUP BY entry_type 
   ORDER BY count DESC;
   
   -- 检查最近24小时数据
   SELECT entry_type, COUNT(*) 
   FROM memory_entries 
   WHERE timestamp >= datetime('now', '-24 hours')
   GROUP BY entry_type;
   EOF
   ```

2. **验证状态一致性**
   ```python
   # 保存为 check_state_consistency.py
   import sys
   sys.path.insert(0, '.')
   import sqlite3
   from datetime import datetime, timedelta
   
   db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
   
   conn = sqlite3.connect(db_path)
   cursor = conn.cursor()
   
   # 检查状态转换记录
   cursor.execute("""
   SELECT timestamp, content_json 
   FROM memory_entries 
   WHERE entry_type='state_transition'
   ORDER BY timestamp DESC
   LIMIT 10
   """)
   
   print("最近10次状态转换:")
   for row in cursor.fetchall():
       print(f"时间: {row[0]}, 内容: {row[1][:100]}...")
   
   conn.close()
   ```

#### 常见解决方案
- **数据库修复**: 运行数据库修复工具
- **数据同步**: 手动同步缺失数据
- **监控增强**: 增加数据一致性检查

## 预防性维护

### 定期检查清单

#### 每日检查
- [ ] 系统进程状态
- [ ] 日志文件大小
- [ ] 日报生成状态
- [ ] 数据库连接状态

#### 每周检查
- [ ] 性能指标趋势
- [ ] 磁盘空间使用
- [ ] 备份完整性
- [ ] 配置一致性

#### 每月检查
- [ ] 安全审计
- [ ] 性能基线更新
- [ ] 系统更新检查
- [ ] 文档更新

### 监控告警设置

#### 必须监控的指标
1. **系统健康**
   - 进程存活状态
   - 数据库连接状态
   - 智能体可用状态

2. **性能指标**
   - 响应时间（状态转换、智能体决策）
   - 资源使用（CPU、内存、磁盘）
   - 数据一致性指标

3. **业务指标**
   - 日报生成成功率
   - 预警准确率
   - 系统可用性

## 紧急恢复流程

### 1. 立即行动
1. 停止受影响的服务
2. 收集故障信息
3. 通知相关人员

### 2. 诊断分析
1. 分析日志文件
2. 检查系统状态
3. 确定根本原因

### 3. 恢复操作
1. 执行修复操作
2. 验证修复效果
3. 恢复服务运行

### 4. 事后分析
1. 编写故障报告
2. 制定预防措施
3. 更新文档和监控

## 联系支持

### 一级支持（紧急）
- **系统管理员**: [联系方式]
- **值班工程师**: [联系方式]

### 二级支持（技术）
- **开发团队**: [联系方式]
- **架构师**: [联系方式]

### 三级支持（业务）
- **产品负责人**: [联系方式]
- **业务负责人**: [联系方式]

---

**文档版本**: v1.0  
**创建日期**: 2026年4月16日  
**更新日期**: 2026年4月16日  
**负责人**: MAREF运维团队  
**状态**: 正式发布