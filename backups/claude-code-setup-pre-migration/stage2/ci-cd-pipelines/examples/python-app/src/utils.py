"""
工具函数模块
包含通用工具、验证器、辅助函数等
"""

import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from functools import wraps

import jwt
from flask import request, current_app, g


# 密码工具
def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """使用SHA-256哈希密码

    Args:
        password: 明文密码
        salt: 盐值，如果为None则生成随机盐

    Returns:
        tuple: (哈希值, 盐值)
    """
    if salt is None:
        salt = uuid.uuid4().hex

    # 组合密码和盐值
    password_salt = password + salt

    # 计算哈希
    hash_obj = hashlib.sha256(password_salt.encode())
    password_hash = hash_obj.hexdigest()

    return password_hash, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """验证密码

    Args:
        password: 待验证的密码
        stored_hash: 存储的哈希值
        salt: 存储的盐值

    Returns:
        bool: 密码是否正确
    """
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest() == stored_hash


# 验证器
def is_valid_email(email: str) -> bool:
    """验证邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        bool: 是否为有效邮箱
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_username(username: str) -> bool:
    """验证用户名格式

    Args:
        username: 用户名

    Returns:
        bool: 是否为有效用户名
    """
    # 只允许字母、数字、下划线和连字符，长度3-20
    pattern = r'^[a-zA-Z0-9_-]{3,20}$'
    return bool(re.match(pattern, username))


def is_valid_password(password: str) -> tuple[bool, Optional[str]]:
    """验证密码强度

    Args:
        password: 密码

    Returns:
        tuple: (是否有效, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8个字符"

    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"

    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"

    if not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含至少一个特殊字符"

    return True, None


# JWT工具
def generate_jwt_token(payload: Dict[str, Any],
                      secret_key: Optional[str] = None,
                      expires_in: int = 3600) -> str:
    """生成JWT令牌

    Args:
        payload: 负载数据
        secret_key: 密钥，如果为None则使用应用配置
        expires_in: 过期时间（秒）

    Returns:
        str: JWT令牌
    """
    if secret_key is None:
        secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')

    # 添加过期时间
    payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_in)
    payload['iat'] = datetime.utcnow()

    return jwt.encode(payload, secret_key, algorithm='HS256')


def verify_jwt_token(token: str, secret_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """验证JWT令牌

    Args:
        token: JWT令牌
        secret_key: 密钥，如果为None则使用应用配置

    Returns:
        Optional[Dict]: 解码后的负载数据，如果验证失败则返回None
    """
    if secret_key is None:
        secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')

    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# 缓存工具
class CacheManager:
    """缓存管理器"""

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.redis:
            return None

        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception:
            return None

        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """设置缓存值"""
        if not self.redis:
            return False

        try:
            self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.redis:
            return False

        try:
            self.redis.delete(key)
            return True
        except Exception:
            return False

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        if not self.redis:
            return 0

        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
        except Exception:
            pass

        return 0

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        if not self.redis:
            return None

        try:
            return self.redis.incrby(key, amount)
        except Exception:
            return None

    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """递减计数器"""
        if not self.redis:
            return None

        try:
            return self.redis.decrby(key, amount)
        except Exception:
            return None


# 分页工具
def paginate_query(query, page: int = 1, per_page: int = 20):
    """分页查询辅助函数

    Args:
        query: SQLAlchemy查询对象
        page: 页码
        per_page: 每页数量

    Returns:
        tuple: (分页对象, 分页元数据)
    """
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    if per_page > 100:
        per_page = 100

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    metadata = {
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'next_num': pagination.next_num,
        'prev_num': pagination.prev_num
    }

    return pagination, metadata


# 请求限流
class RateLimiter:
    """请求限流器"""

    def __init__(self, redis_client, prefix='rate_limit:'):
        self.redis = redis_client
        self.prefix = prefix

    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, Any]]:
        """检查是否允许请求

        Args:
            key: 限流键（如用户ID或IP地址）
            limit: 时间窗口内允许的最大请求数
            window: 时间窗口（秒）

        Returns:
            tuple: (是否允许, 限流信息)
        """
        if not self.redis:
            return True, {'allowed': True, 'remaining': limit}

        redis_key = f'{self.prefix}{key}'

        try:
            # 使用Redis事务
            pipeline = self.redis.pipeline()
            now = int(time.time())

            # 移除窗口外的记录
            pipeline.zremrangebyscore(redis_key, 0, now - window)

            # 获取当前窗口内的请求数
            pipeline.zcard(redis_key)

            # 添加当前请求
            pipeline.zadd(redis_key, {str(now): now})

            # 设置过期时间
            pipeline.expire(redis_key, window)

            results = pipeline.execute()
            current_count = results[1]

            remaining = max(0, limit - current_count)
            allowed = current_count < limit

            return allowed, {
                'allowed': allowed,
                'limit': limit,
                'remaining': remaining,
                'reset': now + window
            }
        except Exception:
            # Redis出错时允许请求
            return True, {'allowed': True, 'remaining': limit}


# 装饰器
def require_auth(f):
    """需要认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return {'error': '缺少认证信息'}, 401

        # 检查Bearer令牌
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return {'error': '无效的认证格式'}, 401

        token = parts[1]
        payload = verify_jwt_token(token)

        if not payload:
            return {'error': '无效或过期的令牌'}, 401

        # 将用户信息添加到g对象
        g.user_id = payload.get('user_id')
        g.user_role = payload.get('role')

        return f(*args, **kwargs)

    return decorated_function


def require_role(required_role: str):
    """需要特定角色的装饰器"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_role') or g.user_role != required_role:
                return {'error': '权限不足'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def rate_limit(limit: int = 100, window: int = 3600, key_func=None):
    """请求限流装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取限流键
            if key_func:
                rate_key = key_func()
            else:
                # 默认使用IP地址
                rate_key = request.remote_addr or 'unknown'

            # 获取限流器
            redis_client = current_app.extensions.get('redis')
            limiter = RateLimiter(redis_client)

            allowed, info = limiter.is_allowed(rate_key, limit, window)

            if not allowed:
                return {
                    'error': '请求过于频繁',
                    'retry_after': info['reset'] - int(time.time())
                }, 429

            # 添加限流信息到响应头
            response = f(*args, **kwargs)

            if isinstance(response, tuple) and len(response) == 2:
                response_obj, status = response
                if isinstance(response_obj, dict):
                    response_obj['rate_limit'] = info
                    return response_obj, status
            elif isinstance(response, dict):
                response['rate_limit'] = info

            return response

        return decorated_function
    return decorator


# 数据序列化
def serialize_datetime(obj: Any) -> Any:
    """序列化datetime对象为ISO格式字符串"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def serialize_query_result(results: List[Any]) -> List[Dict[str, Any]]:
    """序列化查询结果为字典列表"""
    if not results:
        return []

    # 检查是否为SQLAlchemy模型实例
    if hasattr(results[0], 'to_dict'):
        return [item.to_dict() for item in results]

    # 尝试将普通对象转换为字典
    serialized = []
    for item in results:
        if hasattr(item, '__dict__'):
            serialized.append(item.__dict__)
        elif isinstance(item, dict):
            serialized.append(item)
        else:
            # 尝试使用默认序列化
            try:
                serialized.append(json.loads(json.dumps(item, default=serialize_datetime)))
            except:
                serialized.append(str(item))

    return serialized


# 性能监控
class PerformanceTimer:
    """性能计时器"""

    def __init__(self, name: str = 'operation'):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        elapsed = self.end_time - self.start_time

        # 记录到日志
        current_app.logger.info(f'Performance: {self.name} took {elapsed:.3f} seconds')

        # 可以添加到监控系统
        if hasattr(g, 'performance_metrics'):
            g.performance_metrics[self.name] = elapsed

    @property
    def elapsed(self) -> float:
        """获取经过的时间"""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time


# 错误处理
class AppError(Exception):
    """应用错误基类"""

    def __init__(self, message: str, code: int = 400, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ValidationError(AppError):
    """验证错误"""
    pass


class AuthenticationError(AppError):
    """认证错误"""
    pass


class AuthorizationError(AppError):
    """授权错误"""
    pass


class NotFoundError(AppError):
    """资源未找到错误"""
    pass


def handle_app_error(error: AppError):
    """处理应用错误"""
    response = {
        'error': error.message,
        'code': error.code
    }

    if error.details:
        response['details'] = error.details

    return response, error.code


# 配置管理
class ConfigManager:
    """配置管理器"""

    @staticmethod
    def load_config(env: str = 'development') -> Dict[str, Any]:
        """加载配置

        Args:
            env: 环境名称 (development, staging, production)

        Returns:
            Dict: 配置字典
        """
        # 基础配置
        config = {
            'DEBUG': env == 'development',
            'TESTING': False,
            'ENVIRONMENT': env,
            'SECRET_KEY': 'dev-secret-key-change-in-production',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///app.db',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'REDIS_URL': 'redis://localhost:6379/0',
            'LOG_LEVEL': 'INFO',
            'CORS_ORIGINS': '*'
        }

        # 环境特定配置
        if env == 'production':
            config.update({
                'DEBUG': False,
                'LOG_LEVEL': 'WARNING',
                'SQLALCHEMY_POOL_SIZE': 20,
                'SQLALCHEMY_POOL_RECYCLE': 300,
                'SQLALCHEMY_MAX_OVERFLOW': 10,
            })
        elif env == 'staging':
            config.update({
                'DEBUG': False,
                'LOG_LEVEL': 'INFO',
            })

        return config

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """验证配置

        Args:
            config: 配置字典

        Returns:
            List: 错误消息列表
        """
        errors = []

        required_keys = ['SECRET_KEY', 'SQLALCHEMY_DATABASE_URI']
        for key in required_keys:
            if key not in config or not config[key]:
                errors.append(f'Missing required config: {key}')

        # 验证数据库URL格式
        if 'SQLALCHEMY_DATABASE_URI' in config:
            db_uri = config['SQLALCHEMY_DATABASE_URI']
            if not db_uri.startswith(('sqlite:///', 'postgresql://', 'mysql://')):
                errors.append(f'Invalid database URI format: {db_uri}')

        return errors