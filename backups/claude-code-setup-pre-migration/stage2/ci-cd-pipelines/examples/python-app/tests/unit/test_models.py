"""
模型单元测试
测试数据模型和业务逻辑
"""

import pytest
from datetime import datetime
from src.models import User, Product, Order, OrderItem, UserProfile, AuditLog


def test_user_model(test_user):
    """测试用户模型"""
    assert test_user.username == 'testuser'
    assert test_user.email == 'test@example.com'
    assert test_user.is_active is True
    assert isinstance(test_user.created_at, datetime)


def test_user_to_dict(test_user):
    """测试用户字典转换"""
    user_dict = test_user.to_dict()
    assert 'id' in user_dict
    assert user_dict['username'] == 'testuser'
    assert user_dict['email'] == 'test@example.com'
    assert user_dict['is_active'] is True
    assert 'created_at' in user_dict
    assert 'updated_at' in user_dict


def test_user_repr(test_user):
    """测试用户表示方法"""
    repr_str = repr(test_user)
    assert 'User' in repr_str
    assert 'testuser' in repr_str


def test_product_model(test_product):
    """测试产品模型"""
    assert test_product.name == 'Test Product'
    assert test_product.description == 'Test product description'
    assert test_product.price == 99.99
    assert test_product.stock == 100
    assert test_product.category == 'electronics'
    assert test_product.sku == 'TEST-001'
    assert test_product.is_available is True


def test_product_update_stock_increase(test_product):
    """测试增加产品库存"""
    initial_stock = test_product.stock
    success = test_product.update_stock(50)

    assert success is True
    assert test_product.stock == initial_stock + 50


def test_product_update_stock_decrease(test_product):
    """测试减少产品库存"""
    initial_stock = test_product.stock
    success = test_product.update_stock(-30)

    assert success is True
    assert test_product.stock == initial_stock - 30


def test_product_update_stock_insufficient(test_product):
    """测试库存不足的情况"""
    initial_stock = test_product.stock
    success = test_product.update_stock(-(initial_stock + 10))

    assert success is False
    assert test_product.stock == initial_stock  # 库存不应改变


def test_product_to_dict(test_product):
    """测试产品字典转换"""
    product_dict = test_product.to_dict()
    assert 'id' in product_dict
    assert product_dict['name'] == 'Test Product'
    assert product_dict['price'] == 99.99
    assert product_dict['stock'] == 100
    assert product_dict['sku'] == 'TEST-001'
    assert 'created_at' in product_dict
    assert 'updated_at' in product_dict


def test_create_order(session, test_user, test_product):
    """测试创建订单"""
    order = Order(
        user_id=test_user.id,
        status='pending',
        total_amount=199.98,
        shipping_address='123 Test St',
        payment_method='credit_card',
        payment_status='pending'
    )

    session.add(order)
    session.flush()  # 获取订单ID

    # 创建订单项
    order_item = OrderItem(
        order_id=order.id,
        product_id=test_product.id,
        quantity=2,
        unit_price=99.99,
        subtotal=199.98
    )

    session.add(order_item)
    session.commit()

    assert order.id is not None
    assert order.user_id == test_user.id
    assert order.status == 'pending'
    assert order.total_amount == 199.98
    assert len(order.items) == 1
    assert order.items[0].product_id == test_product.id


def test_order_calculate_total(session, test_user, test_product):
    """测试订单总金额计算"""
    order = Order(
        user_id=test_user.id,
        status='pending',
        total_amount=0.0,
        shipping_address='Test Address'
    )

    session.add(order)
    session.flush()

    # 创建多个订单项
    items = [
        OrderItem(
            order_id=order.id,
            product_id=test_product.id,
            quantity=1,
            unit_price=99.99,
            subtotal=99.99
        ),
        OrderItem(
            order_id=order.id,
            product_id=test_product.id,
            quantity=2,
            unit_price=49.99,
            subtotal=99.98
        )
    ]

    session.add_all(items)
    session.commit()

    total = order.calculate_total()
    expected_total = 99.99 + 99.98

    assert abs(total - expected_total) < 0.01


def test_order_item_calculate_subtotal():
    """测试订单项小计计算"""
    order_item = OrderItem(
        quantity=3,
        unit_price=29.99,
        subtotal=0.0  # 初始为0
    )

    subtotal = order_item.calculate_subtotal()
    expected_subtotal = 3 * 29.99

    assert abs(subtotal - expected_subtotal) < 0.01
    assert abs(order_item.subtotal - expected_subtotal) < 0.01


def test_user_profile_model(session, test_user):
    """测试用户资料模型"""
    profile = UserProfile(
        user_id=test_user.id,
        full_name='Test User',
        bio='A test user bio',
        avatar_url='https://example.com/avatar.jpg',
        location='Test City',
        website='https://example.com'
    )

    session.add(profile)
    session.commit()

    assert profile.id is not None
    assert profile.user_id == test_user.id
    assert profile.full_name == 'Test User'
    assert test_user.profiles[0].id == profile.id


def test_audit_log_model(session, test_user):
    """测试审计日志模型"""
    audit_log = AuditLog(
        user_id=test_user.id,
        action='LOGIN',
        resource_type='User',
        resource_id=test_user.id,
        details={'ip': '127.0.0.1'},
        ip_address='127.0.0.1',
        user_agent='Test Agent'
    )

    session.add(audit_log)
    session.commit()

    assert audit_log.id is not None
    assert audit_log.action == 'LOGIN'
    assert audit_log.user_id == test_user.id
    assert audit_log.details == {'ip': '127.0.0.1'}


def test_audit_log_to_dict(session, test_user):
    """测试审计日志字典转换"""
    audit_log = AuditLog(
        user_id=test_user.id,
        action='LOGIN',
        resource_type='User',
        details={'ip': '127.0.0.1'}
    )

    session.add(audit_log)
    session.commit()

    audit_dict = audit_log.to_dict()
    assert 'id' in audit_dict
    assert audit_dict['action'] == 'LOGIN'
    assert audit_dict['user_id'] == test_user.id
    assert audit_dict['details'] == {'ip': '127.0.0.1'}
    assert 'created_at' in audit_dict


def test_create_tables(session):
    """测试创建数据库表"""
    # 尝试查询所有表
    from sqlalchemy import inspect

    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    expected_tables = ['users', 'user_profiles', 'products', 'orders', 'order_items', 'audit_logs']

    for table in expected_tables:
        assert table in tables


def test_model_relationships(session, test_user, test_product):
    """测试模型关系"""
    # 测试用户-订单关系
    order = Order(
        user_id=test_user.id,
        status='pending',
        total_amount=99.99,
        shipping_address='Test Address'
    )

    session.add(order)
    session.commit()

    assert test_user.orders[0].id == order.id

    # 测试订单-订单项关系
    order_item = OrderItem(
        order_id=order.id,
        product_id=test_product.id,
        quantity=1,
        unit_price=99.99,
        subtotal=99.99
    )

    session.add(order_item)
    session.commit()

    assert order.items[0].id == order_item.id
    assert order_item.product.id == test_product.id