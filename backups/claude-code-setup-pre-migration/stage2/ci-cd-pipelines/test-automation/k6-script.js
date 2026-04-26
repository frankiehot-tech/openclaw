// k6性能测试脚本模板
// 支持多种测试场景：负载测试、压力测试、冒烟测试、峰值测试
// 使用方法: k6 run k6-script.js --out json=results.json

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

// 自定义指标
const errorRate = new Rate('errors');
const requestDuration = new Trend('request_duration');
const requestsCounter = new Counter('requests');

// 测试配置
export const options = {
    // 测试场景配置
    scenarios: {
        // 场景1: 冒烟测试 - 验证基本功能
        smoke_test: {
            executor: 'shared-iterations',
            vus: 1,
            iterations: 5,
            maxDuration: '1m',
            startTime: '0s',
            tags: { test_type: 'smoke' }
        },
        // 场景2: 负载测试 - 模拟正常用户负载
        load_test: {
            executor: 'ramping-vus',
            startVUs: 10,
            stages: [
                { duration: '30s', target: 20 },    // 20个VU在30秒内
                { duration: '1m', target: 20 },     // 保持20个VU1分钟
                { duration: '30s', target: 40 },    // 增加到40个VU
                { duration: '1m', target: 40 },     // 保持40个VU1分钟
                { duration: '30s', target: 0 }      // 逐渐减少到0
            ],
            gracefulRampDown: '30s',
            startTime: '1m',  // 在冒烟测试后开始
            tags: { test_type: 'load' }
        },
        // 场景3: 压力测试 - 测试系统极限
        stress_test: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 20,
            maxVUs: 100,
            stages: [
                { duration: '30s', target: 20 },    // 每秒20个请求
                { duration: '1m', target: 50 },     // 每秒50个请求
                { duration: '30s', target: 100 },   // 每秒100个请求
                { duration: '1m', target: 100 },    // 保持每秒100个请求
                { duration: '30s', target: 0 }      // 逐渐减少
            ],
            startTime: '3m',  // 在负载测试后开始
            tags: { test_type: 'stress' }
        },
        // 场景4: 峰值测试 - 模拟突发流量
        spike_test: {
            executor: 'constant-vus',
            vus: 50,
            duration: '30s',
            startTime: '5m',  // 在压力测试后开始
            tags: { test_type: 'spike' }
        }
    },

    // 阈值配置 - 性能指标要求
    thresholds: {
        // HTTP请求阈值
        'http_req_duration{test_type:smoke}': ['p(95)<500'],      // 冒烟测试: 95%请求 < 500ms
        'http_req_duration{test_type:load}': ['p(95)<1000'],      // 负载测试: 95%请求 < 1s
        'http_req_duration{test_type:stress}': ['p(95)<2000'],    // 压力测试: 95%请求 < 2s
        'http_req_duration{test_type:spike}': ['p(95)<1500'],     // 峰值测试: 95%请求 < 1.5s

        // 错误率阈值
        'errors{test_type:smoke}': ['rate<0.01'],    // 冒烟测试错误率 < 1%
        'errors{test_type:load}': ['rate<0.05'],     // 负载测试错误率 < 5%
        'errors{test_type:stress}': ['rate<0.1'],    // 压力测试错误率 < 10%
        'errors{test_type:spike}': ['rate<0.08'],    // 峰值测试错误率 < 8%

        // 请求成功率
        'http_req_failed{test_type:smoke}': ['rate<0.01'],
        'http_req_failed{test_type:load}': ['rate<0.05'],
        'http_req_failed{test_type:stress}': ['rate<0.1'],
        'http_req_failed{test_type:spike}': ['rate<0.08'],

        // 迭代次数阈值
        'iterations{test_type:smoke}': ['count>4'],
        'iterations{test_type:load}': ['count>100'],
        'iterations{test_type:stress}': ['count>500'],
        'iterations{test_type:spike}': ['count>200'],
    },

    // 全局配置
    discardResponseBodies: false,  // 保留响应体用于验证
    userAgent: 'k6-performance-test/1.0',
    noConnectionReuse: false,
    tlsVersion: {
        min: 'tls1.2',
        max: 'tls1.3'
    },

    // 提取器配置 (用于后续请求)
    extractors: {
        // JSON响应提取器示例
        json: {
            type: 'json',
            expr: '$.token',
            attr: 'auth_token'
        }
    },

    // 系统指标收集
    systemTags: ['url', 'name', 'method', 'status', 'error', 'check', 'scenario', 'group']
};

// 环境变量配置
const ENV = (function() {
    // 从环境变量或默认值获取配置
    const baseUrl = __ENV.BASE_URL || 'http://localhost:3000';
    const apiVersion = __ENV.API_VERSION || 'v1';
    const testUser = {
        username: __ENV.TEST_USERNAME || 'test@example.com',
        password: __ENV.TEST_PASSWORD || 'password123'
    };

    // 端点配置
    const endpoints = {
        health: `${baseUrl}/health`,
        api: `${baseUrl}/api/${apiVersion}`,
        auth: {
            login: `${baseUrl}/api/${apiVersion}/auth/login`,
            register: `${baseUrl}/api/${apiVersion}/auth/register`,
            logout: `${baseUrl}/api/${apiVersion}/auth/logout`
        },
        users: `${baseUrl}/api/${apiVersion}/users`,
        products: `${baseUrl}/api/${apiVersion}/products`,
        orders: `${baseUrl}/api/${apiVersion}/orders`
    };

    // 测试数据
    const testData = {
        loginPayload: JSON.stringify({
            username: testUser.username,
            password: testUser.password
        }),
        productPayload: JSON.stringify({
            name: 'Test Product',
            price: 99.99,
            category: 'electronics',
            stock: 100
        }),
        orderPayload: JSON.stringify({
            productId: '123',
            quantity: 1,
            shippingAddress: '123 Test St, Test City'
        })
    };

    return { baseUrl, endpoints, testData, testUser };
})();

// 全局状态 (在VU之间共享)
const globalState = {
    authToken: null,
    productId: null,
    userId: null
};

// 初始化函数 (每个VU执行一次)
export function setup() {
    console.log(`Initializing test with base URL: ${ENV.baseUrl}`);

    // 可选: 预热API
    const healthResponse = http.get(ENV.endpoints.health);
    check(healthResponse, {
        'Health check passed': (r) => r.status === 200,
        'Health response time': (r) => r.timings.duration < 1000
    });

    return { startTime: new Date().toISOString() };
}

// 清理函数 (测试结束后执行)
export function teardown(data) {
    console.log(`Test completed. Started at: ${data.startTime}`);
    console.log('Cleaning up test resources...');

    // 可选: 清理测试数据
    if (globalState.authToken) {
        const logoutResponse = http.post(ENV.endpoints.auth.logout, null, {
            headers: {
                'Authorization': `Bearer ${globalState.authToken}`,
                'Content-Type': 'application/json'
            }
        });

        check(logoutResponse, {
            'Logout successful': (r) => r.status === 200
        });
    }
}

// 主要测试函数 (每个VU迭代执行)
export default function(data) {
    const scenario = __ENV.K6_SCENARIO || 'load_test';
    const vuId = __VU;
    const iter = __ITER;

    // 根据场景选择测试流程
    switch (scenario) {
        case 'smoke_test':
            runSmokeTest(vuId, iter);
            break;
        case 'load_test':
            runLoadTest(vuId, iter);
            break;
        case 'stress_test':
            runStressTest(vuId, iter);
            break;
        case 'spike_test':
            runSpikeTest(vuId, iter);
            break;
        default:
            runDefaultTest(vuId, iter);
    }
}

// 测试场景函数
function runSmokeTest(vuId, iter) {
    group('Smoke Test - Basic API Validation', function() {
        // 1. 健康检查
        const healthRes = http.get(ENV.endpoints.health);
        checkHealth(healthRes, 'smoke');

        // 2. API版本检查
        const apiRes = http.get(ENV.endpoints.api);
        check(apiRes, {
            'API endpoint accessible': (r) => r.status === 200,
            'API returns JSON': (r) => r.headers['Content-Type'].includes('application/json')
        });

        sleep(1);
    });
}

function runLoadTest(vuId, iter) {
    group('Load Test - Simulate Normal User Behavior', function() {
        // 模拟用户登录流程
        if (iter % 10 === 0 || !globalState.authToken) {
            authenticateUser();
        }

        if (globalState.authToken) {
            // 浏览产品
            browseProducts();

            // 查看产品详情
            if (iter % 3 === 0) {
                viewProductDetails();
            }

            // 创建订单 (20%的迭代)
            if (iter % 5 === 0) {
                createOrder();
            }

            // 查看用户信息
            if (iter % 7 === 0) {
                getUserProfile();
            }
        }

        sleep(Math.random() * 2 + 0.5); // 随机延迟 0.5-2.5秒
    });
}

function runStressTest(vuId, iter) {
    group('Stress Test - High Load Operations', function() {
        // 快速连续请求
        const requests = [];

        // 并发健康检查
        requests.push(http.getAsync(ENV.endpoints.health));

        // 并发API请求
        requests.push(http.getAsync(ENV.endpoints.products));

        // 如果有认证令牌，执行更多操作
        if (globalState.authToken) {
            const headers = {
                'Authorization': `Bearer ${globalState.authToken}`,
                'Content-Type': 'application/json'
            };
            requests.push(http.getAsync(ENV.endpoints.users, { headers }));
        }

        // 等待所有请求完成
        const responses = http.batch(requests);

        // 验证响应
        responses.forEach((res, index) => {
            if (res) {
                check(res, {
                    [`Stress test request ${index} succeeded`]: (r) => r.status >= 200 && r.status < 500
                });
            }
        });

        sleep(0.1); // 非常短的延迟
    });
}

function runSpikeTest(vuId, iter) {
    group('Spike Test - Burst Traffic', function() {
        // 突发请求
        const spikeRequests = [];

        for (let i = 0; i < 5; i++) {
            spikeRequests.push(http.getAsync(ENV.endpoints.health));
        }

        // 如果有认证令牌，添加认证请求
        if (globalState.authToken) {
            const headers = {
                'Authorization': `Bearer ${globalState.authToken}`,
                'Content-Type': 'application/json'
            };
            spikeRequests.push(http.getAsync(ENV.endpoints.products, { headers }));
        }

        const responses = http.batch(spikeRequests);

        // 记录指标
        responses.forEach((res, index) => {
            if (res) {
                requestsCounter.add(1);
                requestDuration.add(res.timings.duration);

                if (res.status >= 400) {
                    errorRate.add(1);
                }
            }
        });

        sleep(0.05); // 极短延迟
    });
}

function runDefaultTest(vuId, iter) {
    // 默认测试流程
    group('Default Test Flow', function() {
        const healthRes = http.get(ENV.endpoints.health);
        checkHealth(healthRes, 'default');

        if (healthRes.status === 200) {
            authenticateUser();

            if (globalState.authToken) {
                browseProducts();
            }
        }

        sleep(1);
    });
}

// 辅助函数
function authenticateUser() {
    const loginRes = http.post(ENV.endpoints.auth.login, ENV.testData.loginPayload, {
        headers: { 'Content-Type': 'application/json' }
    });

    if (check(loginRes, {
        'Login successful': (r) => r.status === 200,
        'Login returns token': (r) => {
            if (r.status === 200) {
                try {
                    const body = JSON.parse(r.body);
                    if (body.token) {
                        globalState.authToken = body.token;
                        return true;
                    }
                } catch (e) {
                    return false;
                }
            }
            return false;
        }
    })) {
        console.log(`VU ${__VU}: Authentication successful`);
    } else {
        console.error(`VU ${__VU}: Authentication failed`);
        errorRate.add(1);
    }
}

function browseProducts() {
    const headers = globalState.authToken ? {
        'Authorization': `Bearer ${globalState.authToken}`,
        'Content-Type': 'application/json'
    } : { 'Content-Type': 'application/json' };

    const productsRes = http.get(ENV.endpoints.products, { headers });

    check(productsRes, {
        'Browse products successful': (r) => r.status === 200,
        'Products returned': (r) => {
            if (r.status === 200) {
                try {
                    const body = JSON.parse(r.body);
                    return Array.isArray(body.products || body);
                } catch (e) {
                    return false;
                }
            }
            return false;
        }
    });

    // 记录响应时间
    requestDuration.add(productsRes.timings.duration);
    requestsCounter.add(1);
}

function viewProductDetails() {
    if (!globalState.productId) {
        // 如果没有产品ID，先获取一个
        const productsRes = http.get(ENV.endpoints.products);
        if (productsRes.status === 200) {
            try {
                const body = JSON.parse(productsRes.body);
                const products = body.products || body;
                if (products.length > 0) {
                    globalState.productId = products[0].id;
                }
            } catch (e) {
                // 忽略错误
            }
        }
    }

    if (globalState.productId) {
        const headers = globalState.authToken ? {
            'Authorization': `Bearer ${globalState.authToken}`
        } : {};

        const productRes = http.get(`${ENV.endpoints.products}/${globalState.productId}`, { headers });

        check(productRes, {
            'View product details successful': (r) => r.status === 200
        });
    }
}

function createOrder() {
    if (!globalState.authToken) return;

    const headers = {
        'Authorization': `Bearer ${globalState.authToken}`,
        'Content-Type': 'application/json'
    };

    const orderRes = http.post(ENV.endpoints.orders, ENV.testData.orderPayload, { headers });

    check(orderRes, {
        'Create order successful': (r) => r.status === 201,
        'Order created with ID': (r) => {
            if (r.status === 201) {
                try {
                    const body = JSON.parse(r.body);
                    return body.orderId || body.id;
                } catch (e) {
                    return false;
                }
            }
            return false;
        }
    });
}

function getUserProfile() {
    if (!globalState.authToken) return;

    const headers = {
        'Authorization': `Bearer ${globalState.authToken}`
    };

    const userRes = http.get(ENV.endpoints.users, { headers });

    check(userRes, {
        'Get user profile successful': (r) => r.status === 200
    });
}

function checkHealth(response, testType) {
    const checkResult = check(response, {
        [`${testType} - Health check status`]: (r) => r.status === 200,
        [`${test_type} - Health response time`]: (r) => r.timings.duration < 1000,
        [`${test_type} - Health response format`]: (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.status === 'healthy' || body.status === 'ok';
            } catch (e) {
                return false;
            }
        }
    });

    if (!checkResult) {
        errorRate.add(1);
    }

    requestsCounter.add(1);
    requestDuration.add(response.timings.duration);

    return checkResult;
}

// 生成HTML报告 (可选)
export function handleSummary(data) {
    const reportName = `k6-report-${new Date().toISOString().slice(0, 10)}.html`;
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        [reportName]: htmlReport(data),
        'summary.json': JSON.stringify(data, null, 2)
    };
}

// 环境检查函数
export function envCheck() {
    const requiredVars = ['BASE_URL'];
    const missingVars = requiredVars.filter(varName => !__ENV[varName]);

    if (missingVars.length > 0) {
        console.error(`Missing required environment variables: ${missingVars.join(', ')}`);
        console.error('Set them with: k6 run -e BASE_URL=http://your-api.com k6-script.js');
        return false;
    }

    return true;
}

// 执行环境检查
if (__ENV.K6_CHECK_ENV !== 'false') {
    if (!envCheck()) {
        throw new Error('Environment check failed');
    }
}