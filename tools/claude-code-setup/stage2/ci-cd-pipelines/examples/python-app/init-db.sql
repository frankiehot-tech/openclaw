-- 初始化数据库脚本
-- 在PostgreSQL容器首次启动时执行

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'UTC';

-- 创建测试数据库（用于测试环境）
CREATE DATABASE appdb_test;
COMMENT ON DATABASE appdb_test IS '测试环境数据库';

-- 切换到主数据库
\c appdb

-- 创建用户和权限（如果需要）
-- CREATE USER app_user WITH ENCRYPTED PASSWORD 'app_password';
-- GRANT ALL PRIVILEGES ON DATABASE appdb TO app_user;
-- GRANT ALL PRIVILEGES ON DATABASE appdb_test TO app_user;

-- 设置搜索路径
SET search_path TO public;

-- 创建审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT
);

-- 创建审计日志索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- 添加注释
COMMENT ON TABLE audit_logs IS '应用审计日志表';
COMMENT ON COLUMN audit_logs.user_id IS '用户ID（可为空）';
COMMENT ON COLUMN audit_logs.action IS '操作类型（如LOGIN、CREATE、UPDATE、DELETE）';
COMMENT ON COLUMN audit_logs.resource_type IS '资源类型（如User、Product、Order）';
COMMENT ON COLUMN audit_logs.resource_id IS '资源ID';
COMMENT ON COLUMN audit_logs.details IS '操作详情（JSON格式）';
COMMENT ON COLUMN audit_logs.ip_address IS '客户端IP地址';
COMMENT ON COLUMN audit_logs.user_agent IS '用户代理字符串';

-- 创建函数：更新时间戳
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 创建健康检查表
CREATE TABLE IF NOT EXISTS health_checks (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    check_type VARCHAR(50)
);

-- 创建健康检查索引
CREATE INDEX IF NOT EXISTS idx_health_checks_time ON health_checks(check_time);
CREATE INDEX IF NOT EXISTS idx_health_checks_status ON health_checks(status);

-- 添加初始健康检查记录
INSERT INTO health_checks (status, message, check_type)
VALUES ('healthy', '数据库初始化完成', 'database_init');

-- 输出完成消息
RAISE NOTICE '数据库初始化完成：%', CURRENT_TIMESTAMP;