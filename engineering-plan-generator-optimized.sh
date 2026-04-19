#!/bin/bash
# 工程化实施方案生成器
# 将碎片化的AI提案转换为结构化的工程实施方案
# 按项目阶段分类，生成任务拆解和队列编排

set -euo pipefail

# 配置
BASE_DIR="/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）"
AI_PLAN_DIR="$BASE_DIR/007-AI-plan"
COMPLETED_DIR="$AI_PLAN_DIR/完成"
APPROVED_DIR="$AI_PLAN_DIR/批准"
OUTPUT_DIR="$BASE_DIR/008-工程实施方案"
PHASE_MAPPING_DIR="$BASE_DIR/006-执行阶段"
TEMPLATE_DIR="${HOME}/.openclaw/config/engineering-templates"
STATE_DIR="${HOME}/.openclaw/state"
LOG_DIR="${HOME}/.openclaw/logs"

# 确保目录存在
mkdir -p "$OUTPUT_DIR"
mkdir -p "$TEMPLATE_DIR"
mkdir -p "$LOG_DIR"

# 颜色输出
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# macOS兼容的date函数
date_iso() {
    # 输出ISO8601格式: YYYY-MM-DDTHH:MM:SS+08:00
    date "+%Y-%m-%dT%H:%M:%S%z" | sed 's/\([+-][0-9]\{2\}\)\([0-9]\{2\}\)$/\1:\2/'
}

date_plus_days() {
    local days="$1"
    # macOS使用-v选项
    date -v+${days}d "+%Y-%m-%d"
}

# 项目阶段定义（Bash 3兼容方案）
# 使用get_phase_name函数获取阶段名称

# 创建工程实施方案模板
create_engineering_template() {
    local template_name="$1"
    local template_file="$TEMPLATE_DIR/$template_name.md"

    cat > "$template_file" << 'EOF'
# [项目名称] - 工程实施方案

## 基本信息
- **方案ID**: [自动生成]
- **来源提案**: [原提案文件路径]
- **分类阶段**: [阶段一/阶段二/阶段三/阶段四]
- **创建时间**: $(date_iso)
- **优先级**: P[0-2]
- **预估工时**: [小时]

## 核心需求摘要
[从AI提案中提取的核心需求和技术要点]

## 技术依赖分析
### 1. 技术栈要求
- [ ] 列出所需技术组件和版本

### 2. 外部依赖
- [ ] API服务依赖
- [ ] 第三方库依赖
- [ ] 数据源依赖

### 3. 环境要求
- [ ] 开发环境配置
- [ ] 测试环境配置
- [ ] 生产环境配置

## 详细任务拆解
### 子任务 1.1: [任务名称]
- **负责人**: [团队/Agent]
- **技术栈**: [技术栈]
- **验收标准**:
  - [ ] 标准1
  - [ ] 标准2
- **依赖任务**: [无/任务ID]
- **预估工时**: [小时]
- **截止日期**: [日期]

### 子任务 1.2: [任务名称]
- **负责人**: [团队/Agent]
- **技术栈**: [技术栈]
- **验收标准**:
  - [ ] 标准1
  - [ ] 标准2
- **依赖任务**: [无/任务ID]
- **预估工时**: [小时]
- **截止日期**: [日期]

## 质量门禁
### 1. 代码质量
- [ ] 代码审查通过
- [ ] 单元测试覆盖率 ≥80%
- [ ] 静态分析无严重警告

### 2. 文档要求
- [ ] API文档完整
- [ ] 用户手册完成
- [ ] 部署文档完成

### 3. 性能指标
- [ ] 响应时间 ≤[X]ms
- [ ] 并发支持 ≥[Y]用户
- [ ] 内存使用 ≤[Z]MB

## 风险与应对方案
### 高优先级风险 (P0)
1. **风险描述**: [描述]
   - **影响**: [影响范围]
   - **概率**: [高中低]
   - **应对方案**: [应对策略]

### 中优先级风险 (P1)
1. **风险描述**: [描述]
   - **影响**: [影响范围]
   - **概率**: [高中低]
   - **应对方案**: [应对策略]

## 监控与度量
### 1. 进度跟踪
- [ ] 每日进度报告
- [ ] 里程碑达成确认
- [ ] 问题日志维护

### 2. 质量度量
- [ ] 缺陷密度跟踪
- [ ] 用户满意度调查
- [ ] 性能指标监控

## 附件
1. [相关文档链接]
2. [参考技术资料]
3. [测试数据]

---
*本方案由工程化实施方案生成器自动生成*
EOF

    print_success "创建工程模板: $template_name"
}

# 提取提案核心信息
extract_proposal_info() {
    local proposal_file="$1"
    local output_file="$2"

    echo "提取提案信息: $(basename "$proposal_file")" >&2

    # 提取YAML frontmatter
    local title=""
    local source=""
    local status=""
    local created=""

    # 使用python解析YAML frontmatter
    python3 -c "
import yaml
import sys
import re

try:
    with open('$proposal_file', 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            try:
                data = yaml.safe_load(frontmatter)
                if data:
                    print(f'title: {data.get(\"proposal_id\", \"\")}')
                    print(f'source: {data.get(\"source\", \"\")}')
                    print(f'status: {data.get(\"status\", \"\")}')
                    print(f'created: {data.get(\"created\", \"\")}')
            except:
                pass

    # 提取标题
    lines = content.split('\n')
    for line in lines:
        if line.startswith('# ') and '基于' in line:
            # 提取标题内容
            title_match = re.search(r'基于「([^」]+)」', line)
            if title_match:
                print(f'extracted_title: {title_match.group(1)}')
                break

except Exception as e:
    print(f'error: {e}')
    sys.exit(1)
" > "$output_file"

    # 读取提取的信息
    local extracted_title=""
    while IFS=': ' read -r key value; do
        case "$key" in
            title)
                title="$value"
                ;;
            source)
                source="$value"
                ;;
            status)
                status="$value"
                ;;
            created)
                created="$value"
                ;;
            extracted_title)
                extracted_title="$value"
                ;;
        esac
    done < "$output_file"

    # 使用提取的标题或文件名
    if [ -n "$extracted_title" ] && [ "$extracted_title" != "---" ]; then
        title="$extracted_title"
    elif [ -z "$title" ] || [ "$title" = "null" ]; then
        title="$(basename "$proposal_file" .md)"
    fi

    echo "title: $title"
    echo "source: $source"
    echo "status: $status"
    echo "created: $created"
}

# 确定项目阶段
determine_project_phase() {
    local proposal_file="$1"
    local title="$2"

    local content=""
    if [ -f "$proposal_file" ]; then
        content=$(head -500 "$proposal_file" 2>/dev/null || echo "")
    fi

    local search_text="$title $content"

    # 关键词匹配计数 - Bash 3兼容方案
    local phase1_score=0
    local phase2_score=0
    local phase3_score=0
    local phase4_score=0

    # 阶段关键词数组
    local phase1_keywords="内核 硬化 资产 蒸馏 元技能 财务熔断器 Wallet Guardian 知识单元 Lego SKILL 年金协议 OpenClaw 调优 优化 架构 系统 性能"
    local phase2_keywords="原子技能 爆款 筹备 skill-matcher SkillWeaver Demo First 演示视频 人岗匹配 技能 生产 原子"
    local phase3_keywords="GitHub 开源 运营 生态 捕获 星标 开源宣言 MANIFESTO 流量拦截 木马 防御 营销 推广 社区 宣传 社交媒体 内容 运营"
    local phase4_keywords="政策 收割 OPC 入驻 申报 代码贡献奖 奖金 免费算力 数据特权 家族传承 政府 申报 政策 补贴 奖励"

    # 计算每个阶段的关键词匹配分数
    for keyword in $phase1_keywords; do
        if echo "$search_text" | grep -qi "$keyword"; then
            phase1_score=$((phase1_score + 1))
        fi
    done

    for keyword in $phase2_keywords; do
        if echo "$search_text" | grep -qi "$keyword"; then
            phase2_score=$((phase2_score + 1))
        fi
    done

    for keyword in $phase3_keywords; do
        if echo "$search_text" | grep -qi "$keyword"; then
            phase3_score=$((phase3_score + 1))
        fi
    done

    for keyword in $phase4_keywords; do
        if echo "$search_text" | grep -qi "$keyword"; then
            phase4_score=$((phase4_score + 1))
        fi
    done

    # 找出最高分的阶段
    local max_score=$phase1_score
    local selected_phase="phase1"

    if [ $phase2_score -gt $max_score ]; then
        max_score=$phase2_score
        selected_phase="phase2"
    fi

    if [ $phase3_score -gt $max_score ]; then
        max_score=$phase3_score
        selected_phase="phase3"
    fi

    if [ $phase4_score -gt $max_score ]; then
        max_score=$phase4_score
        selected_phase="phase4"
    fi

    # 调试输出
    echo "阶段分数: phase1=$phase1_score, phase2=$phase2_score, phase3=$phase3_score, phase4=$phase4_score" >&2
    echo "选择阶段: $selected_phase (最高分: $max_score)" >&2

    echo "$selected_phase"
}

# 获取阶段名称（Bash 3兼容）
get_phase_name() {
    local phase="$1"
    case "$phase" in
        phase1)
            echo "第一阶段：内核硬化与资产蒸馏 (4月 - 5月)"
            ;;
        phase2)
            echo "第二阶段：原子技能生产与爆款筹备 (5月 - 6月)"
            ;;
        phase3)
            echo "第三阶段：GitHub 开源运营与生态捕获 (6月 - 7月)"
            ;;
        phase4)
            echo "第四阶段：政策收割与 OPC 高位入驻 (7月 - 8月)"
            ;;
        *)
            echo "未知阶段"
            ;;
    esac
}

# 生成工程实施方案
generate_engineering_plan() {
    local proposal_file="$1"
    local output_dir="$2"

    print_header "生成工程实施方案: $(basename "$proposal_file")"

    # 创建临时文件存储提取信息
    local temp_info_file="/tmp/engineering-extract-$$.txt"

    # 提取提案信息
    extract_proposal_info "$proposal_file" "$temp_info_file"

    # 读取提取的信息
    local title=""
    local source=""
    local status=""
    local created=""

    while IFS=':' read -r key value; do
        case "$key" in
            title)
                title="$value"
                ;;
            source)
                source="$value"
                ;;
            status)
                status="$value"
                ;;
            created)
                created="$value"
                ;;
        esac
    done < <(grep -E "^(title|source|status|created):" "$temp_info_file" | sed 's/:/:/')

    # 清理标题（移除-proposal-时间戳后缀）
    local clean_title="$title"
    # 尝试多种清理模式
    clean_title=$(echo "$clean_title" | sed 's/-proposal-[0-9]\{8\}-[0-9]\{6\}$//')
    clean_title=$(echo "$clean_title" | sed 's/-[0-9]\{8\}-[0-9]\{6\}$//')
    clean_title=$(echo "$clean_title" | sed 's/^proposal-//')
    clean_title=$(echo "$clean_title" | sed 's/\.md$//')
    # 修剪首尾空格和连字符
    clean_title=$(echo "$clean_title" | sed 's/^[[:space:]-]*//;s/[[:space:]-]*$//')

    # 如果清理后为空或只有连字符，使用文件名
    if [ -z "$clean_title" ] || [ "$clean_title" = "---" ] || [ "$clean_title" = "-" ]; then
        clean_title=$(basename "$proposal_file" .md)
        # 再次清理文件名
        clean_title=$(echo "$clean_title" | sed 's/-proposal-[0-9]\{8\}-[0-9]\{6\}$//')
        clean_title=$(echo "$clean_title" | sed 's/-[0-9]\{8\}-[0-9]\{6\}$//')
        clean_title=$(echo "$clean_title" | sed 's/^[[:space:]-]*//;s/[[:space:]-]*$//')
    fi

    # 确定项目阶段
    local phase=$(determine_project_phase "$proposal_file" "$clean_title")
    local phase_name=$(get_phase_name "$phase")

    echo "提案标题: $clean_title"
    echo "项目阶段: $phase_name"
    echo "来源文件: $source"

    # 生成方案ID
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local plan_id=$(echo "$clean_title" | tr ' ' '-' | tr -cd '[:alnum:]-' | head -c 50)
    # 移除开头和结尾的连字符
    plan_id=$(echo "$plan_id" | sed 's/^-*//;s/-*$//')
    plan_id="${plan_id}-engineering-plan-${timestamp}"

    # 创建输出文件
    local output_file="$output_dir/${phase}/${plan_id}.md"
    mkdir -p "$(dirname "$output_file")"

    # 读取提案内容以提取更多信息
    local proposal_content=""
    if [ -f "$proposal_file" ]; then
        proposal_content=$(head -1000 "$proposal_file" 2>/dev/null || echo "")
    fi

    # 提取Wave信息
    local wave_info=""
    if echo "$proposal_content" | grep -q "Wave [0-9]:"; then
        wave_info=$(echo "$proposal_content" | grep -A 10 "Wave [0-9]:" | head -30)
    fi

    # 生成工程实施方案
    cat > "$output_file" << EOF
# $clean_title - 工程实施方案

## 基本信息
- **方案ID**: $plan_id
- **来源提案**: $(basename "$proposal_file")
- **提案路径**: $proposal_file
- **分类阶段**: $phase_name
- **创建时间**: $(date_iso)
- **优先级**: P1
- **预估工时**: 8小时

## 核心需求摘要
基于提案"$clean_title"生成工程实施方案。

### 原提案关键信息
- **提案状态**: $status
- **创建时间**: $created
- **来源文件**: $source

EOF

    # 添加Wave信息（如果存在）
    if [ -n "$wave_info" ]; then
        cat >> "$output_file" << EOF

### Wave执行计划（来自原提案）
$wave_info

EOF
    fi

    cat >> "$output_file" << EOF

## 技术依赖分析
### 1. 技术栈要求
- [ ] 根据提案内容确定具体技术栈
- [ ] 验证技术组件版本兼容性
- [ ] 准备开发环境配置

### 2. 外部依赖
- [ ] 识别API服务依赖
- [ ] 确定第三方库依赖
- [ ] 确认数据源可用性

### 3. 环境要求
- [ ] 开发环境：本地开发环境配置
- [ ] 测试环境：隔离测试环境
- [ ] 生产环境：部署环境准备

## 详细任务拆解
### 子任务 1.1: 需求分析与技术选型
- **负责人**: athena-strategist
- **技术栈**: 文档分析、技术评估
- **验收标准**:
  - [ ] 完成需求分析报告
  - [ ] 确定技术选型方案
  - [ ] 制定开发计划
- **依赖任务**: 无
- **预估工时**: 2小时
- **截止日期**: $(date_plus_days 1)

### 子任务 1.2: 原型开发与验证
- **负责人**: claude-executor
- **技术栈**: 原型开发、功能验证
- **验收标准**:
  - [ ] 完成最小可行原型
  - [ ] 通过基础功能测试
  - [ ] 获取用户反馈
- **依赖任务**: 子任务 1.1
- **预估工时**: 3小时
- **截止日期**: $(date_plus_days 2)

### 子任务 1.3: 完整实现与测试
- **负责人**: claude-executor
- **技术栈**: 完整开发、测试套件
- **验收标准**:
  - [ ] 所有功能完整实现
  - [ ] 通过集成测试
  - [ ] 性能测试达标
- **依赖任务**: 子任务 1.2
- **预估工时**: 2小时
- **截止日期**: $(date_plus_days 3)

### 子任务 1.4: 质量审计与部署
- **负责人**: reviewer-auditor
- **技术栈**: 代码审计、部署验证
- **验收标准**:
  - [ ] 代码审计无严重问题
  - [ ] 文档完整度≥90%
  - [ ] 生产部署验证通过
- **依赖任务**: 子任务 1.3
- **预估工时**: 1小时
- **截止日期**: $(date_plus_days 4)

## 质量门禁
### 1. 代码质量
- [ ] 代码审查通过
- [ ] 单元测试覆盖率 ≥80%
- [ ] 静态分析无严重警告

### 2. 文档要求
- [ ] API文档完整
- [ ] 用户手册完成
- [ ] 部署文档完成

### 3. 性能指标
- [ ] 响应时间 ≤1000ms
- [ ] 内存使用 ≤512MB
- [ ] 并发支持 ≥100用户

## 风险与应对方案
### 高优先级风险 (P0)
1. **技术依赖不满足**
   - **影响**: 项目延期或技术方案变更
   - **概率**: 中
   - **应对方案**: 准备备选技术方案，设置技术调研子任务

2. **需求理解偏差**
   - **影响**: 交付物不符合预期
   - **概率**: 中
   - **应对方案**: 设置需求确认环节，定期与提案方沟通

### 中优先级风险 (P1)
1. **开发时间超预期**
   - **影响**: 项目延期
   - **概率**: 高
   - **应对方案**: 设置里程碑检查点，60分钟未完成的任务强制拆分

## 监控与度量
### 1. 进度跟踪
- [ ] 每日进度报告（集成到日报系统）
- [ ] 里程碑达成确认
- [ ] 问题日志维护

### 2. 质量度量
- [ ] 缺陷密度跟踪（每日统计）
- [ ] 代码覆盖率趋势分析
- [ ] 性能指标监控

## 队列编排建议
### 任务队列分配
1. **OpenHuman-AIPlan-优先执行队列.queue.json**: 子任务 1.1, 1.2
2. **OpenHuman-AIPlan-自动策划队列.queue.json**: 子任务 1.3
3. **OpenHuman-AIPlan-策划研究队列.queue.json**: 技术调研任务
4. **OpenHuman-AIPlan-Codex审计队列.queue.json**: 子任务 1.4

### 执行建议
- 按顺序执行子任务 1.1 → 1.2 → 1.3 → 1.4
- 每个子任务完成后自动验证验收标准
- 高风险任务设置检查点机制

## 附件
1. **原提案文件**: $proposal_file
2. **阶段定义参考**: $PHASE_MAPPING_DIR/001-open human 项目-阶段一行动手册.md
3. **工程化模板**: $TEMPLATE_DIR/engineering-template.md

---
*本方案由工程化实施方案生成器自动生成*
*生成时间: $(date_iso)*
EOF

    # 清理临时文件
    rm -f "$temp_info_file"

    print_success "生成工程实施方案: $(basename "$output_file")"
    echo "文件路径: $output_file"

    # 生成队列任务
    generate_queue_tasks "$output_file" "$phase"
}

# 生成队列任务
generate_queue_tasks() {
    local plan_file="$1"
    local phase="$2"

    local queue_base="$AI_PLAN_DIR"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local plan_id=$(basename "$plan_file" .md)

    # 不同阶段使用不同的队列
    local queue_file=""
    case "$phase" in
        phase1)
            queue_file="${queue_base}/OpenHuman-AIPlan-优先执行队列.queue.json"
            ;;
        phase2)
            queue_file="${queue_base}/OpenHuman-AIPlan-自动策划队列.queue.json"
            ;;
        phase3)
            queue_file="${queue_base}/OpenHuman-AIPlan-策划研究队列.queue.json"
            ;;
        phase4)
            queue_file="${queue_base}/OpenHuman-AIPlan-Codex审计队列.queue.json"
            ;;
        *)
            queue_file="${queue_base}/OpenHuman-AIPlan-优先执行队列.queue.json"
            ;;
    esac

    # 确保队列文件存在
    if [ ! -f "$queue_file" ]; then
        cat > "$queue_file" << 'EOF'
{
  "queue_id": "engineering_plan_queue_$(date +%Y%m%d)",
  "name": "工程实施方案执行队列",
  "notes": "由工程化实施方案生成器自动创建",
  "items": []
}
EOF
    fi

    # 创建任务对象（匹配队列格式）
    # 使用TaskIdentityContract生成规范化任务ID（解决以'-'开头被argparse误识别问题）
    local prefix=$(echo "$plan_id" | tr -cd '[:alnum:]_-' | sed 's/^[_-]*//;s/[_-]*$//' | tr '[:upper:]' '[:lower:]')
    if [ -z "$prefix" ]; then
        prefix="engineering_plan"
    fi
    local task_id=$(python3 scripts/generate_task_id.py "$prefix")
    local task_object=$(cat << EOF
{
  "id": "$task_id",
  "title": "执行工程实施方案: $(basename "$plan_file" .md)",
  "instruction_path": "$plan_file",
  "entry_stage": "build",
  "risk_level": "medium",
  "unattended_allowed": true,
  "targets": [],
  "metadata": {
    "priority": "P1",
    "lane": "engineering_execution",
    "epic": "engineering_implementation",
    "category": "engineering_plan",
    "rationale": "由工程化实施方案生成器自动创建的工程实施任务",
    "depends_on": [],
    "autostart": false,
    "generated_by": "engineering-plan-generator.sh",
    "phase": "$phase",
    "plan_file": "$plan_file",
    "assigned_agent": "claude-executor",
    "estimated_hours": 8,
    "acceptance_criteria": [
      "完成需求分析与技术选型",
      "实现原型开发与验证",
      "完成完整实现与测试",
      "通过质量审计与部署"
    ]
  }
}
EOF
)

    # 添加到队列
    local temp_file="/tmp/queue-$$.json"

    # 检查队列文件是否有items字段
    if jq -e '.items' "$queue_file" >/dev/null 2>&1; then
        # 有items字段，添加到items数组
        jq --argjson task "$task_object" '.items += [$task]' "$queue_file" > "$temp_file"
    else
        # 没有items字段，检查是否是数组格式
        if jq -e 'type == "array"' "$queue_file" >/dev/null 2>&1; then
            # 是数组，直接添加
            jq --argjson task "$task_object" '. += [$task]' "$queue_file" > "$temp_file"
        else
            # 是对象但没有items，创建items字段
            jq --argjson task "$task_object" '.items = [$task]' "$queue_file" > "$temp_file"
        fi
    fi

    if [ -f "$temp_file" ]; then
        mv "$temp_file" "$queue_file"
        print_success "添加到任务队列: $(basename "$queue_file")"
        echo "任务ID: $task_id"
    else
        print_error "添加到队列失败: $queue_file"
    fi
}

# 批量处理提案
batch_process_proposals() {
    local source_dir="$1"
    local max_files="${2:-10}"

    print_header "批量处理提案: $source_dir (最多 $max_files 个文件)"

    if [ ! -d "$source_dir" ]; then
        print_error "目录不存在: $source_dir"
        return 1
    fi

    local files=($(find "$source_dir" -name "*.md" -type f | head -$max_files))
    local total_files=${#files[@]}
    local processed=0
    local success=0
    local failed=0

    echo "找到 $total_files 个提案文件"

    for file in "${files[@]}"; do
        processed=$((processed + 1))
        echo -e "\n[$processed/$total_files] 处理: $(basename "$file")"

        if generate_engineering_plan "$file" "$OUTPUT_DIR"; then
            success=$((success + 1))
        else
            failed=$((failed + 1))
            print_warning "处理失败: $(basename "$file")"
        fi
    done

    echo -e "\n批量处理完成:"
    echo "总计处理: $processed"
    echo "成功: $success"
    echo "失败: $failed"

    # 生成汇总报告
    generate_summary_report "$source_dir" "$processed" "$success" "$failed"
}

# 生成汇总报告
generate_summary_report() {
    local source_dir="$1"
    local processed="$2"
    local success="$3"
    local failed="$4"

    local report_file="$LOG_DIR/engineering-planning-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" << EOF
# 工程化实施方案生成汇总报告

## 执行摘要
- **生成时间**: $(date_iso)
- **来源目录**: $source_dir
- **处理文件数**: $processed
- **成功生成**: $success
- **失败**: $failed

## 生成结果
### 按阶段分布
EOF

    # 统计各阶段文件数量
    for phase in phase1 phase2 phase3 phase4; do
        local phase_dir="$OUTPUT_DIR/${phase}"
        if [ -d "$phase_dir" ]; then
            local count=$(find "$phase_dir" -name "*.md" -type f | wc -l | tr -d ' ')
            local phase_name=$(get_phase_name "$phase")
            echo "- **${phase_name}**: $count 个方案" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF

## 任务队列更新
### 队列任务统计
EOF

    # 统计队列任务
    local queue_files=(
        "$AI_PLAN_DIR/OpenHuman-AIPlan-优先执行队列.queue.json"
        "$AI_PLAN_DIR/OpenHuman-AIPlan-自动策划队列.queue.json"
        "$AI_PLAN_DIR/OpenHuman-AIPlan-策划研究队列.queue.json"
        "$AI_PLAN_DIR/OpenHuman-AIPlan-Codex审计队列.queue.json"
    )

    for queue_file in "${queue_files[@]}"; do
        if [ -f "$queue_file" ]; then
            local queue_name=$(basename "$queue_file" .queue.json)
            local task_count=$(jq 'length' "$queue_file" 2>/dev/null || echo "0")
            echo "- **$queue_name**: $task_count 个任务" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF

## 建议与下一步
### 立即行动
1. **审查生成的工程实施方案**：在 $OUTPUT_DIR 目录中
2. **检查任务队列**：确认任务已正确编排
3. **启动任务执行**：使用状态机执行队列任务

### 长期优化
1. **完善阶段分类算法**：提高自动分类准确率
2. **增强任务拆解逻辑**：根据提案内容动态生成任务
3. **集成进度跟踪**：与日报系统集成

## 技术指标
- **处理速度**: $processed 个文件/批次
- **成功率**: $(awk "BEGIN {printf \"%.1f%%\", $success/$processed*100}")
- **阶段分布平衡度**: [待分析]

---
*本报告由工程化实施方案生成器自动生成*
EOF

    print_success "生成汇总报告: $report_file"
}

# 主函数
main() {
    case "${1:-}" in
        "init")
            print_header "初始化工程模板"
            create_engineering_template "engineering-template.md"
            ;;
        "single")
            if [ -z "$2" ]; then
                echo "用法: $0 single <提案文件路径>"
                exit 1
            fi
            print_header "处理单个提案"
            generate_engineering_plan "$2" "$OUTPUT_DIR"
            ;;
        "batch-approved")
            print_header "批量处理已批准提案"
            batch_process_proposals "$APPROVED_DIR" "${2:-10}"
            ;;
        "batch-completed")
            print_header "批量处理已完成提案"
            batch_process_proposals "$COMPLETED_DIR" "${2:-20}"
            ;;
        "test")
            print_header "测试阶段分类"
            # 测试阶段分类功能
            local test_file="$APPROVED_DIR/OpenClaw全量调优工程实施方案-proposal-20260412-175519.md"
            if [ -f "$test_file" ]; then
                extract_proposal_info "$test_file" "/tmp/test-extract.txt"
                local title=$(grep "^title:" /tmp/test-extract.txt | cut -d: -f2-)
                local phase=$(determine_project_phase "$test_file" "$title")
                echo "测试文件: $(basename "$test_file")"
                local phase_name=$(get_phase_name "$phase")
                echo "识别阶段: ${phase_name}"
                rm -f /tmp/test-extract.txt
            else
                print_error "测试文件不存在: $test_file"
            fi
            ;;
        "status")
            print_header "工程化实施方案生成器状态"
            echo "输出目录: $OUTPUT_DIR"
            echo "模板目录: $TEMPLATE_DIR"
            echo "完成目录文件数: $(find "$COMPLETED_DIR" -name "*.md" -type f 2>/dev/null | wc -l)"
            echo "批准目录文件数: $(find "$APPROVED_DIR" -name "*.md" -type f 2>/dev/null | wc -l)"

            # 统计已生成的方案
            if [ -d "$OUTPUT_DIR" ]; then
                echo "已生成工程方案:"
                for phase in phase1 phase2 phase3 phase4; do
                    local phase_dir="$OUTPUT_DIR/${phase}"
                    if [ -d "$phase_dir" ]; then
                        local count=$(find "$phase_dir" -name "*.md" -type f | wc -l | tr -d ' ')
                        local phase_name=$(get_phase_name "$phase")
                        echo "  ${phase_name}: $count 个"
                    fi
                done
            fi
            ;;
        *)
            echo "用法: $0 [command]"
            echo ""
            echo "可用命令:"
            echo "  init                 - 初始化工程模板"
            echo "  single <file>        - 处理单个提案文件"
            echo "  batch-approved [N]   - 批量处理已批准提案（默认10个）"
            echo "  batch-completed [N]  - 批量处理已完成提案（默认20个）"
            echo "  test                 - 测试阶段分类功能"
            echo "  status               - 查看生成器状态"
            echo ""
            echo "示例:"
            echo "  $0 init"
            echo "  $0 single /path/to/proposal.md"
            echo "  $0 batch-approved 5"
            echo "  $0 batch-completed"
            echo "  $0 status"
            ;;
    esac
}

# 执行主函数
main "$@"