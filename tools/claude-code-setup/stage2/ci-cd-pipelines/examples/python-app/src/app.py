#!/usr/bin/env python3
"""
Flask Web应用主文件
包含RESTful API端点、数据库集成和监控端点
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis
from prometheus_flask_exporter import PrometheusMetrics

# 配置结构化日志
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s", "request_id": "%(request_id)s"}'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/mydb'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# 配置Redis缓存
app.config['REDIS_URL'] = os.environ.get(
    'REDIS_URL',
    'redis://localhost:6379/0'
)

# 初始化扩展
db = SQLAlchemy(app)
redis_client = FlaskRedis(app)
metrics = PrometheusMetrics(app)

# 添加默认的指标
metrics.info('app_info', 'Application info', version='1.0.0')

# 请求ID中间件
@app.before_request
def before_request():
    """为每个请求生成唯一ID"""
    request.request_id = os.urandom(8).hex()
    logger.info(f"Request started: {request.method} {request.path}")

@app.after_request
def after_request(response: Response) -> Response:
    """记录请求完成"""
    logger.info(f"Request completed: {request.method} {request.path} - {response.status_code}")
    return response

# 数据模型
class User(db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class Product(db.Model):
    """产品模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'created_at': self.created_at.isoformat()
        }

# API路由
@app.route('/')
def index() -> Dict[str, str]:
    """主页"""
    return {
        'message': 'Welcome to Python Flask API',
        'version': '1.0.0',
        'environment': os.environ.get('ENVIRONMENT', 'development')
    }

@app.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """健康检查端点"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False

    try:
        # 检查Redis连接
        redis_client.ping()
        redis_healthy = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_healthy = False

    return {
        'status': 'healthy' if db_healthy and redis_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {
            'database': 'healthy' if db_healthy else 'unhealthy',
            'redis': 'healthy' if redis_healthy else 'unhealthy'
        }
    }

@app.route('/ready', methods=['GET'])
def readiness_check() -> Dict[str, Any]:
    """就绪检查端点"""
    return {
        'status': 'ready',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'python-app',
        'version': '1.0.0'
    }

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    """Prometheus指标端点 (由PrometheusMetrics自动处理)"""
    return Response("", mimetype="text/plain")

@app.route('/api/users', methods=['GET'])
def get_users():
    """获取所有用户"""
    cache_key = 'users:all'
    cached = redis_client.get(cache_key)

    if cached:
        logger.info("Returning cached users")
        return jsonify(json.loads(cached))

    users = User.query.all()
    result = [user.to_dict() for user in users]

    # 缓存1分钟
    redis_client.setex(cache_key, 60, json.dumps(result))

    return jsonify(result)

@app.route('/api/users', methods=['POST'])
def create_user():
    """创建新用户"""
    data = request.get_json()

    if not data or 'username' not in data or 'email' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    # 检查用户名是否已存在
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    # 检查邮箱是否已存在
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    user = User(
        username=data['username'],
        email=data['email']
    )

    db.session.add(user)
    db.session.commit()

    # 清除用户列表缓存
    redis_client.delete('users:all')

    logger.info(f"Created new user: {user.username}")
    return jsonify(user.to_dict()), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    """获取单个用户"""
    cache_key = f'user:{user_id}'
    cached = redis_client.get(cache_key)

    if cached:
        return jsonify(json.loads(cached))

    user = User.query.get_or_404(user_id)
    result = user.to_dict()

    # 缓存2分钟
    redis_client.setex(cache_key, 120, json.dumps(result))

    return jsonify(result)

@app.route('/api/products', methods=['GET'])
def get_products():
    """获取所有产品"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    cache_key = f'products:page:{page}:per_page:{per_page}'
    cached = redis_client.get(cache_key)

    if cached:
        logger.info(f"Returning cached products page {page}")
        return jsonify(json.loads(cached))

    products = Product.query.paginate(page=page, per_page=per_page, error_out=False)
    result = {
        'items': [product.to_dict() for product in products.items],
        'page': page,
        'per_page': per_page,
        'total': products.total,
        'pages': products.pages
    }

    # 缓存30秒
    redis_client.setex(cache_key, 30, json.dumps(result))

    return jsonify(result)

@app.route('/api/products', methods=['POST'])
def create_product():
    """创建新产品"""
    data = request.get_json()

    if not data or 'name' not in data or 'price' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    product = Product(
        name=data['name'],
        price=data['price'],
        stock=data.get('stock', 0)
    )

    db.session.add(product)
    db.session.commit()

    # 清除产品列表缓存
    redis_client.delete('products:*')

    logger.info(f"Created new product: {product.name}")
    return jsonify(product.to_dict()), 201

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id: int):
    """更新产品库存"""
    data = request.get_json()

    if not data or 'stock' not in data:
        return jsonify({'error': 'Missing stock field'}), 400

    product = Product.query.get_or_404(product_id)
    product.stock = data['stock']

    db.session.commit()

    # 清除相关缓存
    redis_client.delete(f'product:{product_id}')
    redis_client.delete('products:*')

    logger.info(f"Updated product {product_id} stock to {product.stock}")
    return jsonify(product.to_dict())

@app.route('/api/status', methods=['GET'])
def status():
    """应用状态信息"""
    from sqlalchemy import text

    db_status = 'unknown'
    redis_status = 'unknown'

    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'

    try:
        redis_client.ping()
        redis_status = 'connected'
    except Exception:
        redis_status = 'disconnected'

    return jsonify({
        'application': 'python-flask-api',
        'version': '1.0.0',
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'database': db_status,
        'redis': redis_status,
        'timestamp': datetime.utcnow().isoformat(),
        'uptime': 'N/A'  # 实际应用中可以使用启动时间计算
    })

# 错误处理
@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(400)
def bad_request(error):
    """400错误处理"""
    return jsonify({'error': 'Bad request'}), 400

if __name__ == '__main__':
    # 创建数据库表（开发环境）
    with app.app_context():
        db.create_all()

    # 启动应用
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting Flask application on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)