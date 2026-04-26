"""
工具函数单元测试
测试工具函数、验证器和辅助类
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from src.utils import (
    hash_password,
    verify_password,
    is_valid_email,
    is_valid_username,
    is_valid_password,
    generate_jwt_token,
    verify_jwt_token,
    CacheManager,
    RateLimiter,
    paginate_query,
    PerformanceTimer,
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    handle_app_error,
    ConfigManager,
    serialize_datetime,
    serialize_query_result
)


# 密码工具测试
def test_hash_password():
    """测试密码哈希"""
    password = 'TestPassword123!'
    hash1, salt1 = hash_password(password)
    hash2, salt2 = hash_password(password, salt1)

    assert len(hash1) == 64  # SHA-256哈希长度
    assert len(salt1) == 32  # UUID十六进制长度
    assert hash1 == hash2  # 相同密码和盐值应该产生相同哈希
    assert salt1 == salt2


def test_hash_password_different_salts():
    """测试不同盐值产生不同哈希"""
    password = 'TestPassword123!'
    hash1, salt1 = hash_password(password)
    hash2, salt2 = hash_password(password)

    assert hash1 != hash2  # 不同盐值应该产生不同哈希
    assert salt1 != salt2


def test_verify_password_correct():
    """测试密码验证正确"""
    password = 'TestPassword123!'
    stored_hash, salt = hash_password(password)

    assert verify_password(password, stored_hash, salt) is True


def test_verify_password_incorrect():
    """测试密码验证错误"""
    password = 'TestPassword123!'
    wrong_password = 'WrongPassword123!'
    stored_hash, salt = hash_password(password)

    assert verify_password(wrong_password, stored_hash, salt) is False


# 验证器测试
def test_is_valid_email():
    """测试邮箱验证"""
    # 有效邮箱
    assert is_valid_email('test@example.com') is True
    assert is_valid_email('user.name@domain.co.uk') is True
    assert is_valid_email('user+tag@domain.org') is True

    # 无效邮箱
    assert is_valid_email('invalid-email') is False
    assert is_valid_email('@domain.com') is False
    assert is_valid_email('user@domain') is False
    assert is_valid_email('') is False


def test_is_valid_username():
    """测试用户名验证"""
    # 有效用户名
    assert is_valid_username('user123') is True
    assert is_valid_username('test_user') is True
    assert is_valid_username('test-user') is True
    assert is_valid_username('abc') is True  # 最小长度
    assert is_valid_username('a' * 20) is True  # 最大长度

    # 无效用户名
    assert is_valid_username('ab') is False  # 太短
    assert is_valid_username('a' * 21) is False  # 太长
    assert is_valid_username('user@name') is False  # 无效字符
    assert is_valid_username('user name') is False  # 空格
    assert is_valid_username('') is False


def test_is_valid_password():
    """测试密码强度验证"""
    # 有效密码
    valid, msg = is_valid_password('StrongPass123!')
    assert valid is True
    assert msg is None

    # 各种无效情况
    valid, msg = is_valid_password('short')
    assert valid is False
    assert '长度' in msg

    valid, msg = is_valid_password('nouppercase123!')
    assert valid is False
    assert '大写字母' in msg

    valid, msg = is_valid_password('NOLOWERCASE123!')
    assert valid is False
    assert '小写字母' in msg

    valid, msg = is_valid_password('NoNumber!')
    assert valid is False
    assert '数字' in msg

    valid, msg = is_valid_password('NoSpecial123')
    assert valid is False
    assert '特殊字符' in msg


# JWT工具测试
def test_generate_jwt_token():
    """测试生成JWT令牌"""
    payload = {'user_id': 123, 'role': 'admin'}
    token = generate_jwt_token(payload, secret_key='test-secret', expires_in=3600)

    assert isinstance(token, str)
    assert len(token) > 0

    # 令牌应该包含三部分（header.payload.signature）
    parts = token.split('.')
    assert len(parts) == 3


def test_verify_jwt_token_valid():
    """测试验证有效JWT令牌"""
    payload = {'user_id': 123, 'role': 'admin'}
    token = generate_jwt_token(payload, secret_key='test-secret', expires_in=3600)

    decoded = verify_jwt_token(token, secret_key='test-secret')
    assert decoded is not None
    assert decoded['user_id'] == 123
    assert decoded['role'] == 'admin'
    assert 'exp' in decoded
    assert 'iat' in decoded


def test_verify_jwt_token_expired():
    """测试验证过期JWT令牌"""
    payload = {'user_id': 123, 'role': 'admin'}
    token = generate_jwt_token(payload, secret_key='test-secret', expires_in=-1)  # 立即过期

    decoded = verify_jwt_token(token, secret_key='test-secret')
    assert decoded is None


def test_verify_jwt_token_invalid_signature():
    """测试验证无效签名的JWT令牌"""
    payload = {'user_id': 123, 'role': 'admin'}
    token = generate_jwt_token(payload, secret_key='correct-secret', expires_in=3600)

    # 使用错误的密钥验证
    decoded = verify_jwt_token(token, secret_key='wrong-secret')
    assert decoded is None


# 缓存管理器测试
def test_cache_manager_get_set(mock_redis):
    """测试缓存获取和设置"""
    cache = CacheManager(mock_redis)

    # 测试设置和获取
    cache.set('test_key', {'data': 'value'}, ttl=60)
    value = cache.get('test_key')

    assert value == {'data': 'value'}


def test_cache_manager_delete(mock_redis):
    """测试缓存删除"""
    cache = CacheManager(mock_redis)

    cache.set('key1', 'value1')
    cache.set('key2', 'value2')

    assert cache.get('key1') == 'value1'
    assert cache.delete('key1') is True
    assert cache.get('key1') is None
    assert cache.get('key2') == 'value2'  # key2应该还在


def test_cache_manager_delete_pattern(mock_redis):
    """测试按模式删除缓存"""
    cache = CacheManager(mock_redis)

    cache.set('users:1', 'user1')
    cache.set('users:2', 'user2')
    cache.set('products:1', 'product1')

    deleted = cache.delete_pattern('users:*')
    assert deleted == 2
    assert cache.get('users:1') is None
    assert cache.get('users:2') is None
    assert cache.get('products:1') == 'product1'


def test_cache_manager_increment_decrement(mock_redis):
    """测试缓存递增递减"""
    cache = CacheManager(mock_redis)

    # 测试递增
    result = cache.increment('counter', 5)
    assert result == 5

    result = cache.increment('counter', 3)
    assert result == 8

    # 测试递减
    result = cache.decrement('counter', 2)
    assert result == 6


def test_cache_manager_without_redis():
    """测试没有Redis时的缓存管理器"""
    cache = CacheManager(None)

    # 所有操作应该静默失败或返回默认值
    assert cache.set('key', 'value') is False
    assert cache.get('key') is None
    assert cache.delete('key') is False
    assert cache.delete_pattern('*') == 0
    assert cache.increment('counter') is None


# 限流器测试
def test_rate_limiter_allowed(mock_redis):
    """测试限流器允许请求"""
    limiter = RateLimiter(mock_redis)

    allowed, info = limiter.is_allowed('user:123', limit=10, window=60)

    assert allowed is True
    assert info['allowed'] is True
    assert info['remaining'] == 9  # 第一次请求后剩余9次
    assert info['limit'] == 10


def test_rate_limiter_exceed_limit(mock_redis):
    """测试限流器超过限制"""
    limiter = RateLimiter(mock_redis)

    # 发送10次请求
    for i in range(10):
        allowed, info = limiter.is_allowed('user:123', limit=10, window=60)
        assert allowed is True

    # 第11次应该被拒绝
    allowed, info = limiter.is_allowed('user:123', limit=10, window=60)
    assert allowed is False
    assert info['remaining'] == 0


def test_rate_limiter_without_redis():
    """测试没有Redis时的限流器"""
    limiter = RateLimiter(None)

    allowed, info = limiter.is_allowed('user:123', limit=10, window=60)

    # 没有Redis时应该允许所有请求
    assert allowed is True
    assert info['allowed'] is True
    assert info['remaining'] == 10


# 分页工具测试（需要模拟查询对象）
def test_paginate_query():
    """测试分页查询工具"""
    # 创建模拟查询对象
    class MockQuery:
        def __init__(self, items):
            self.items = items

        def paginate(self, page, per_page, error_out):
            class MockPagination:
                def __init__(self, items, page, per_page):
                    self.items = items
                    self.page = page
                    self.per_page = per_page
                    self.total = len(items)
                    self.pages = (len(items) + per_page - 1) // per_page
                    self.has_next = page < self.pages
                    self.has_prev = page > 1
                    self.next_num = page + 1 if self.has_next else None
                    self.prev_num = page - 1 if self.has_prev else None

            # 计算分页数据
            start = (page - 1) * per_page
            end = start + per_page
            paginated_items = self.items[start:end]

            return MockPagination(paginated_items, page, per_page)

    # 创建测试数据
    items = list(range(1, 101))  # 1到100
    query = MockQuery(items)

    # 测试第一页
    pagination, metadata = paginate_query(query, page=1, per_page=10)

    assert metadata['page'] == 1
    assert metadata['per_page'] == 10
    assert metadata['total'] == 100
    assert metadata['pages'] == 10
    assert metadata['has_next'] is True
    assert metadata['has_prev'] is False
    assert pagination.items == list(range(1, 11))

    # 测试中间页
    pagination, metadata = paginate_query(query, page=5, per_page=20)

    assert metadata['page'] == 5
    assert metadata['per_page'] == 20
    assert metadata['pages'] == 5  # 100/20 = 5页
    assert pagination.items == list(range(81, 101))


def test_paginate_query_invalid_parameters():
    """测试分页查询无效参数"""
    class MockQuery:
        def paginate(self, page, per_page, error_out):
            return type('MockPagination', (), {
                'items': [],
                'total': 0,
                'pages': 0,
                'has_next': False,
                'has_prev': False,
                'next_num': None,
                'prev_num': None
            })()

    query = MockQuery()

    # 测试无效页码和每页数量自动修正
    pagination, metadata = paginate_query(query, page=0, per_page=0)

    assert metadata['page'] == 1  # 修正为1
    assert metadata['per_page'] == 20  # 修正为20

    pagination, metadata = paginate_query(query, page=1, per_page=200)

    assert metadata['per_page'] == 100  # 限制为100


# 性能计时器测试
def test_performance_timer():
    """测试性能计时器"""
    with PerformanceTimer('test_operation') as timer:
        time.sleep(0.01)  # 休眠10毫秒

    assert timer.elapsed > 0.01
    assert timer.name == 'test_operation'


def test_performance_timer_context_manager():
    """测试性能计时器作为上下文管理器"""
    start_time = time.perf_counter()

    with PerformanceTimer('test'):
        time.sleep(0.005)

    elapsed = time.perf_counter() - start_time

    # 确保计时器记录的时间与手动测量一致（允许微小误差）
    assert elapsed > 0.005


# 错误类测试
def test_app_error():
    """测试应用错误基类"""
    error = AppError('Test error', code=400, details={'field': 'value'})

    assert str(error) == 'Test error'
    assert error.message == 'Test error'
    assert error.code == 400
    assert error.details == {'field': 'value'}


def test_validation_error():
    """测试验证错误"""
    error = ValidationError('Invalid input')

    assert isinstance(error, AppError)
    assert error.code == 400


def test_authentication_error():
    """测试认证错误"""
    error = AuthenticationError('Invalid credentials')

    assert isinstance(error, AppError)
    assert error.code == 401


def test_authorization_error():
    """测试授权错误"""
    error = AuthorizationError('Permission denied')

    assert isinstance(error, AppError)
    assert error.code == 403


def test_not_found_error():
    """测试未找到错误"""
    error = NotFoundError('Resource not found')

    assert isinstance(error, AppError)
    assert error.code == 404


def test_handle_app_error():
    """测试处理应用错误"""
    error = AppError('Test error', code=400, details={'field': 'value'})
    response, status_code = handle_app_error(error)

    assert status_code == 400
    assert response['error'] == 'Test error'
    assert response['code'] == 400
    assert response['details'] == {'field': 'value'}


# 配置管理器测试
def test_config_manager_load_config():
    """测试加载配置"""
    # 测试开发环境配置
    dev_config = ConfigManager.load_config('development')

    assert dev_config['DEBUG'] is True
    assert dev_config['ENVIRONMENT'] == 'development'
    assert 'SECRET_KEY' in dev_config

    # 测试生产环境配置
    prod_config = ConfigManager.load_config('production')

    assert prod_config['DEBUG'] is False
    assert prod_config['ENVIRONMENT'] == 'production'
    assert prod_config['LOG_LEVEL'] == 'WARNING'

    # 测试预生产环境配置
    staging_config = ConfigManager.load_config('staging')

    assert staging_config['DEBUG'] is False
    assert staging_config['ENVIRONMENT'] == 'staging'


def test_config_manager_validate_config():
    """测试验证配置"""
    # 有效配置
    valid_config = {
        'SECRET_KEY': 'test-secret',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'
    }
    errors = ConfigManager.validate_config(valid_config)
    assert len(errors) == 0

    # 缺少必需配置
    invalid_config = {'SECRET_KEY': ''}
    errors = ConfigManager.validate_config(invalid_config)
    assert len(errors) > 0
    assert any('Missing required config' in error for error in errors)

    # 无效数据库URL
    invalid_db_config = {
        'SECRET_KEY': 'test',
        'SQLALCHEMY_DATABASE_URI': 'invalid://url'
    }
    errors = ConfigManager.validate_config(invalid_db_config)
    assert any('Invalid database URI' in error for error in errors)


# 序列化测试
def test_serialize_datetime():
    """测试日期时间序列化"""
    dt = datetime(2023, 12, 25, 10, 30, 45)
    result = serialize_datetime(dt)

    assert result == '2023-12-25T10:30:45'

    # 测试非日期时间对象
    with pytest.raises(TypeError):
        serialize_datetime('not a datetime')


def test_serialize_query_result():
    """测试查询结果序列化"""
    # 测试空列表
    assert serialize_query_result([]) == []

    # 测试字典列表
    dict_list = [{'id': 1, 'name': 'test'}, {'id': 2, 'name': 'test2'}]
    assert serialize_query_result(dict_list) == dict_list

    # 测试具有to_dict方法的对象
    class MockModel:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        def to_dict(self):
            return {'id': self.id, 'name': self.name}

    objects = [MockModel(1, 'test1'), MockModel(2, 'test2')]
    result = serialize_query_result(objects)

    assert result == [{'id': 1, 'name': 'test1'}, {'id': 2, 'name': 'test2'}]

    # 测试普通对象
    class PlainObject:
        def __init__(self, value):
            self.value = value

    plain_objects = [PlainObject('test')]
    result = serialize_query_result(plain_objects)

    assert len(result) == 1
    assert 'value' in result[0]