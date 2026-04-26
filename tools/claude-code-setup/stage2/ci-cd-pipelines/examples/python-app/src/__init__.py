"""
Python Flask应用包
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "Python Flask web application with CI/CD pipeline"

# 导入主要模块
from .app import app, db, redis_client
from .models import User, Product, Order, OrderItem, UserProfile, AuditLog
from .routes import api_blueprint
from .utils import (
    hash_password,
    verify_password,
    generate_jwt_token,
    verify_jwt_token,
    CacheManager,
    RateLimiter,
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    handle_app_error
)