#!/bin/bash

# AI Assistant 别名配置脚本
# 设置6个工作流别名系统

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  AI Assistant 工作流别名配置${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查配置文件
CONFIG_FILE="${SCRIPT_DIR}/claude-config.sh"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠  配置文件不存在，创建默认配置...${NC}"
    cat > "$CONFIG_FILE" << 'EOF'
#!/bin/bash

# AI Assistant 配置文件
# 统一管理 DeepSeek 和阿里云 API 配置

# 默认配置
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-}"
DEEPSEEK_API_KEY=""
ALIYUN_API_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"

# DeepSeek 配置
DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
DEEPSEEK_CHAT_MODEL="deepseek-chat"
DEEPSEEK_REASONER_MODEL="deepseek-reasoner"

# 阿里云 DashScope 配置
DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com"
DASHSCOPE_COMPATIBLE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL_QWEN_PLUS="qwen3.6-plus"
DASHSCOPE_MODEL_QWEN_FLASH="qwen3.5-flash"

# 导出配置函数
export_config() {
    local model_type="$1"
    case $model_type in
        "deepseek-chat")
            export LLM_BASE_URL="$DEEPSEEK_BASE_URL"
            export LLM_MODEL="$DEEPSEEK_CHAT_MODEL"
            export LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "deepseek-reasoner")
            export LLM_BASE_URL="$DEEPSEEK_BASE_URL"
            export LLM_MODEL="$DEEPSEEK_REASONER_MODEL"
            export LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "qwen3.6-plus")
            export LLM_BASE_URL="${DASHSCOPE_ADAPTER_URL:-http://127.0.0.1:8080}"
            export LLM_MODEL="qwen3.6-plus"
            export LLM_AUTH_TOKEN="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        *)
            echo "未知模型类型: $model_type"
            return 1
            ;;
    esac
    export AI_CODE_BARE=1
    export AI_CODE_SKIP_KEYCHAIN=1
}
EOF
    echo -e "${GREEN}✓ 已创建默认配置文件${NC}"
fi

# 检查所有脚本文件是否存在
SCRIPTS=(
    "claude-dual-model.sh"
    "claude-qwen-alt.sh"
    "claude-dev.sh"
    "claude-fix.sh"
    "claude-zh.sh"
    "claude-qwen-max.sh"
)

echo -e "${BLUE}🔍 检查脚本文件...${NC}"
for script in "${SCRIPTS[@]}"; do
    if [ -f "/Users/frankie/claude-code-setup/$script" ]; then
        echo -e "  ${GREEN}✓ $script${NC}"
    else
        echo -e "  ${RED}✗ $script (缺失)${NC}"
    fi
done

echo ""
echo -e "${BLUE}📝 别名配置${NC}"
echo ""

# 生成别名配置
ALIAS_CONFIG=$(cat << 'ALIASES'
# AI Assistant 工作流别名 (由 setup-aliases.sh 生成)

# 核心别名
alias claude='/Users/frankie/claude-code-setup/claude-dual-model.sh'
alias claude-dual='/Users/frankie/claude-code-setup/claude-dual-model.sh'

# 专用工作流
alias claude-max='/Users/frankie/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus'
alias claude-dev='/Users/frankie/claude-code-setup/claude-dual-model.sh 2'
alias claude-fix='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'
alias claude-zh='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'

# 备用别名
alias claude-qwen='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'
alias claude-deepseek='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'
ALIASES
)

echo "$ALIAS_CONFIG"
echo ""

# 检查当前shell配置文件
SHELL_CONFIG=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
else
    # 尝试检测
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_CONFIG="$HOME/.bash_profile"
    fi
fi

echo -e "${YELLOW}🤔 如何安装这些别名？${NC}"
echo ""
echo "选项1: 手动添加到shell配置文件 (~/.zshrc 或 ~/.bashrc)"
echo "      将上面的别名配置复制到配置文件中"
echo ""
echo "选项2: 自动添加到当前配置文件"
if [ -n "$SHELL_CONFIG" ]; then
    echo -e "      检测到配置文件: ${CYAN}$SHELL_CONFIG${NC}"
    read -p "      是否自动添加别名？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 备份原文件
        cp "$SHELL_CONFIG" "${SHELL_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)"

        # 移除旧的别名配置（如果有）
        sed -i '' '/^# AI Assistant 工作流别名/,/^alias claude-deepseek=/d' "$SHELL_CONFIG" 2>/dev/null || \
        sed -i '/^# AI Assistant 工作流别名/,/^alias claude-deepseek=/d' "$SHELL_CONFIG"

        # 添加新的别名配置
        echo "" >> "$SHELL_CONFIG"
        echo "# AI Assistant 工作流别名 (由 setup-aliases.sh 生成)" >> "$SHELL_CONFIG"
        echo "" >> "$SHELL_CONFIG"
        echo "# 核心别名" >> "$SHELL_CONFIG"
        echo "alias claude='/Users/frankie/claude-code-setup/claude-dual-model.sh'" >> "$SHELL_CONFIG"
        echo "alias claude-dual='/Users/frankie/claude-code-setup/claude-dual-model.sh'" >> "$SHELL_CONFIG"
        echo "" >> "$SHELL_CONFIG"
        echo "# 专用工作流" >> "$SHELL_CONFIG"
        echo "alias claude-max='/Users/frankie/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus'" >> "$SHELL_CONFIG"
        echo "alias claude-dev='/Users/frankie/claude-code-setup/claude-dual-model.sh 2'" >> "$SHELL_CONFIG"
        echo "alias claude-fix='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'" >> "$SHELL_CONFIG"
        echo "alias claude-zh='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'" >> "$SHELL_CONFIG"
        echo "" >> "$SHELL_CONFIG"
        echo "# 备用别名" >> "$SHELL_CONFIG"
        echo "alias claude-qwen='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'" >> "$SHELL_CONFIG"
        echo "alias claude-deepseek='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'" >> "$SHELL_CONFIG"

        echo -e "${GREEN}✓ 别名已添加到 $SHELL_CONFIG${NC}"
        echo -e "${YELLOW}⚠  运行 'source $SHELL_CONFIG' 使别名生效${NC}"
    fi
else
    echo "      ❌ 无法自动检测shell配置文件"
fi

echo ""
echo -e "${BLUE}🚀 测试别名${NC}"
echo ""
echo "安装别名后，可以运行以下命令测试："
echo ""
echo "  1. ${CYAN}claude${NC}              # 交互式选择模型"
echo "  2. ${CYAN}claude-max '测试'${NC}   # Qwen3.6-Plus最强性能"
echo "  3. ${CYAN}claude-dev${NC}          # DeepSeek R1新功能开发"
echo "  4. ${CYAN}claude-fix 'bug'${NC}    # DeepSeek Chat问题修复"
echo "  5. ${CYAN}claude-zh '中文'${NC}    # Qwen中文项目"
echo ""
echo -e "${YELLOW}⚠  注意：DeepSeek相关功能需要设置 DEEPSEEK_API_KEY${NC}"
echo "  获取地址: https://platform.deepseek.com/api_keys"
echo ""
echo -e "${GREEN}✅ 配置完成！${NC}"
