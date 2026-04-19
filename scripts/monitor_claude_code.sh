#!/bin/bash
# Claude Code Router 监控脚本
# 用于 Athena Open Human 集成监控

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BASE_URL="http://127.0.0.1:3000"
CONFIG_PATH="/Volumes/1TB-M2/openclaw/.openclaw/claude_code_integration.json"
LOG_DIR="/Volumes/1TB-M2/openclaw/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SCRIPT_NAME=$(basename "$0")

# 创建日志目录
mkdir -p "$LOG_DIR"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_DIR/claude_code_monitor.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_DIR/claude_code_monitor.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_DIR/claude_code_monitor.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_DIR/claude_code_monitor.log"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" --connect-timeout 10)
    
    if [ "$response" = "200" ]; then
        log_success "服务健康: HTTP $response"
        return 0
    else
        log_error "服务异常: HTTP $response"
        return 1
    fi
}

# 性能检查
performance_check() {
    log_info "执行性能检查..."
    
    local start_time end_time duration
    start_time=$(date +%s%N | cut -c1-13)
    response=$(curl -s "$BASE_URL/health" --connect-timeout 10)
    end_time=$(date +%s%N | cut -c1-13)
    duration=$((end_time - start_time))
    
    if [ $duration -lt 100 ]; then
        log_success "响应时间正常: ${duration}ms"
    elif [ $duration -lt 500 ]; then
        log_info "响应时间可接受: ${duration}ms"
    else
        log_warning "响应时间较慢: ${duration}ms"
    fi
    
    echo "响应时间: ${duration}ms" >> "$LOG_DIR/claude_code_performance.log"
}

# 配置验证
config_check() {
    log_info "验证配置文件..."
    
    if [ ! -f "$CONFIG_PATH" ]; then
        log_error "配置文件不存在: $CONFIG_PATH"
        return 1
    fi
    
    # 检查JSON格式
    if jq empty "$CONFIG_PATH" 2>/dev/null; then
        log_success "配置文件JSON格式正确"
    else
        log_error "配置文件JSON格式错误"
        return 1
    fi
    
    # 检查关键配置
    local enabled
    enabled=$(jq -r '.claude_code_integration.enabled' "$CONFIG_PATH" 2>/dev/null || echo "false")
    
    if [ "$enabled" = "true" ]; then
        log_success "集成已启用"
    else
        log_warning "集成未启用"
    fi
    
    return 0
}

# 服务状态检查
service_status_check() {
    log_info "检查服务状态..."
    
    # 检查端口是否监听
    if lsof -i :3000 > /dev/null 2>&1; then
        log_success "端口 3000 正在监听"
        
        # 获取进程信息
        local pid
        pid=$(lsof -ti:3000 | head -1)
        if [ -n "$pid" ]; then
            log_info "进程ID: $pid"
            
            # 检查进程状态
            if ps -p "$pid" > /dev/null 2>&1; then
                log_success "进程运行正常"
            else
                log_error "进程不存在"
                return 1
            fi
        fi
    else
        log_error "端口 3000 未监听"
        return 1
    fi
    
    return 0
}

# 提供商状态检查
provider_check() {
    log_info "检查提供商配置..."
    
    if [ ! -f "$CONFIG_PATH" ]; then
        return 1
    fi
    
    # 从配置中提取提供商信息
    local providers_count
    providers_count=$(jq -r '.claude_code_integration.model_mapping | length' "$CONFIG_PATH" 2>/dev/null || echo "0")
    
    if [ "$providers_count" -gt 0 ]; then
        log_success "配置了 $providers_count 个模型映射"
        
        # 列出所有模型类型
        jq -r '.claude_code_integration.model_mapping | keys[]' "$CONFIG_PATH" 2>/dev/null | while read -r model_type; do
            local provider model
            provider=$(jq -r ".claude_code_integration.model_mapping.\"$model_type\".provider" "$CONFIG_PATH" 2>/dev/null)
            model=$(jq -r ".claude_code_integration.model_mapping.\"$model_type\".model" "$CONFIG_PATH" 2>/dev/null)
            log_info "  $model_type: $provider/$model"
        done
    else
        log_warning "未配置模型映射"
    fi
}

# API功能测试
api_functional_test() {
    log_info "执行API功能测试..."
    
    # 简单的模型调用测试
    local test_payload test_response
    test_payload='{
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello, this is a test. Please reply with TEST OK."}],
        "temperature": 0.7,
        "max_tokens": 50
    }'
    
    # 尝试从配置获取API密钥
    local api_key
    api_key=$(jq -r '.claude_code_integration.api_key' "$CONFIG_PATH" 2>/dev/null || echo "athena-openhuman-integration-key")
    
    start_time=$(date +%s%N | cut -c1-13)
    
    if test_response=$(curl -s -X POST \
        "$BASE_URL/v1/chat/completions" \
        -H "Authorization: Bearer $api_key" \
        -H "Content-Type: application/json" \
        -d "$test_payload" \
        --connect-timeout 30 \
        --max-time 60); then
        
        end_time=$(date +%s%N | cut -c1-13)
        duration=$((end_time - start_time))
        
        # 检查响应
        if echo "$test_response" | jq -e '.choices' > /dev/null 2>&1; then
            log_success "API功能测试通过: ${duration}ms"
            return 0
        else
            log_warning "API响应格式异常: ${duration}ms"
            echo "响应内容: $test_response" >> "$LOG_DIR/claude_code_api_test.log"
            return 1
        fi
    else
        log_error "API功能测试失败"
        return 1
    fi
}

# 生成报告
generate_report() {
    log_info "生成监控报告..."
    
    local report_file
    report_file="$LOG_DIR/claude_code_report_$TIMESTAMP.txt"
    
    {
        echo "========================================"
        echo "Claude Code Router 监控报告"
        echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================"
        echo ""
        echo "1. 服务状态:"
        echo "   主机: 127.0.0.1"
        echo "   端口: 3000"
        echo "   健康检查: $([ $health_status -eq 0 ] && echo "正常" || echo "异常")"
        echo ""
        echo "2. 性能指标:"
        echo "   响应时间: ${performance_duration}ms"
        echo ""
        echo "3. 配置状态:"
        echo "   配置文件: $CONFIG_PATH"
        echo "   集成启用: $([ "$config_enabled" = "true" ] && echo "是" || echo "否")"
        echo ""
        echo "4. 服务进程:"
        echo "   端口监听: $([ $service_status -eq 0 ] && echo "正常" || echo "异常")"
        echo ""
        echo "5. 提供商配置:"
        echo "   模型映射数量: $providers_count"
        echo ""
        echo "6. API功能:"
        echo "   功能测试: $([ $api_test_status -eq 0 ] && echo "通过" || echo "失败")"
        echo ""
        echo "========================================"
        echo "总结: $([ $overall_status -eq 0 ] && echo "✅ 所有检查通过" || echo "❌ 发现问题")"
        echo "========================================"
    } > "$report_file"
    
    log_success "报告已生成: $report_file"
    
    # 显示报告摘要
    echo ""
    echo "监控报告摘要:"
    tail -20 "$report_file"
}

# 主监控流程
main() {
    echo ""
    echo "🔍 Claude Code Router 监控检查"
    echo "================================"
    
    # 初始化状态变量
    local health_status=0
    local performance_duration=0
    local config_enabled="false"
    local service_status=0
    local providers_count=0
    local api_test_status=0
    local overall_status=0
    
    # 执行各项检查
    health_check || health_status=1
    performance_check
    config_check || config_check_status=1
    
    # 获取配置状态
    config_enabled=$(jq -r '.claude_code_integration.enabled' "$CONFIG_PATH" 2>/dev/null || echo "false")
    
    service_status_check || service_status=1
    
    # 获取提供商数量
    providers_count=$(jq -r '.claude_code_integration.model_mapping | length' "$CONFIG_PATH" 2>/dev/null || echo "0")
    
    # 执行API测试（可选）
    if [ "${1:-}" = "--full" ]; then
        api_functional_test || api_test_status=1
    else
        log_info "跳过API功能测试（使用 --full 参数启用完整测试）"
    fi
    
    # 计算总体状态
    if [ $health_status -eq 0 ] && [ $service_status -eq 0 ]; then
        overall_status=0
    else
        overall_status=1
    fi
    
    # 生成报告
    generate_report
    
    # 退出状态
    if [ $overall_status -eq 0 ]; then
        log_success "监控检查完成，所有关键检查通过"
        exit 0
    else
        log_error "监控检查完成，发现关键问题"
        exit 1
    fi
}

# 帮助信息
show_help() {
    echo "使用方法: $SCRIPT_NAME [选项]"
    echo ""
    echo "选项:"
    echo "  --help     显示此帮助信息"
    echo "  --full     执行完整测试（包括API功能测试）"
    echo "  --health   仅执行健康检查"
    echo "  --config   仅验证配置文件"
    echo "  --status   仅检查服务状态"
    echo ""
    echo "示例:"
    echo "  $SCRIPT_NAME           # 基础监控检查"
    echo "  $SCRIPT_NAME --full    # 完整监控检查"
    echo "  $SCRIPT_NAME --health  # 仅健康检查"
}

# 解析参数
case "${1:-}" in
    --help)
        show_help
        exit 0
        ;;
    --health)
        health_check
        exit $?
        ;;
    --config)
        config_check
        exit $?
        ;;
    --status)
        service_status_check
        exit $?
        ;;
    --full)
        main "$1"
        ;;
    "")
        main
        ;;
    *)
        echo "错误: 未知选项 '$1'"
        show_help
        exit 1
        ;;
esac

