# Makefile for Python Flask Application
.PHONY: help install test lint format clean docker-up docker-down docker-build docker-push

# 默认目标
help:
	@echo "可用命令:"
	@echo "  install     - 安装Python依赖"
	@echo "  test        - 运行测试"
	@echo "  lint        - 运行代码检查"
	@echo "  format      - 格式化代码"
	@echo "  clean       - 清理临时文件"
	@echo "  docker-up   - 启动Docker环境"
	@echo "  docker-down - 停止Docker环境"
	@echo "  docker-build - 构建Docker镜像"
	@echo "  docker-push - 推送Docker镜像"
	@echo "  dev         - 启动开发服务器"
	@echo "  prod        - 启动生产服务器"

# 安装依赖
install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .[dev]

# 开发服务器
dev:
	FLASK_ENV=development FLASK_DEBUG=1 python src/app.py

# 生产服务器（使用gunicorn）
prod:
	gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gthread --threads 2 src.app:app

# 运行测试
test:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml

# 运行单元测试
test-unit:
	pytest tests/unit/ -v

# 运行集成测试
test-integration:
	pytest tests/integration/ -v

# 代码检查
lint:
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports
	pip-audit

# 格式化代码
format:
	black src/ tests/
	isort src/ tests/

# 检查代码格式
check-format:
	black --check src/ tests/
	isort --check-only src/ tests/

# 清理临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".cache" -exec rm -rf {} +

# Docker命令
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker build -t python-app:latest .

docker-push:
	docker tag python-app:latest $(DOCKER_REGISTRY)/python-app:$(DOCKER_TAG)
	docker push $(DOCKER_REGISTRY)/python-app:$(DOCKER_TAG)

# 数据库迁移
db-init:
	flask db init

db-migrate:
	flask db migrate -m "$(MESSAGE)"

db-upgrade:
	flask db upgrade

db-downgrade:
	flask db downgrade

# 安全检查
security-scan:
	pip-audit
	bandit -r src/
	safety check

# 生成依赖图
deps-graph:
	pipdeptree --graph-output png > deps.png

# 覆盖率报告
coverage:
	pytest tests/ --cov=src --cov-report=html
	@echo "覆盖率报告生成在 htmlcov/ 目录中"

# 性能测试
perf-test:
	locust -f tests/performance/locustfile.py --host=http://localhost:5000

# 监控
monitor-up:
	docker-compose -f docker-compose.monitoring.yml up -d

monitor-down:
	docker-compose -f docker-compose.monitoring.yml down

# CI/CD本地模拟
ci-local:
	@echo "运行本地CI检查..."
	$(MAKE) check-format
	$(MAKE) lint
	$(MAKE) test
	@echo "所有检查通过！"

# 环境设置
env-dev:
	cp .env.example .env
	@echo "开发环境配置文件已创建，请编辑 .env 文件"

env-prod:
	cp .env.example .env.production
	@echo "生产环境配置文件已创建，请编辑 .env.production 文件"

# 部署
deploy-staging:
	@echo "部署到staging环境..."
	# 这里添加staging部署命令

deploy-prod:
	@echo "部署到production环境..."
	# 这里添加production部署命令