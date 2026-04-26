---
name: react-developer
description: React全栈开发技能包 - 组件生成、状态管理、路由配置
---

# React 全栈开发技能包

## 🎯 核心功能

提供完整的React开发工作流支持，包括：
- 🏗️ 项目初始化和脚手架
- 📦 组件和Hook智能生成
- 🎨 样式系统集成 (Tailwind/SCSS)
- 🔄 状态管理配置 (Redux/Zustand)
- 🚪 路由和导航配置 (React Router)
- 📡 API集成和数据获取
- 🧪 测试用例生成

## 🚀 快速开始

### 1. 项目初始化
```bash
# 创建新的React项目
npx create-react-app my-app --template typescript
cd my-app

# 或使用Vite (推荐)
npm create vite@latest my-app -- --template react-ts
cd my-app
```

### 2. 添加核心依赖
```bash
# 状态管理
npm install zustand @reduxjs/toolkit react-redux

# 路由
npm install react-router-dom

# 样式
npm install tailwindcss postcss autoprefixer
npm install @emotion/react @emotion/styled

# UI组件库 (选择其一)
npm install @mui/material @emotion/react @emotion/styled  # Material-UI
npm install antd                                          # Ant Design
npm install @chakra-ui/react @emotion/react @emotion/styled framer-motion  # Chakra UI

# 开发工具
npm install -D prettier eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
```

## 🛠️ 功能详解

### 1. 组件生成器

#### 函数组件模板
```typescript
import React from 'react';
import './{{ComponentName}}.css';

interface {{ComponentName}}Props {
  // 定义Props接口
  title?: string;
  onAction?: () => void;
}

const {{ComponentName}}: React.FC<{{ComponentName}}Props> = ({
  title = 'Default Title',
  onAction,
}) => {
  const [state, setState] = React.useState<string>('');

  const handleClick = () => {
    setState('Clicked');
    onAction?.();
  };

  return (
    <div className="{{component-name}}">
      <h1>{title}</h1>
      <p>State: {state}</p>
      <button onClick={handleClick}>Click me</button>
    </div>
  );
};

export default {{ComponentName}};
```

#### 类组件模板
```typescript
import React, { Component } from 'react';
import './{{ComponentName}}.css';

interface {{ComponentName}}Props {
  title?: string;
}

interface {{ComponentName}}State {
  count: number;
}

class {{ComponentName}} extends Component<{{ComponentName}}Props, {{ComponentName}}State> {
  constructor(props: {{ComponentName}}Props) {
    super(props);
    this.state = {
      count: 0,
    };
  }

  handleIncrement = () => {
    this.setState(prevState => ({
      count: prevState.count + 1,
    }));
  };

  render() {
    const { title = 'Default Title' } = this.props;
    const { count } = this.state;

    return (
      <div className="{{component-name}}">
        <h1>{title}</h1>
        <p>Count: {count}</p>
        <button onClick={this.handleIncrement}>Increment</button>
      </div>
    );
  }
}

export default {{ComponentName}};
```

### 2. Hook生成器

#### 自定义Hook模板
```typescript
import { useState, useEffect, useCallback } from 'react';

interface Use{{HookName}}Options {
  initialValue?: string;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

interface Use{{HookName}}Return {
  data: any;
  loading: boolean;
  error: Error | null;
  fetchData: () => Promise<void>;
  reset: () => void;
}

const use{{HookName}} = (options: Use{{HookName}}Options = {}): Use{{HookName}}Return => {
  const { initialValue = '', onSuccess, onError } = options;
  
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // API调用示例
      const response = await fetch('/api/endpoint');
      const result = await response.json();
      
      setData(result);
      onSuccess?.(result);
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);
      onError?.(errorObj);
    } finally {
      setLoading(false);
    }
  }, [onSuccess, onError]);

  const reset = () => {
    setData(null);
    setError(null);
    setLoading(false);
  };

  useEffect(() => {
    // 可选：组件挂载时自动获取数据
    // fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    fetchData,
    reset,
  };
};

export default use{{HookName}};
```

#### 状态管理Hook (Zustand)
```typescript
import create from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface {{StoreName}}State {
  // 状态定义
  items: string[];
  selectedItem: string | null;
  loading: boolean;
  
  // Actions
  addItem: (item: string) => void;
  removeItem: (index: number) => void;
  selectItem: (item: string) => void;
  clearItems: () => void;
  setLoading: (loading: boolean) => void;
}

const use{{StoreName}}Store = create<{{StoreName}}State>()(
  devtools(
    persist(
      (set) => ({
        // 初始状态
        items: [],
        selectedItem: null,
        loading: false,
        
        // Actions实现
        addItem: (item) =>
          set((state) => ({
            items: [...state.items, item],
          })),
          
        removeItem: (index) =>
          set((state) => ({
            items: state.items.filter((_, i) => i !== index),
          })),
          
        selectItem: (item) =>
          set(() => ({
            selectedItem: item,
          })),
          
        clearItems: () =>
          set(() => ({
            items: [],
            selectedItem: null,
          })),
          
        setLoading: (loading) =>
          set(() => ({
            loading,
          })),
      }),
      {
        name: '{{store-name}}-storage', // localStorage key
      }
    )
  )
);

export default use{{StoreName}}Store;
```

### 3. 路由配置生成

#### 路由配置文件
```typescript
// src/routes/index.tsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '../components/Layout';
import HomePage from '../pages/HomePage';
import AboutPage from '../pages/AboutPage';
import ProductsPage from '../pages/ProductsPage';
import ProductDetailPage from '../pages/ProductDetailPage';
import NotFoundPage from '../pages/NotFoundPage';
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';

// 保护路由组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = localStorage.getItem('token'); // 简化示例
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* 公共路由 */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="products/:id" element={<ProductDetailPage />} />
          <Route path="login" element={<LoginPage />} />
          
          {/* 保护路由 */}
          <Route
            path="dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          
          {/* 404页面 */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default AppRoutes;
```

### 4. API集成层

#### API客户端配置
```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 未授权，跳转到登录页
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

#### API服务示例
```typescript
// src/api/userService.ts
import apiClient from './client';

export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export const userService = {
  // 用户登录
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },
  
  // 获取用户信息
  getProfile: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/profile');
    return response.data;
  },
  
  // 更新用户信息
  updateProfile: async (userData: Partial<User>): Promise<User> => {
    const response = await apiClient.put<User>('/users/profile', userData);
    return response.data;
  },
  
  // 获取用户列表
  getUsers: async (params?: { page?: number; limit?: number }): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/users', { params });
    return response.data;
  },
  
  // 注销
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
    localStorage.removeItem('token');
  },
};
```

### 5. 样式配置

#### Tailwind CSS配置
```javascript
// tailwind.config.js
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
};
```

### 6. 测试配置

#### Jest + React Testing Library配置
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(gif|ttf|eot|svg|png)$': '<rootDir>/test/__mocks__/fileMock.js',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/reportWebVitals.ts',
    '!src/setupTests.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

#### 组件测试模板
```typescript
// src/components/__tests__/Button.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Button from '../Button';

describe('Button', () => {
  it('渲染按钮文本', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('点击时调用onClick处理程序', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('禁用时不能点击', () => {
    const handleClick = jest.fn();
    render(
      <Button onClick={handleClick} disabled>
        Click me
      </Button>
    );
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).not.toHaveBeenCalled();
  });
});
```

## 📁 项目结构推荐

```
my-react-app/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── api/
│   │   ├── client.ts
│   │   ├── userService.ts
│   │   └── productService.ts
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button/
│   │   │   ├── Input/
│   │   │   └── Modal/
│   │   ├── layout/
│   │   │   ├── Header/
│   │   │   ├── Footer/
│   │   │   └── Sidebar/
│   │   └── features/
│   │       ├── Auth/
│   │       └── Dashboard/
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── useApi.ts
│   ├── pages/
│   │   ├── HomePage/
│   │   ├── LoginPage/
│   │   └── DashboardPage/
│   ├── store/
│   │   ├── index.ts
│   │   ├── userSlice.ts
│   │   └── productSlice.ts
│   ├── styles/
│   │   ├── global.css
│   │   └── variables.css
│   ├── utils/
│   │   ├── constants.ts
│   │   └── helpers.ts
│   ├── routes/
│   │   └── index.tsx
│   ├── App.tsx
│   └── index.tsx
├── .env
├── .eslintrc.js
├── .prettierrc
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

## 🚀 使用示例

### 场景1: 创建新React项目
```
用户: "创建一个新的React TypeScript项目，使用Vite和Tailwind CSS"

技能自动执行:
1. npm create vite@latest my-app -- --template react-ts
2. cd my-app
3. npm install tailwindcss postcss autoprefixer
4. npx tailwindcss init -p
5. 配置tailwind.config.js和index.css
6. 创建基础项目结构
```

### 场景2: 生成用户管理组件
```
用户: "生成一个用户管理表格组件，包含搜索、排序和分页"

技能自动执行:
1. 生成UserTable组件TSX文件
2. 生成对应的样式文件
3. 生成useUserTable Hook
4. 生成测试文件
5. 集成到路由和API服务
```

### 场景3: 配置状态管理
```
用户: "为购物车功能配置Zustand状态管理"

技能自动执行:
1. 创建cartStore.ts Zustand store
2. 定义状态接口和actions
3. 配置持久化中间件
4. 生成使用示例
5. 集成到购物车组件
```

## 🔧 集成到AI Assistant工作流

### 智能识别React开发需求
当用户描述包含以下关键词时自动触发：
- "React组件"、"React项目"、"React Hook"
- "前端界面"、"用户界面"、"UI组件"
- "状态管理"、"路由配置"、"API集成"

### 与现有技能协同
- **优化工作流**: 复杂React项目使用并行工作区
- **上下文管理**: 保留组件设计和状态管理决策
- **MCP集成**: 与GitHub、文件系统MCP协同

---

**💡 提示**: 此技能已集成到AI Assistant的智能工作流系统中，可根据项目需求自动推荐和使用相应的React开发模式。