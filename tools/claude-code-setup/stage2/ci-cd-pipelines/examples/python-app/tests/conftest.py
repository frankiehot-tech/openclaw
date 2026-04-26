"""
Pytest配置和测试固件
"""

import pytest
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flask import Flask
from src.app import app, db, redis_client
from src.models import User, Product, Order, OrderItem, UserProfile, AuditLog


@pytest.fixture(scope='session')
def flask_app():
    """创建测试Flask应用"""
    # 配置测试环境
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'REDIS_URL': 'redis://localhost:6379/1'  # 使用不同的数据库
    })

    return app


@pytest.fixture(scope='session')
def database(flask_app):
    """创建测试数据库"""
    with flask_app.app_context():
        # 创建所有表
        db.create_all()

        yield db

        # 清理
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(flask_app, database):
    """测试客户端"""
    return flask_app.test_client()


@pytest.fixture
def runner(flask_app):
    """CLI测试运行器"""
    return flask_app.test_cli_runner()


@pytest.fixture
def session(database):
    """数据库会话"""
    connection = database.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = database.create_scoped_session(options=options)

    database.session = session

    yield session

    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def test_user(session):
    """创建测试用户"""
    user = User(
        username='testuser',
        email='test@example.com',
        is_active=True
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def test_product(session):
    """创建测试产品"""
    product = Product(
        name='Test Product',
        description='Test product description',
        price=99.99,
        stock=100,
        category='electronics',
        sku='TEST-001',
        is_available=True
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def authenticated_client(client, test_user):
    """认证的测试客户端"""
    # 创建JWT令牌
    from src.utils import generate_jwt_token

    token = generate_jwt_token(
        {'user_id': test_user.id, 'role': 'user'},
        secret_key='test-secret-key'
    )

    # 设置认证头
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.fixture
def redis_test_client(flask_app):
    """Redis测试客户端"""
    if redis_client:
        # 清空测试数据库
        redis_client.flushdb()
        return redis_client
    return None


@pytest.fixture
def sample_order_data(test_user, test_product):
    """示例订单数据"""
    return {
        'user_id': test_user.id,
        'items': [
            {
                'product_id': test_product.id,
                'quantity': 2
            }
        ],
        'shipping_address': '123 Test St, Test City',
        'payment_method': 'credit_card'
    }


class MockRedis:
    """模拟Redis客户端用于测试"""

    def __init__(self):
        self.data = {}
        self.expiry = {}

    def get(self, key):
        import time
        if key in self.expiry and self.expiry[key] < time.time():
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)

    def setex(self, key, ttl, value):
        import time
        self.data[key] = value
        self.expiry[key] = time.time() + ttl

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                if key in self.expiry:
                    del self.expiry[key]
                count += 1
        return count

    def keys(self, pattern):
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]

    def incrby(self, key, amount):
        if key not in self.data:
            self.data[key] = '0'
        current = int(self.data[key])
        new_value = current + amount
        self.data[key] = str(new_value)
        return new_value

    def decrby(self, key, amount):
        return self.incrby(key, -amount)

    def ping(self):
        return True

    def flushdb(self):
        self.data.clear()
        self.expiry.clear()


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    return MockRedis()