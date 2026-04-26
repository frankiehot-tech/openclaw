"""
API路由定义
包含所有RESTful API端点和业务逻辑
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, Response, current_app
from flask_sqlalchemy import Pagination

from .models import db, User, UserProfile, Product, Order, OrderItem, AuditLog

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

# 辅助函数
def log_audit(action: str, resource_type: str, resource_id: Optional[int] = None,
              details: Optional[Dict] = None) -> None:
    """记录审计日志"""
    try:
        audit_log = AuditLog(
            user_id=request.user_id if hasattr(request, 'user_id') else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")

def get_redis_client():
    """获取Redis客户端"""
    return current_app.extensions.get('redis')

def cache_get(key: str) -> Optional[Any]:
    """从缓存获取数据"""
    redis_client = get_redis_client()
    if redis_client:
        cached = redis_client.get(key)
        return json.loads(cached) if cached else None
    return None

def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """设置缓存"""
    redis_client = get_redis_client()
    if redis_client:
        redis_client.setex(key, ttl, json.dumps(value))

def cache_delete(pattern: str) -> None:
    """删除匹配模式的缓存"""
    redis_client = get_redis_client()
    if redis_client:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)

# 用户相关路由
@api_bp.route('/users', methods=['GET'])
def get_users():
    """获取所有用户"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    cache_key = f'users:page:{page}:per_page:{per_page}'
    cached = cache_get(cache_key)

    if cached:
        logger.info(f"Returning cached users page {page}")
        return jsonify(cached)

    users = User.query.paginate(page=page, per_page=per_page, error_out=False)
    result = {
        'items': [user.to_dict() for user in users.items],
        'page': page,
        'per_page': per_page,
        'total': users.total,
        'pages': users.pages
    }

    cache_set(cache_key, result, ttl=30)
    return jsonify(result)

@api_bp.route('/users', methods=['POST'])
def create_user():
    """创建新用户"""
    data = request.get_json()

    if not data or 'username' not in data or 'email' not in data:
        return jsonify({'error': 'Missing required fields: username and email'}), 400

    # 验证用户名格式
    if not data['username'].isalnum():
        return jsonify({'error': 'Username must be alphanumeric'}), 400

    # 验证邮箱格式
    if '@' not in data['email']:
        return jsonify({'error': 'Invalid email format'}), 400

    # 检查用户名是否已存在
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    # 检查邮箱是否已存在
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    user = User(
        username=data['username'],
        email=data['email'],
        is_active=data.get('is_active', True)
    )

    db.session.add(user)
    db.session.commit()

    # 创建用户资料
    if 'full_name' in data or 'bio' in data:
        profile = UserProfile(
            user_id=user.id,
            full_name=data.get('full_name'),
            bio=data.get('bio'),
            avatar_url=data.get('avatar_url'),
            location=data.get('location'),
            website=data.get('website')
        )
        db.session.add(profile)
        db.session.commit()

    # 清除缓存
    cache_delete('users:*')

    # 记录审计日志
    log_audit('CREATE', 'User', user.id, {'username': user.username, 'email': user.email})

    logger.info(f"Created new user: {user.username}")
    return jsonify(user.to_dict()), 201

@api_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    """获取单个用户"""
    cache_key = f'user:{user_id}'
    cached = cache_get(cache_key)

    if cached:
        return jsonify(cached)

    user = User.query.get_or_404(user_id)
    result = user.to_dict()

    cache_set(cache_key, result, ttl=120)
    return jsonify(result)

@api_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id: int):
    """更新用户信息"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # 更新用户字段
    if 'email' in data:
        if User.query.filter(User.email == data['email'], User.id != user_id).first():
            return jsonify({'error': 'Email already exists'}), 409
        user.email = data['email']

    if 'is_active' in data:
        user.is_active = data['is_active']

    # 更新用户资料
    if 'full_name' in data or 'bio' in data:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)

        if 'full_name' in data:
            profile.full_name = data['full_name']
        if 'bio' in data:
            profile.bio = data['bio']
        if 'avatar_url' in data:
            profile.avatar_url = data['avatar_url']
        if 'location' in data:
            profile.location = data['location']
        if 'website' in data:
            profile.website = data['website']

        db.session.add(profile)

    user.updated_at = datetime.utcnow()
    db.session.commit()

    # 清除缓存
    cache_delete(f'user:{user_id}')
    cache_delete('users:*')

    # 记录审计日志
    log_audit('UPDATE', 'User', user_id, {'updated_fields': list(data.keys())})

    return jsonify(user.to_dict())

@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    """删除用户"""
    user = User.query.get_or_404(user_id)

    # 软删除：标记为不活跃
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.session.commit()

    # 清除缓存
    cache_delete(f'user:{user_id}')
    cache_delete('users:*')

    # 记录审计日志
    log_audit('DELETE', 'User', user_id, {'username': user.username})

    return jsonify({'message': 'User deactivated successfully'})

# 产品相关路由
@api_bp.route('/products', methods=['GET'])
def get_products():
    """获取所有产品"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category')
    available_only = request.args.get('available_only', 'false').lower() == 'true'

    # 构建缓存键
    cache_key = f'products:page:{page}:per_page:{per_page}'
    if category:
        cache_key += f':category:{category}'
    if available_only:
        cache_key += ':available_only'

    cached = cache_get(cache_key)

    if cached:
        logger.info(f"Returning cached products page {page}")
        return jsonify(cached)

    # 构建查询
    query = Product.query

    if category:
        query = query.filter_by(category=category)

    if available_only:
        query = query.filter_by(is_available=True)

    products = query.paginate(page=page, per_page=per_page, error_out=False)
    result = {
        'items': [product.to_dict() for product in products.items],
        'page': page,
        'per_page': per_page,
        'total': products.total,
        'pages': products.pages
    }

    cache_set(cache_key, result, ttl=30)
    return jsonify(result)

@api_bp.route('/products', methods=['POST'])
def create_product():
    """创建新产品"""
    data = request.get_json()

    required_fields = ['name', 'price', 'sku']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # 检查SKU是否已存在
    if Product.query.filter_by(sku=data['sku']).first():
        return jsonify({'error': 'SKU already exists'}), 409

    product = Product(
        name=data['name'],
        description=data.get('description'),
        price=data['price'],
        stock=data.get('stock', 0),
        category=data.get('category'),
        sku=data['sku'],
        is_available=data.get('is_available', True)
    )

    db.session.add(product)
    db.session.commit()

    # 清除缓存
    cache_delete('products:*')

    # 记录审计日志
    log_audit('CREATE', 'Product', product.id, {'name': product.name, 'sku': product.sku})

    logger.info(f"Created new product: {product.name}")
    return jsonify(product.to_dict()), 201

@api_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id: int):
    """获取单个产品"""
    cache_key = f'product:{product_id}'
    cached = cache_get(cache_key)

    if cached:
        return jsonify(cached)

    product = Product.query.get_or_404(product_id)
    result = product.to_dict()

    cache_set(cache_key, result, ttl=120)
    return jsonify(result)

@api_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id: int):
    """更新产品信息"""
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # 更新产品字段
    updatable_fields = ['name', 'description', 'price', 'stock', 'category', 'is_available']
    updated_fields = []

    for field in updatable_fields:
        if field in data:
            setattr(product, field, data[field])
            updated_fields.append(field)

    # 特殊处理：如果更新了SKU，需要检查唯一性
    if 'sku' in data and data['sku'] != product.sku:
        if Product.query.filter_by(sku=data['sku']).first():
            return jsonify({'error': 'SKU already exists'}), 409
        product.sku = data['sku']
        updated_fields.append('sku')

    if updated_fields:
        product.updated_at = datetime.utcnow()
        db.session.commit()

        # 清除缓存
        cache_delete(f'product:{product_id}')
        cache_delete('products:*')

        # 记录审计日志
        log_audit('UPDATE', 'Product', product_id, {'updated_fields': updated_fields})

    return jsonify(product.to_dict())

@api_bp.route('/products/<int:product_id>/stock', methods=['PATCH'])
def update_product_stock(product_id: int):
    """更新产品库存"""
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    if not data or 'quantity' not in data:
        return jsonify({'error': 'Missing quantity field'}), 400

    quantity = data['quantity']
    if not isinstance(quantity, int):
        return jsonify({'error': 'Quantity must be an integer'}), 400

    # 检查库存是否足够（如果是减少库存）
    if quantity < 0 and product.stock + quantity < 0:
        return jsonify({'error': 'Insufficient stock'}), 400

    old_stock = product.stock
    product.stock += quantity
    product.updated_at = datetime.utcnow()
    db.session.commit()

    # 清除缓存
    cache_delete(f'product:{product_id}')
    cache_delete('products:*')

    # 记录审计日志
    log_audit('UPDATE_STOCK', 'Product', product_id, {
        'old_stock': old_stock,
        'new_stock': product.stock,
        'delta': quantity
    })

    return jsonify({
        'product_id': product_id,
        'old_stock': old_stock,
        'new_stock': product.stock,
        'delta': quantity
    })

# 订单相关路由
@api_bp.route('/orders', methods=['GET'])
def get_orders():
    """获取所有订单"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status')

    # 构建查询
    query = Order.query

    if user_id:
        query = query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    result = {
        'items': [order.to_dict() for order in orders.items],
        'page': page,
        'per_page': per_page,
        'total': orders.total,
        'pages': orders.pages
    }

    return jsonify(result)

@api_bp.route('/orders', methods=['POST'])
def create_order():
    """创建新订单"""
    data = request.get_json()

    if not data or 'user_id' not in data or 'items' not in data:
        return jsonify({'error': 'Missing required fields: user_id and items'}), 400

    # 检查用户是否存在
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # 验证订单项
    order_items = []
    total_amount = 0

    for item_data in data['items']:
        if 'product_id' not in item_data or 'quantity' not in item_data:
            return jsonify({'error': 'Missing product_id or quantity in item'}), 400

        product = Product.query.get(item_data['product_id'])
        if not product:
            return jsonify({'error': f'Product {item_data["product_id"]} not found'}), 404

        if not product.is_available:
            return jsonify({'error': f'Product {product.name} is not available'}), 400

        if product.stock < item_data['quantity']:
            return jsonify({'error': f'Insufficient stock for product {product.name}'}), 400

        unit_price = product.price
        subtotal = unit_price * item_data['quantity']

        order_item = OrderItem(
            product_id=product.id,
            quantity=item_data['quantity'],
            unit_price=unit_price,
            subtotal=subtotal
        )

        order_items.append(order_item)
        total_amount += subtotal

    # 创建订单
    order = Order(
        user_id=data['user_id'],
        status='pending',
        total_amount=total_amount,
        shipping_address=data.get('shipping_address'),
        payment_method=data.get('payment_method', 'credit_card'),
        payment_status='pending'
    )

    db.session.add(order)
    db.session.flush()  # 获取订单ID

    # 设置订单项的order_id并添加到数据库
    for order_item in order_items:
        order_item.order_id = order.id
        db.session.add(order_item)

    # 更新产品库存
    for item_data, order_item in zip(data['items'], order_items):
        product = Product.query.get(item_data['product_id'])
        product.stock -= item_data['quantity']

    db.session.commit()

    # 记录审计日志
    log_audit('CREATE', 'Order', order.id, {
        'user_id': order.user_id,
        'total_amount': order.total_amount,
        'item_count': len(order_items)
    })

    logger.info(f"Created new order {order.id} for user {order.user_id}")
    return jsonify(order.to_dict()), 201

@api_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id: int):
    """获取单个订单"""
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict())

@api_bp.route('/orders/<int:order_id>/status', methods=['PATCH'])
def update_order_status(order_id: int):
    """更新订单状态"""
    order = Order.query.get_or_404(order_id)
    data = request.get_json()

    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status field'}), 400

    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

    old_status = order.status
    order.status = data['status']
    order.updated_at = datetime.utcnow()
    db.session.commit()

    # 记录审计日志
    log_audit('UPDATE_STATUS', 'Order', order_id, {
        'old_status': old_status,
        'new_status': order.status
    })

    return jsonify({
        'order_id': order_id,
        'old_status': old_status,
        'new_status': order.status
    })

# 系统状态路由
@api_bp.route('/status', methods=['GET'])
def system_status():
    """系统状态检查"""
    from sqlalchemy import text

    db_status = 'unknown'
    redis_status = 'unknown'

    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = 'disconnected'

    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            redis_status = 'connected'
        else:
            redis_status = 'not_configured'
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_status = 'disconnected'

    return jsonify({
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': db_status,
            'redis': redis_status
        },
        'environment': current_app.config.get('ENVIRONMENT', 'development'),
        'version': '1.0.0'
    })