# 迁移回滚计划 (Plan B)

## 迁移概述
- **迁移时间**: 2026-04-24
- **迁移目标**: 将 `/Volumes/1TB-M2/openclaw` 下的活跃组件迁移到 `/Volumes/1TB-M2/openclaw`
- **回滚策略**: 保留原始文件直到验证完成

## 迁移前备份清单

### 1. Claude Code 设置
```bash
# 源路径
/Volumes/1TB-M2/openclaw/claude-code-setup/

# 备份路径（迁移前自动创建）
/Volumes/1TB-M2/openclaw/backups/claude-code-setup-pre-migration/

# 回滚命令
cp -r /Volumes/1TB-M2/openclaw/backups/claude-code-setup-pre-migration /Volumes/1TB-M2/openclaw/claude-code-setup
```

### 2. OpenCode Athena
```bash
# 源路径
/Volumes/1TB-M2/openclaw/bin/opencode-athena

# 备份路径
/Volumes/1TB-M2/openclaw/backups/opencode-athena-pre-migration

# 回滚命令
cp /Volumes/1TB-M2/openclaw/backups/opencode-athena-pre-migration /Volumes/1TB-M2/openclaw/bin/opencode-athena
chmod +x /Volumes/1TB-M2/openclaw/bin/opencode-athena
```

## 迁移步骤与回滚点

### Phase 1: 创建备份
- [ ] 备份 `claude-code-setup/` → `backups/`
- [ ] 备份 `bin/opencode-athena` → `backups/`
- **回滚**: 直接删除备份，恢复原状

### Phase 2: 物理迁移
- [ ] 复制文件到新位置
- [ ] 验证新位置文件完整
- **回滚**: 删除新位置文件，恢复原始文件

### Phase 3: 更新路径引用
- [ ] 批量替换 `/Volumes/1TB-M2/openclaw` → `/Volumes/1TB-M2/openclaw`
- **回滚**: 使用 git checkout 或备份文件恢复

### Phase 4: 验证
- [ ] 测试所有功能
- **回滚**: 如果验证失败，执行完整回滚

## 完整回滚脚本

```bash
#!/bin/bash
# 完整回滚脚本 - 在验证失败时执行

echo "🔄 开始回滚..."

# 1. 恢复 claude-code-setup
if [ -d "/Volumes/1TB-M2/openclaw/backups/claude-code-setup-pre-migration" ]; then
    rm -rf /Volumes/1TB-M2/openclaw/claude-code-setup
    cp -r /Volumes/1TB-M2/openclaw/backups/claude-code-setup-pre-migration /Volumes/1TB-M2/openclaw/claude-code-setup
    echo "✅ claude-code-setup 已恢复"
fi

# 2. 恢复 opencode-athena
if [ -f "/Volumes/1TB-M2/openclaw/backups/opencode-athena-pre-migration" ]; then
    cp /Volumes/1TB-M2/openclaw/backups/opencode-athena-pre-migration /Volumes/1TB-M2/openclaw/bin/opencode-athena
    chmod +x /Volumes/1TB-M2/openclaw/bin/opencode-athena
    echo "✅ opencode-athena 已恢复"
fi

# 3. 恢复代码中的路径引用（使用git）
cd /Volumes/1TB-M2/openclaw
git checkout -- .
echo "✅ 代码路径引用已恢复"

echo "🎉 回滚完成"
```

## 验证检查点

| 检查点 | 验证内容 | 失败处理 |
|--------|----------|----------|
| CP1 | 文件完整性检查 | 重新复制 |
| CP2 | 脚本启动测试 | 检查路径配置 |
| CP3 | 功能端到端测试 | 执行回滚 |

## 紧急联系
- 如果回滚失败，保留所有备份文件
- 手动恢复关键路径引用
