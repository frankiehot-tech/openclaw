#!/bin/bash
# MAREF沙箱环境部署脚本

set -e  # 遇到错误退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}MAREF沙箱环境部署脚本${NC}"
echo "========================================"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装${NC}"
    echo "请安装Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}警告: Docker Compose未安装，尝试使用docker compose命令${NC}"
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}错误: Docker Compose未安装${NC}"
        echo "请安装Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# 显示菜单
echo "选择部署模式:"
echo "  1) 开发环境 (使用Docker Compose)"
echo "  2) 生产环境 (构建Docker镜像)"
echo "  3) 仅测试Docker构建"
echo "  4) 清理所有容器和镜像"
echo -n "请输入选项 [1-4]: "
read option

case $option in
    1)
        echo -e "${GREEN}启动开发环境...${NC}"
        $DOCKER_COMPOSE up --build -d
        echo -e "${GREEN}开发环境已启动！${NC}"
        echo "API服务地址: http://localhost:5001"
        echo "健康检查: http://localhost:5001/health"
        echo ""
        echo "查看日志: $DOCKER_COMPOSE logs -f"
        echo "停止服务: $DOCKER_COMPOSE down"
        ;;
    2)
        echo -e "${GREEN}构建生产镜像...${NC}"
        docker build -t maref-sandbox:latest .

        echo -e "${GREEN}运行生产容器...${NC}"
        docker run -d \
            --name maref-sandbox-prod \
            -p 5001:5001 \
            -v $(pwd)/sandbox_monitor_report.json:/app/sandbox_monitor_report.json \
            -v $(pwd)/hetu_hexagram_mapping.json:/app/hetu_hexagram_mapping.json \
            --restart unless-stopped \
            maref-sandbox:latest

        echo -e "${GREEN}生产容器已启动！${NC}"
        echo "容器名称: maref-sandbox-prod"
        echo "API服务地址: http://localhost:5001"
        echo ""
        echo "查看日志: docker logs -f maref-sandbox-prod"
        echo "停止容器: docker stop maref-sandbox-prod"
        echo "删除容器: docker rm maref-sandbox-prod"
        ;;
    3)
        echo -e "${GREEN}测试Docker构建...${NC}"
        docker build -t maref-sandbox-test .
        echo -e "${GREEN}构建成功！${NC}"
        echo "镜像大小:"
        docker images maref-sandbox-test --format "{{.Size}}"
        ;;
    4)
        echo -e "${YELLOW}清理所有容器和镜像...${NC}"
        echo -n "确认清理？(y/N): "
        read confirm
        if [[ $confirm == "y" || $confirm == "Y" ]]; then
            docker stop maref-sandbox-prod 2>/dev/null || true
            docker rm maref-sandbox-prod 2>/dev/null || true
            $DOCKER_COMPOSE down 2>/dev/null || true
            docker rmi maref-sandbox:latest 2>/dev/null || true
            docker rmi maref-sandbox-test 2>/dev/null || true
            echo -e "${GREEN}清理完成！${NC}"
        else
            echo -e "${YELLOW}取消清理${NC}"
        fi
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}部署脚本完成！${NC}"
echo "========================================"