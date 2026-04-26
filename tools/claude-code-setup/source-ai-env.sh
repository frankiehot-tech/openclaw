#!/bin/bash

# AI Assistant 环境变量导出脚本
# 仅导出非敏感配置，并从本地 Keychain 加载实际密钥。

SECRET_LOADER="$HOME/.config/secret-env/load-keychain-secrets.sh"

cat <<EOF
[ -f "$SECRET_LOADER" ] && source "$SECRET_LOADER"
export GITHUB_USERNAME="frankiehot-tech"
export GITHUB_EMAIL="frankiehot@hotmail.com"
export GITHUB_PERSONAL_ACCESS_TOKEN="\${GITHUB_PERSONAL_ACCESS_TOKEN:-\$GITHUB_TOKEN}"
export AI_AUTOCOMPACT_PCT_OVERRIDE=60
export AI_CODE_AUTO_COMPACT_WINDOW=120000
export AI_BARE_MODE="true"
export AI_ENHANCED="true"
export AI_CODE_BARE="1"
export AI_CODE_SKIP_KEYCHAIN="1"
echo "✅ AI Assistant 环境变量已设置"
EOF
