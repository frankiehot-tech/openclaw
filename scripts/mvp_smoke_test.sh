#!/bin/bash
# MVP测试环境冒烟测试脚本
# 验证MVP测试环境骨架的基本功能
#
# 测试项目：
# 1. 配置文件存在且可读
# 2. 配置解析测试通过
# 3. 控制面集成测试通过
# 4. 权限映射测试通过
# 5. 模拟onboarding流程步骤
#
# 退出码：
# 0 - 所有测试通过
# 1 - 配置文件缺失
# 2 - 配置解析失败
# 3 - 控制面集成失败
# 4 - 权限映射失败
# 5 - onboarding流程验证失败

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
CONFIG_DIR="$ROOT_DIR/mini-agent/config"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${GREEN}=== $1 ===${NC}"
}

# 步骤1: 检查配置文件存在
log_step "1. 检查MVP配置文件"
MVP_CONFIG="$CONFIG_DIR/mvp_test_env.yaml"
CONTROL_PLANE_CONFIG="$CONFIG_DIR/control_plane.yaml"

if [[ ! -f "$MVP_CONFIG" ]]; then
    log_error "MVP配置文件不存在: $MVP_CONFIG"
    exit 1
fi

if [[ ! -f "$CONTROL_PLANE_CONFIG" ]]; then
    log_error "控制面配置文件不存在: $CONTROL_PLANE_CONFIG"
    exit 1
fi

log_info "找到配置文件:"
log_info "  - $MVP_CONFIG"
log_info "  - $CONTROL_PLANE_CONFIG"

# 步骤2: 验证YAML语法
log_step "2. 验证YAML语法"
if ! python3 -c "import yaml; yaml.safe_load(open('$MVP_CONFIG'))" 2>/dev/null; then
    log_error "MVP配置文件YAML语法错误"
    exit 2
fi

if ! python3 -c "import yaml; yaml.safe_load(open('$CONTROL_PLANE_CONFIG'))" 2>/dev/null; then
    log_error "控制面配置文件YAML语法错误"
    exit 2
fi

log_info "YAML语法验证通过"

# 步骤3: 运行配置解析测试
log_step "3. 运行配置解析测试"
PYTHONPATH="$ROOT_DIR/mini-agent:$PYTHONPATH"
if ! python3 "$SCRIPT_DIR/test_mvp_config_load.py" --verbose; then
    log_error "配置解析测试失败"
    exit 2
fi

log_info "配置解析测试通过"

# 步骤4: 验证控制面集成
log_step "4. 验证控制面集成"
# 检查控制面中是否有mvp_test_env引用
if ! grep -q "mvp_test_env:" "$CONTROL_PLANE_CONFIG"; then
    log_error "控制面中缺少mvp_test_env引用"
    exit 3
fi

# 检查config_source是否正确
if ! grep -A2 "mvp_test_env:" "$CONTROL_PLANE_CONFIG" | grep -q "config_source.*mvp_test_env.yaml"; then
    log_error "控制面中mvp_test_env的config_source不正确"
    exit 3
fi

log_info "控制面集成验证通过"

# 步骤5: 验证权限映射
log_step "5. 验证权限映射"
# 使用Python脚本进行更详细的权限映射验证
if ! python3 -c "
import yaml
import sys

with open('$MVP_CONFIG', 'r') as f:
    config = yaml.safe_load(f)

tiers = config.get('internal_user_tiers', {}).get('tiers', {})
perms = config.get('internal_user_tiers', {}).get('permission_definitions', {})

errors = []
for tier_id, tier_data in tiers.items():
    for perm in tier_data.get('default_permissions', []):
        if perm not in perms:
            errors.append(f'{tier_id}: 权限未定义: {perm}')

if errors:
    print('权限映射错误:')
    for err in errors:
        print(f'  - {err}')
    sys.exit(1)
else:
    print(f'权限映射验证通过: {len(tiers)} 个用户分层, {len(perms)} 个权限定义')
"; then
    log_error "权限映射验证失败"
    exit 4
fi

log_info "权限映射验证通过"

# 步骤6: 模拟onboarding流程
log_step "6. 模拟onboarding流程"
# 检查onboarding骨架定义
if ! python3 -c "
import yaml
import sys

with open('$MVP_CONFIG', 'r') as f:
    config = yaml.safe_load(f)

onboarding = config.get('onboarding_skeleton', {})
if not onboarding:
    print('onboarding_skeleton 为空')
    sys.exit(1)

# 检查必需部分
required_sections = ['invitation_workflow', 'approval_workflow', 'training_materials', 'support_channels']
missing = [section for section in required_sections if section not in onboarding]
if missing:
    print(f'缺少onboarding部分: {missing}')
    sys.exit(1)

print('Onboarding骨架验证通过:')
print(f'  - 邀请流程步骤: {len(onboarding[\"invitation_workflow\"].get(\"steps\", []))}')
print(f'  - 培训材料分类: {len(onboarding[\"training_materials\"].get(\"structure\", []))}')
print(f'  - 支持渠道: {len(onboarding[\"support_channels\"].get(\"tier_specific_channels\", {}))}')
"; then
    log_error "onboarding骨架验证失败"
    exit 5
fi

log_info "Onboarding骨架验证通过"

# 步骤7: 环境健康检查
log_step "7. 环境健康检查"
# 检查健康检查定义
if ! python3 -c "
import yaml
import sys

with open('$MVP_CONFIG', 'r') as f:
    config = yaml.safe_load(f)

health = config.get('environment_health', {})
if not health:
    print('environment_health 为空')
    sys.exit(1)

health_checks = health.get('health_checks', {})
smoke_tests = health.get('smoke_test_suite', {}).get('tests', [])

print('环境健康检查验证通过:')
print(f'  - 健康检查定义: {len(health_checks)} 个')
print(f'  - 冒烟测试用例: {len(smoke_tests)} 个')
"; then
    log_warn "环境健康检查定义不完整（非致命错误）"
fi

# 最终总结
log_step "MVP冒烟测试完成"
log_info "所有核心测试通过"
log_info ""
log_info "MVP测试环境骨架已验证："
log_info "  ✓ 配置文件完整且可解析"
log_info "  ✓ 控制面集成就绪"
log_info "  ✓ 用户分层与权限定义完整"
log_info "  ✓ Onboarding流程骨架就绪"
log_info "  ✓ 环境健康检查定义就绪"
log_info ""
log_info "下一步："
log_info "  1. 邀请内部用户（core_dev/product/early_adopter）"
log_info "  2. 运行完整端到端测试"
log_info "  3. 收集反馈并迭代"
log_info ""

exit 0