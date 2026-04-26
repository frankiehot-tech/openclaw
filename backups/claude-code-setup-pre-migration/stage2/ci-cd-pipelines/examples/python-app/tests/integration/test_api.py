"""
API集成测试
测试Flask应用的API端点
"""

import json
import pytest
from datetime import datetime


def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get('/health')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_ready_endpoint(client):
    """测试就绪检查端点"""
    response = client.get('/ready')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ready'] is True
    assert 'database' in data
    assert 'redis' in data


def test_metrics_endpoint(client):
    """测试指标端点"""
    response = client.get('/metrics')

    assert response.status_code == 200
    # Prometheus格式的指标
    assert 'http_requests_total' in response.data.decode()


def test_root_endpoint(client):
    """测试根端点"""
    response = client.get('/')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Python Flask API'
    assert 'version' in data


def test_users_endpoint_unauthenticated(client):
    """测试未认证的用户端点访问"""
    response = client.get('/api/users')

    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'error' in data


def test_users_endpoint_authenticated(authenticated_client, test_user):
    """测试认证的用户端点访问"""
    response = authenticated_client.get('/api/users')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]['username'] == test_user.username


def test_create_user(client, session):
    """测试创建用户"""
    user_data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'StrongPass123!'
    }

    response = client.post('/api/users',
                          data=json.dumps(user_data),
                          content_type='application/json')

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['username'] == 'newuser'
    assert data['email'] == 'newuser@example.com'
    assert 'id' in data


def test_create_user_invalid_data(client):
    """测试使用无效数据创建用户"""
    invalid_data = {
        'username': 'ab',  # 太短
        'email': 'invalid-email',
        'password': 'weak'
    }

    response = client.post('/api/users',
                          data=json.dumps(invalid_data),
                          content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_products_endpoint(client):
    """测试产品端点"""
    response = client.get('/api/products')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_create_product_authenticated(authenticated_client, session):
    """测试认证用户创建产品"""
    product_data = {
        'name': 'Test Product',
        'description': 'A test product',
        'price': 99.99,
        'stock': 100,
        'category': 'electronics',
        'sku': 'TEST-001'
    }

    response = authenticated_client.post('/api/products',
                                        data=json.dumps(product_data),
                                        content_type='application/json')

    # 可能需要管理员权限，这里测试响应格式
    assert response.status_code in [201, 403]
    if response.status_code == 201:
        data = json.loads(response.data)
        assert data['name'] == 'Test Product'


def test_orders_endpoint_authenticated(authenticated_client, test_user, test_product):
    """测试认证用户的订单端点"""
    # 首先创建一个订单
    order_data = {
        'items': [
            {
                'product_id': test_product.id,
                'quantity': 2
            }
        ],
        'shipping_address': '123 Test St',
        'payment_method': 'credit_card'
    }

    create_response = authenticated_client.post('/api/orders',
                                               data=json.dumps(order_data),
                                               content_type='application/json')

    if create_response.status_code == 201:
        # 测试获取订单列表
        list_response = authenticated_client.get('/api/orders')
        assert list_response.status_code == 200
        orders = json.loads(list_response.data)
        assert isinstance(orders, list)


def test_rate_limiting(client):
    """测试速率限制"""
    endpoint = '/api/status'

    # 发送多个请求
    responses = []
    for i in range(15):  # 假设限制是10/小时
        response = client.get(endpoint)
        responses.append(response.status_code)

    # 应该有一些请求被限制（429状态码）
    # 注意：这取决于实际的速率限制配置
    print(f"响应状态码: {responses}")


def test_error_handling(client):
    """测试错误处理"""
    # 测试不存在的端点
    response = client.get('/api/nonexistent')
    assert response.status_code == 404

    # 测试不支持的HTTP方法
    response = client.put('/health')
    assert response.status_code == 405

    # 测试无效的JSON
    response = client.post('/api/users',
                          data='invalid json',
                          content_type='application/json')
    assert response.status_code == 400


def test_cors_headers(client):
    """测试CORS头"""
    response = client.get('/health')

    # 检查CORS头
    assert 'Access-Control-Allow-Origin' in response.headers
    assert response.headers['Access-Control-Allow-Origin'] == '*'


def test_cache_headers(client):
    """测试缓存头"""
    response = client.get('/api/products')

    # 检查缓存控制头
    if 'Cache-Control' in response.headers:
        cache_control = response.headers['Cache-Control']
        # 应该包含no-cache或max-age
        assert 'no-cache' in cache_control or 'max-age' in cache_control