#!/bin/bash
# deploy_all_karpathy.sh — 全工具 Karpathy AutoResearch Skill 一键部署
#
# 部署范围: Claude Code / OpenCode / Trae CN / VSCode / Codex
# 部署内容: 7 Karpathy Skills + AGENTS.md (OpenCode/Codex)
#
# 用法:
#   ./scripts/deploy/deploy_all_karpathy.sh [--tool claude|opencode|trae|vscode|codex|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKILLS_SOURCE="$REPO_ROOT/.claude/skills"
SKILLS_DEST="$HOME/.claude/skills"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC} $1"; }
warn() { echo -e "${YELLOW}WARN${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; }

DEPLOY_TOOL="${1:-all}"
if [[ "$DEPLOY_TOOL" == "--tool" ]]; then
    DEPLOY_TOOL="${2:-all}"
fi

KARPATHY_SKILLS=(
    "karpathy-principles.json"
    "karpathy-autoresearch-loop.md"
    "karpathy-code-quality.md"
    "karpathy-simplicity.md"
    "karpathy-knowledge-bases.md"
    "karpathy-goal-driven.md"
    "karpathy-multi-agent.md"
)

verify_deploy() {
    local dest="$1"
    local all_ok=true
    for skill in "${KARPATHY_SKILLS[@]}"; do
        if [[ -f "$dest/$skill" ]]; then
            pass "$skill → $dest"
        else
            fail "$skill 未部署到 $dest"
            all_ok=false
        fi
    done
    $all_ok
}

deploy_claude_code() {
    echo ""
    echo "=== 1/5: Claude Code 部署 ==="
    mkdir -p "$SKILLS_DEST"
    local count=0
    for skill in "${KARPATHY_SKILLS[@]}"; do
        if [[ -f "$SKILLS_SOURCE/$skill" ]]; then
            cp "$SKILLS_SOURCE/$skill" "$SKILLS_DEST/$skill"
            ((count++))
        else
            warn "$skill 源文件不存在: $SKILLS_SOURCE/$skill"
        fi
    done
    echo "  已部署 $count/${#KARPATHY_SKILLS[@]} Skills 到 $SKILLS_DEST"
    verify_deploy "$SKILLS_DEST"
}

deploy_opencode() {
    echo ""
    echo "=== 2/5: OpenCode 部署 ==="
    local dest="$REPO_ROOT"
    local count=0

    if [[ ! -f "$dest/AGENTS.md" ]]; then
        warn "AGENTS.md 不存在，请确认 OpenCode 项目根目录"
        return 1
    fi

    local oc_skills_dir="$dest/.opencode/skills"
    mkdir -p "$oc_skills_dir"

    for skill in "${KARPATHY_SKILLS[@]}"; do
        if [[ -f "$SKILLS_SOURCE/$skill" ]]; then
            cp "$SKILLS_SOURCE/$skill" "$oc_skills_dir/$skill"
            ((count++))
        fi
    done
    echo "  已部署 $count Skills 到 $oc_skills_dir"
    echo "  AGENTS.md 已内建 Karpathy 原则 (无需额外部署)"
    pass "OpenCode 部署完成 (AGENTS.md + Skills)"
}

deploy_trae_cn() {
    echo ""
    echo "=== 3/5: Trae CN 部署 ==="
    local trae_config_dir=""
    if [[ -d "$HOME/Library/Application Support/Code/User" ]]; then
        trae_config_dir="$HOME/Library/Application Support/Code/User"
    elif [[ -d "$HOME/.config/Code/User" ]]; then
        trae_config_dir="$HOME/.config/Code/User"
    fi

    local trae_skills_dir="$trae_config_dir/skills"
    if [[ -n "$trae_config_dir" ]]; then
        mkdir -p "$trae_skills_dir"
        local count=0
        for skill in "${KARPATHY_SKILLS[@]}"; do
            if [[ -f "$SKILLS_SOURCE/$skill" ]]; then
                cp "$SKILLS_SOURCE/$skill" "$trae_skills_dir/$skill"
                ((count++))
            fi
        done
        echo "  已部署 $count Skills 到 $trae_skills_dir"
        pass "Trae CN 部署完成"
    else
        warn "未找到 Trae CN 配置目录 — 请手动部署 Skills 到 Trae CN 的 skills/ 目录"
        echo "  推荐目标路径: ~/.trae/skills/ 或项目 .trae/skills/"
    fi
}

deploy_vscode() {
    echo ""
    echo "=== 4/5: VSCode 部署 ==="
    local vscode_dir="$HOME/.vscode"
    mkdir -p "$vscode_dir/skills"

    local count=0
    for skill in "${KARPATHY_SKILLS[@]}"; do
        if [[ -f "$SKILLS_SOURCE/$skill" ]]; then
            cp "$SKILLS_SOURCE/$skill" "$vscode_dir/skills/$skill"
            ((count++))
        fi
    done
    echo "  已部署 $count Skills 到 $vscode_dir/skills/"
    pass "VSCode 部署完成"
}

deploy_codex() {
    echo ""
    echo "=== 5/5: OpenAI Codex 部署 ==="
    local codex_config="$HOME/.codex"
    mkdir -p "$codex_config"

    if [[ -f "$REPO_ROOT/AGENTS.md" ]]; then
        cp "$REPO_ROOT/AGENTS.md" "$codex_config/AGENTS.md"
    fi

    local codex_skills="$codex_config/skills"
    mkdir -p "$codex_skills"
    local count=0
    for skill in "${KARPATHY_SKILLS[@]}"; do
        if [[ -f "$SKILLS_SOURCE/$skill" ]]; then
            cp "$SKILLS_SOURCE/$skill" "$codex_skills/$skill"
            ((count++))
        fi
    done
    echo "  已部署 $count Skills 到 $codex_skills"
    echo "  已知限制: Codex 可能不完整支持 YAML frontmatter Skill 格式"
    pass "Codex 部署完成"
}

echo "╔══════════════════════════════════════════════╗"
echo "║  Karpathy AutoResearch — 全工具部署 v0.2.0  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "部署范围: $DEPLOY_TOOL"
echo "Skills源: $SKILLS_SOURCE"
echo ""

case "$DEPLOY_TOOL" in
    claude|claude-code)
        deploy_claude_code
        ;;
    opencode)
        deploy_opencode
        ;;
    trae|trae-cn)
        deploy_trae_cn
        ;;
    vscode|code)
        deploy_vscode
        ;;
    codex)
        deploy_codex
        ;;
    all)
        deploy_claude_code
        deploy_opencode
        deploy_trae_cn
        deploy_vscode
        deploy_codex
        ;;
    *)
        echo "用法: $0 [--tool claude|opencode|trae|vscode|codex|all]"
        exit 1
        ;;
esac

echo ""
echo "════════════════════════════════════════════════"
echo -e "${GREEN}部署完成${NC}"
echo ""
echo "验证: 在各工具中运行 '使用 Karpathy 评分' 测试 Skill 激活"
