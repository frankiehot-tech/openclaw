# 🌐 Athena Web Desktop 强制刷新操作指南

## 🔄 强制刷新方法

### 方法1: 浏览器强制刷新 (推荐)
1. **打开浏览器**: 访问 http://127.0.0.1:8080
2. **强制刷新快捷键**:
   - **Windows/Linux**: `Ctrl + F5` 或 `Ctrl + Shift + R`
   - **Mac**: `Cmd + Shift + R`
3. **清除浏览器缓存**:
   - 打开开发者工具 (F12)
   - 右键刷新按钮 → "清空缓存并硬性重新加载"

### 方法2: 浏览器控制台刷新
```javascript
// 在浏览器控制台中执行以下命令
location.reload(true);  // 强制刷新
localStorage.clear();   // 清除本地存储
sessionStorage.clear(); // 清除会话存储
```

### 方法3: 使用无痕/隐私模式
1. 打开浏览器的无痕/隐私模式
2. 访问 http://127.0.0.1:8080
3. 避免缓存干扰

## 🎯 验证修复效果

刷新后检查以下内容：
1. ✅ **队列状态**: 应该显示"运行中"而不是"手动保留"
2. ✅ **当前任务**: 应该显示"opencode_cli_optimization"
3. ✅ **错误消失**: "无法定位当前队列项"警告应该消失
4. ✅ **手动拉起**: 手动拉起按钮应该可以正常响应

## 🔧 如果问题仍然存在

如果强制刷新后问题仍然存在，请执行：
1. 重启Web服务器: `pkill -f athena_web_desktop_compat.py && python3 /Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py`
2. 等待30秒后重新访问
3. 如果仍然有问题，请联系技术支持
