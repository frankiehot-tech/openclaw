"""
Locust性能测试文件
用于负载测试Python Flask应用
"""

from locust import HttpUser, task, between, events
import json
import random


class QuickstartUser(HttpUser):
    """快速启动用户类"""
    wait_time = between(1, 5)  # 请求之间的等待时间

    def on_start(self):
        """用户启动时执行"""
        # 登录获取令牌
        self.login()

    def login(self):
        """模拟用户登录"""
        login_data = {
            "username": "testuser",
            "password": "TestPass123!"
        }

        with self.client.post("/api/auth/login",
                            json=login_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                data = json.loads(response.text)
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                # 如果登录失败，使用默认头部
                self.headers = {}

    @task(3)  # 权重：更频繁执行
    def get_health(self):
        """测试健康检查端点"""
        self.client.get("/health")

    @task(2)
    def get_products(self):
        """测试获取产品列表"""
        self.client.get("/api/products")

    @task(1)
    def get_product_detail(self):
        """测试获取产品详情"""
        # 假设产品ID从1到10
        product_id = random.randint(1, 10)
        self.client.get(f"/api/products/{product_id}")

    @task(1)
    def create_order(self):
        """测试创建订单（需要认证）"""
        if hasattr(self, 'headers') and self.headers:
            order_data = {
                "items": [
                    {
                        "product_id": random.randint(1, 10),
                        "quantity": random.randint(1, 3)
                    }
                ],
                "shipping_address": "123 Test St, Test City",
                "payment_method": "credit_card"
            }

            self.client.post("/api/orders",
                           json=order_data,
                           headers=self.headers)

    @task(5)  # 权重最高：频繁的基础端点
    def get_status(self):
        """测试状态端点"""
        self.client.get("/api/status")


class APITestingUser(HttpUser):
    """API测试用户类"""
    wait_time = between(2, 8)

    @task
    def test_all_endpoints(self):
        """测试所有端点"""
        endpoints = [
            "/health",
            "/ready",
            "/metrics",
            "/api/status",
            "/api/products"
        ]

        for endpoint in endpoints:
            self.client.get(endpoint)


# 自定义事件处理器
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """请求事件监听器"""
    if exception:
        print(f"请求失败: {name}, 异常: {exception}")
    elif response_time > 1000:  # 超过1秒
        print(f"慢请求: {name}, 响应时间: {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始事件"""
    print("性能测试开始")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束事件"""
    print("性能测试结束")


# 自定义负载测试场景
class HighLoadScenario(HttpUser):
    """高负载场景测试"""
    wait_time = between(0.1, 0.5)  # 更短的等待时间，更高的并发

    @task(10)
    def health_check_high_load(self):
        """高负载下的健康检查"""
        self.client.get("/health")

    @task(5)
    def products_high_load(self):
        """高负载下的产品查询"""
        self.client.get("/api/products")


# 压力测试场景
class StressTestScenario(HttpUser):
    """压力测试场景"""
    wait_time = between(0.05, 0.2)  # 非常短的等待时间

    @task(20)
    def stress_test_endpoints(self):
        """压力测试端点"""
        endpoints = [
            "/health",
            "/api/status",
            "/ready"
        ]

        endpoint = random.choice(endpoints)
        self.client.get(endpoint)


# 配置测试数据
test_users = [
    {"username": f"user{i}", "password": "TestPass123!"}
    for i in range(1, 11)
]

# 示例：如何运行此测试
# locust -f tests/performance/locustfile.py --host=http://localhost:5000
# 然后在浏览器中打开 http://localhost:8089