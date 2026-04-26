# Athena Open Human 与 Claude Code Router 对齐配置方案

**生成时间**: 2026-04-07  
**基于报告**: /Volumes/1TB-M2/openclaw/claude-code-deployment-report.md  
**目标**: 实现Athena Open Human与Claude Code Router的深度集成

## 📋 集成概览

### **当前Claude Code部署状态**
- **版本**: Claude Code CLI v2.1.92, Router v2.0.0
- **环境**: macOS Sequoia (Apple Silicon)
- **配置**: 单一DeepSeek提供商，端口3000
- **状态**: 运行中，但配置较为基础

### **对齐目标**
1. **统一模型路由**: 将Athena的模型调用路由到Claude Code
2. **配置标准化**: 建立统一的配置管理
3. **性能优化**: 利用Claude Code的路由能力优化Athena性能
4. **监控集成**: 实现统一的监控和日志管理

## 🔧 核心配置方案

### **1. Claude Code Router 增强配置**

#### **配置文件**: `~/.claude-code-router/config.json`
```json
{
  "LOG": true,
  "LOG_LEVEL": "info",
  "HOST": "127.0.0.1",
  "PORT": 3000,
  "APIKEY": "athena-openhuman-integration-key",
  "API_TIMEOUT_MS": 300000,
  "NON_INTERACTIVE_MODE": false,
  
  "Providers": [
    {
      "name": "deepseek-primary",
      "api_base_url": "https://api.deepseek.com/chat/completions",
      "api_key": "$DEEPSEEK_API_KEY",
      "models": ["deepseek-chat", "deepseek-reasoner"],
      "priority": 1,
      "max_retries": 3,
      "timeout": 120000
    },
    {
      "name": "deepseek-backup",
      "api_base_url": "https://api.deepseek.com/chat/completions",
      "api_key": "$DEEPSEEK_BACKUP_KEY",
      "models": ["deepseek-chat"],
      "priority": 2,
      "max_retries": 2,
      "timeout": 90000
    },
    {
      "name": "ollama-local",
      "api_base_url": "http://localhost:11434/v1",
      "api_key": "",
      "models": ["llama3.2", "qwen2.5"],
      "priority": 3,
      "max_retries": 1,
      "timeout": 60000
    }
  ],
  
  "Router": {
    "default": "deepseek-primary,deepseek-chat",
    "background_tasks": "ollama-local,llama3.2",
    "reasoning_tasks": "deepseek-primary,deepseek-reasoner",
    "long_context": "deepseek-primary,deepseek-chat",
    "code_generation": "deepseek-primary,deepseek-chat",
    "document_analysis": "ollama-local,qwen2.5"
  },
  
  "Cache": {
    "enabled": true,
    "ttl": 3600,
    "max_size": 1000
  },
  
  "Metrics": {
    "enabled": true,
    "prometheus_port": 9090,
    "health_check": "/health"
  }
}
```

### **2. Athena Open Human 集成配置**

#### **配置文件**: `/Volumes/1TB-M2/openclaw/.openclaw/claude_code_integration.json`
```json
{
  "claude_code_integration": {
    "enabled": true,
    "base_url": "http://127.0.0.1:3000",
    "api_key": "athena-openhuman-integration-key",
    "timeout": 300,
    "retry_count": 3,
    
    "model_mapping": {
      "athena_default": {
        "provider": "deepseek-primary",
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 4000
      },
      "athena_reasoning": {
        "provider": "deepseek-primary", 
        "model": "deepseek-reasoner",
        "temperature": 0.3,
        "max_tokens": 8000
      },
      "athena_code": {
        "provider": "deepseek-primary",
        "model": "deepseek-chat",
        "temperature": 0.2,
        "max_tokens": 6000
      },
      "athena_background": {
        "provider": "ollama-local",
        "model": "llama3.2",
        "temperature": 0.5,
        "max_tokens": 2000
      }
    },
    
    "routing_strategy": {
      "fallback_enabled": true,
      "health_check_interval": 30,
      "circuit_breaker": {
        "failure_threshold": 5,
        "reset_timeout": 300
      }
    }
  }
}
```

### **3. 环境变量配置**

#### **Shell配置文件**: `~/.zshrc` 或 `~/.bashrc`
```bash
# Claude Code Router 集成配置
export DEEPSEEK_API_KEY="your-actual-deepseek-key"
export DEEPSEEK_BACKUP_KEY="your-backup-deepseek-key"
export CLAUDE_CODE_BASE_URL="http://127.0.0.1:3000"
export ATHENA_CLAUDE_CODE_ENABLED="true"

# 性能调优
export NODE_OPTIONS="--max-old-space-size=4096"
export UV_THREADPOOL_SIZE=16

# 日志配置
export CLAUDE_CODE_LOG_LEVEL="info"
export ATHENA_LOG_LEVEL="debug"
```

## 🚀 集成实施步骤

### **第一阶段：基础集成（1-2天）**

#### **步骤1：配置更新**
```bash
# 备份现有配置
cp ~/.claude-code-router/config.json ~/.claude-code-router/config.json.backup

# 应用新配置
cat > ~/.claude-code-router/config.json << 'EOF'
# 使用上面的增强配置内容
EOF

# 创建Athena集成配置
mkdir -p /Volumes/1TB-M2/openclaw/.openclaw
cat > /Volumes/1TB-M2/openclaw/.openclaw/claude_code_integration.json << 'EOF'
# 使用上面的集成配置内容
EOF
```

#### **步骤2：服务重启**
```bash
# 停止现有服务
ccr stop

# 启动增强服务
ccr start

# 验证服务状态
ccr status
curl http://127.0.0.1:3000/health
```

### **第二阶段：Athena适配（2-3天）**

#### **步骤3：创建集成模块**
```python
# /Volumes/1TB-M2/openclaw/scripts/claude_code_integration.py

import requests
import json
import time
from typing import Dict, Any, Optional

class ClaudeCodeIntegration:
    """Claude Code Router 集成类"""
    
    def __init__(self, config_path: str = "/Volumes/1TB-M2/openclaw/.openclaw/claude_code_integration.json"):
        self.config = self._load_config(config_path)
        self.base_url = self.config['claude_code_integration']['base_url']
        self.api_key = self.config['claude_code_integration']['api_key']
        self.timeout = self.config['claude_code_integration']['timeout']
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"配置加载失败: {e}")
            return {}
    
    def call_model(self, prompt: str, model_type: str = "athena_default") -> Optional[Dict[str, Any]]:
        """调用模型"""
        model_config = self.config['claude_code_integration']['model_mapping'].get(model_type, {})
        
        payload = {
            "model": model_config.get('model', 'deepseek-chat'),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.7),
            "max_tokens": model_config.get('max_tokens', 4000)
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API调用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"请求异常: {e}")
            return None
```

#### **步骤4：集成测试**
```python
# 测试脚本
integration = ClaudeCodeIntegration()

# 测试默认模型
result = integration.call_model("你好，这是一个测试消息")
if result:
    print("✅ 集成测试通过")
    print(f"响应: {result.get('choices', [{}])[0].get('message', {}).get('content', '')}")
else:
    print("❌ 集成测试失败")
```

### **第三阶段：监控和优化（持续）**

#### **步骤5：监控配置**
```bash
# 启用Prometheus监控
curl http://127.0.0.1:9090/metrics

# 健康检查脚本
cat > /Volumes/1TB-M2/openclaw/scripts/monitor_claude_code.sh << 'EOF'
#!/bin/bash
# Claude Code Router 监控脚本

BASE_URL="http://127.0.0.1:3000"

# 健康检查
health_check() {
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
    if [ "$response" = "200" ]; then
        echo "✅ 服务健康"
        return 0
    else
        echo "❌ 服务异常: HTTP $response"
        return 1
    fi
}

# 性能检查
performance_check() {
    start_time=$(date +%s%3N)
    response=$(curl -s "$BASE_URL/health")
    end_time=$(date +%s%3N)
    duration=$((end_time - start_time))
    
    if [ $duration -lt 100 ]; then
        echo "✅ 响应时间正常: ${duration}ms"
    else
        echo "⚠️ 响应时间较慢: ${duration}ms"
    fi
}

# 执行检查
echo "🔍 Claude Code Router 监控检查"
echo "================================"
health_check
performance_check
EOF

chmod +x /Volumes/1TB-M2/openclaw/scripts/monitor_claude_code.sh
```

## 📊 性能预期与优化

### **性能提升目标**
- **响应时间**: 减少20-30%的模型调用延迟
- **可用性**: 实现99.9%的服务可用性
- **成本优化**: 通过本地模型降低30-50%的API成本

### **监控指标**
1. **响应时间**: 平均响应时间 < 2秒
2. **错误率**: API调用错误率 < 1%
3. **缓存命中率**: 缓存命中率 > 60%
4. **资源使用**: CPU使用率 < 70%, 内存使用 < 80%

## 🔧 故障排除指南

### **常见问题解决**

#### **问题1：服务启动失败**
```bash
# 检查端口占用
lsof -i :3000

# 检查日志
tail -f ~/.claude-code-router/logs/ccr-*.log

# 重新安装
pnpm install
ccr restart
```

#### **问题2：API调用超时**
```bash
# 检查网络连接
ping api.deepseek.com

# 调整超时设置
# 在config.json中增加API_TIMEOUT_MS
```

#### **问题3：模型路由错误**
```bash
# 检查提供商状态
ccr model list

# 验证配置
ccr config validate
```

## 🎯 成功标准

### **技术指标**
- ✅ Claude Code Router 稳定运行
- ✅ Athena 成功通过集成接口调用模型
- ✅ 多提供商故障转移正常工作
- ✅ 监控指标在预期范围内

### **业务价值**
- ✅ 模型调用成本降低
- ✅ 系统响应速度提升
- ✅ 服务可用性提高
- ✅ 运维复杂度降低

---

## 💡 后续优化方向

1. **智能路由**: 基于任务类型自动选择最优模型
2. **负载均衡**: 实现多实例负载均衡
3. **自适应优化**: 根据使用模式动态调整配置
4. **安全增强**: 添加更严格的身份验证和授权

**此配置方案将显著提升Athena Open Human的性能和可靠性，建议按阶段逐步实施。**