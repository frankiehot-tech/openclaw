---
name: api-designer
description: API设计与开发技能包 - OpenAPI规范、REST/GraphQL设计、接口测试
---

# API 设计与开发技能包

## 🎯 核心功能

提供完整的API开发生命周期支持：
- 📝 OpenAPI/Swagger规范设计与生成
- 🔌 RESTful API设计与实现
- 🕸️ GraphQL Schema设计与解析
- 🧪 接口测试自动化 (单元/集成/E2E)
- 📚 API文档自动生成与同步
- 🔒 认证授权与安全配置
- 📊 性能测试与监控配置

## 🚀 快速开始

### 1. 项目初始化
```bash
# 创建API项目 (Node.js/Express示例)
mkdir my-api && cd my-api
npm init -y

# 安装核心依赖
npm install express cors helmet morgan
npm install @types/express @types/cors @types/node typescript ts-node -D

# 安装开发工具
npm install -D nodemon prettier eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser

# API文档工具
npm install swagger-jsdoc swagger-ui-express
npm install -D @types/swagger-jsdoc @types/swagger-ui-express

# 测试工具
npm install -D jest supertest @types/jest @types/supertest
```

### 2. TypeScript配置
```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

## 🛠️ 功能详解

### 1. OpenAPI规范生成

#### OpenAPI 3.0基础模板
```yaml
# openapi.yaml
openapi: 3.0.3
info:
  title: {{API名称}}
  description: {{API描述}}
  version: 1.0.0
  contact:
    name: {{维护者}}
    email: {{邮箱}}
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: http://localhost:3000/api
    description: 开发环境
  - url: https://api.example.com/v1
    description: 生产环境

tags:
  - name: 用户
    description: 用户管理接口
  - name: 产品
    description: 产品管理接口

paths:
  /users:
    get:
      tags: [用户]
      summary: 获取用户列表
      description: 分页获取用户列表
      parameters:
        - name: page
          in: query
          description: 页码
          required: false
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          description: 每页数量
          required: false
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: 用户列表
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

components:
  schemas:
    User:
      type: object
      required:
        - id
        - name
        - email
      properties:
        id:
          type: integer
          format: int64
          example: 1
        name:
          type: string
          example: "张三"
        email:
          type: string
          format: email
          example: "zhangsan@example.com"
        role:
          type: string
          enum: [admin, user, guest]
          example: "user"
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time

    Pagination:
      type: object
      properties:
        total:
          type: integer
          example: 100
        page:
          type: integer
          example: 1
        limit:
          type: integer
          example: 20
        totalPages:
          type: integer
          example: 5

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
```

#### 代码生成OpenAPI配置
```typescript
// src/swagger.ts
import swaggerJSDoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';
import { Express } from 'express';

const swaggerDefinition = {
  openapi: '3.0.0',
  info: {
    title: '用户管理系统 API',
    version: '1.0.0',
    description: '用户管理系统的RESTful API文档',
    contact: {
      name: 'API支持',
      email: 'support@example.com',
    },
    license: {
      name: 'MIT',
      url: 'https://opensource.org/licenses/MIT',
    },
  },
  servers: [
    {
      url: 'http://localhost:3000/api',
      description: '开发服务器',
    },
    {
      url: 'https://api.example.com/v1',
      description: '生产服务器',
    },
  ],
  components: {
    securitySchemes: {
      BearerAuth: {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
      },
    },
    schemas: {
      Error: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: false,
          },
          error: {
            type: 'object',
            properties: {
              code: {
                type: 'string',
                example: 'VALIDATION_ERROR',
              },
              message: {
                type: 'string',
                example: '输入验证失败',
              },
              details: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    field: { type: 'string' },
                    message: { type: 'string' },
                  },
                },
              },
            },
          },
        },
      },
    },
  },
};

const options = {
  swaggerDefinition,
  apis: ['./src/routes/**/*.ts', './src/models/*.ts'], // API路由和模型文件路径
};

const swaggerSpec = swaggerJSDoc(options);

export const setupSwagger = (app: Express): void => {
  app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));
  
  app.get('/api-docs.json', (req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.send(swaggerSpec);
  });
};
```

### 2. RESTful API设计与实现

#### Express.js API路由模板
```typescript
// src/routes/userRoutes.ts
import { Router, Request, Response, NextFunction } from 'express';
import { body, validationResult } from 'express-validator';
import { UserService } from '../services/userService';
import { authMiddleware } from '../middleware/auth';
import { validateRequest } from '../middleware/validate';

const router = Router();
const userService = new UserService();

/**
 * @swagger
 * /users:
 *   get:
 *     tags: [用户]
 *     summary: 获取用户列表
 *     description: 分页获取用户列表，支持搜索和排序
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - in: query
 *         name: page
 *         schema:
 *           type: integer
 *           default: 1
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           default: 20
 *       - in: query
 *         name: search
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: 用户列表
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                 data:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/User'
 *                 pagination:
 *                   $ref: '#/components/schemas/Pagination'
 */
router.get(
  '/',
  authMiddleware,
  validateRequest([
    body('page').optional().isInt({ min: 1 }),
    body('limit').optional().isInt({ min: 1, max: 100 }),
  ]),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { page = 1, limit = 20, search } = req.query;
      
      const result = await userService.getUsers({
        page: Number(page),
        limit: Number(limit),
        search: search as string,
      });
      
      res.json({
        success: true,
        data: result.users,
        pagination: result.pagination,
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @swagger
 * /users/{id}:
 *   get:
 *     tags: [用户]
 *     summary: 获取单个用户
 *     description: 根据ID获取用户详细信息
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: 用户ID
 *     responses:
 *       200:
 *         description: 用户信息
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                 data:
 *                   $ref: '#/components/schemas/User'
 *       404:
 *         description: 用户不存在
 */
router.get(
  '/:id',
  authMiddleware,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const userId = parseInt(req.params.id);
      
      const user = await userService.getUserById(userId);
      if (!user) {
        return res.status(404).json({
          success: false,
          error: {
            code: 'USER_NOT_FOUND',
            message: '用户不存在',
          },
        });
      }
      
      res.json({
        success: true,
        data: user,
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @swagger
 * /users:
 *   post:
 *     tags: [用户]
 *     summary: 创建用户
 *     description: 创建新用户
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - name
 *               - email
 *               - password
 *             properties:
 *               name:
 *                 type: string
 *                 example: "张三"
 *               email:
 *                 type: string
 *                 format: email
 *                 example: "zhangsan@example.com"
 *               password:
 *                 type: string
 *                 format: password
 *                 example: "password123"
 *               role:
 *                 type: string
 *                 enum: [admin, user, guest]
 *                 default: user
 *     responses:
 *       201:
 *         description: 用户创建成功
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                 data:
 *                   $ref: '#/components/schemas/User'
 *       400:
 *         description: 输入验证失败
 */
router.post(
  '/',
  authMiddleware,
  validateRequest([
    body('name').notEmpty().trim().isLength({ min: 2, max: 50 }),
    body('email').isEmail().normalizeEmail(),
    body('password').isLength({ min: 6 }),
    body('role').optional().isIn(['admin', 'user', 'guest']),
  ]),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: '输入验证失败',
            details: errors.array(),
          },
        });
      }
      
      const userData = req.body;
      const newUser = await userService.createUser(userData);
      
      res.status(201).json({
        success: true,
        data: newUser,
      });
    } catch (error) {
      next(error);
    }
  }
);

export default router;
```

#### 服务层模板
```typescript
// src/services/userService.ts
import { User } from '../models/User';
import { AppError } from '../utils/errors';

export interface UserCreateData {
  name: string;
  email: string;
  password: string;
  role?: string;
}

export interface PaginationOptions {
  page: number;
  limit: number;
  search?: string;
}

export interface PaginatedResult<T> {
  data: T[];
  pagination: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

export class UserService {
  async getUsers(options: PaginationOptions): Promise<PaginatedResult<User>> {
    const { page, limit, search } = options;
    const skip = (page - 1) * limit;
    
    // 构建查询条件
    const query: any = {};
    if (search) {
      query.$or = [
        { name: { $regex: search, $options: 'i' } },
        { email: { $regex: search, $options: 'i' } },
      ];
    }
    
    // 获取总数
    const total = await User.countDocuments(query);
    
    // 获取数据
    const users = await User.find(query)
      .skip(skip)
      .limit(limit)
      .sort({ createdAt: -1 })
      .select('-password');
    
    return {
      data: users,
      pagination: {
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      },
    };
  }
  
  async getUserById(id: number): Promise<User | null> {
    return await User.findById(id).select('-password');
  }
  
  async createUser(userData: UserCreateData): Promise<User> {
    // 检查邮箱是否已存在
    const existingUser = await User.findOne({ email: userData.email });
    if (existingUser) {
      throw new AppError('EMAIL_EXISTS', '邮箱已注册', 400);
    }
    
    // 创建用户
    const user = new User(userData);
    await user.save();
    
    // 移除密码字段
    const userObject = user.toObject();
    delete userObject.password;
    
    return userObject;
  }
  
  async updateUser(id: number, updateData: Partial<UserCreateData>): Promise<User | null> {
    const user = await User.findByIdAndUpdate(
      id,
      { $set: updateData },
      { new: true, runValidators: true }
    ).select('-password');
    
    return user;
  }
  
  async deleteUser(id: number): Promise<boolean> {
    const result = await User.deleteOne({ _id: id });
    return result.deletedCount > 0;
  }
}
```

### 3. GraphQL API设计

#### GraphQL Schema定义
```graphql
# src/graphql/schema.graphql
scalar DateTime
scalar JSON

type Query {
  # 用户查询
  users(
    page: Int = 1
    limit: Int = 20
    search: String
  ): UserPaginatedResult!
  
  user(id: ID!): User
  
  # 产品查询
  products(
    page: Int = 1
    limit: Int = 20
    category: String
    sortBy: ProductSortBy = CREATED_AT_DESC
  ): ProductPaginatedResult!
  
  product(id: ID!): Product
}

type Mutation {
  # 用户操作
  createUser(input: CreateUserInput!): User!
  updateUser(id: ID!, input: UpdateUserInput!): User!
  deleteUser(id: ID!): Boolean!
  
  # 认证操作
  login(email: String!, password: String!): AuthPayload!
  register(input: RegisterInput!): AuthPayload!
  logout: Boolean!
  
  # 产品操作
  createProduct(input: CreateProductInput!): Product!
  updateProduct(id: ID!, input: UpdateProductInput!): Product!
  deleteProduct(id: ID!): Boolean!
}

type Subscription {
  userCreated: User!
  productUpdated(id: ID!): Product!
}

# 用户相关类型
type User {
  id: ID!
  name: String!
  email: String!
  role: UserRole!
  createdAt: DateTime!
  updatedAt: DateTime!
  profile: UserProfile
}

type UserProfile {
  bio: String
  avatar: String
  website: String
  location: String
}

type UserPaginatedResult {
  data: [User!]!
  pagination: Pagination!
}

input CreateUserInput {
  name: String!
  email: String!
  password: String!
  role: UserRole = USER
}

input UpdateUserInput {
  name: String
  email: String
  role: UserRole
}

enum UserRole {
  ADMIN
  USER
  GUEST
}

# 产品相关类型
type Product {
  id: ID!
  name: String!
  description: String
  price: Float!
  category: String!
  stock: Int!
  images: [String!]
  createdAt: DateTime!
  updatedAt: DateTime!
}

type ProductPaginatedResult {
  data: [Product!]!
  pagination: Pagination!
}

input CreateProductInput {
  name: String!
  description: String
  price: Float!
  category: String!
  stock: Int!
  images: [String!]
}

input UpdateProductInput {
  name: String
  description: String
  price: Float
  category: String
  stock: Int
  images: [String!]
}

enum ProductSortBy {
  NAME_ASC
  NAME_DESC
  PRICE_ASC
  PRICE_DESC
  CREATED_AT_ASC
  CREATED_AT_DESC
}

# 认证相关类型
type AuthPayload {
  token: String!
  user: User!
}

input RegisterInput {
  name: String!
  email: String!
  password: String!
}

# 通用类型
type Pagination {
  total: Int!
  page: Int!
  limit: Int!
  totalPages: Int!
}
```

#### GraphQL Resolver实现
```typescript
// src/graphql/resolvers.ts
import { User } from '../models/User';
import { Product } from '../models/Product';
import { AppError } from '../utils/errors';
import { signToken, verifyToken } from '../utils/auth';

export const resolvers = {
  Query: {
    users: async (_, { page = 1, limit = 20, search }) => {
      const skip = (page - 1) * limit;
      
      const query: any = {};
      if (search) {
        query.$or = [
          { name: { $regex: search, $options: 'i' } },
          { email: { $regex: search, $options: 'i' } },
        ];
      }
      
      const [users, total] = await Promise.all([
        User.find(query)
          .skip(skip)
          .limit(limit)
          .sort({ createdAt: -1 })
          .select('-password'),
        User.countDocuments(query),
      ]);
      
      return {
        data: users,
        pagination: {
          total,
          page,
          limit,
          totalPages: Math.ceil(total / limit),
        },
      };
    },
    
    user: async (_, { id }) => {
      const user = await User.findById(id).select('-password');
      if (!user) {
        throw new AppError('USER_NOT_FOUND', '用户不存在', 404);
      }
      return user;
    },
    
    products: async (_, { page = 1, limit = 20, category, sortBy = 'CREATED_AT_DESC' }) => {
      const skip = (page - 1) * limit;
      
      const query: any = {};
      if (category) {
        query.category = category;
      }
      
      // 排序映射
      const sortMapping = {
        NAME_ASC: { name: 1 },
        NAME_DESC: { name: -1 },
        PRICE_ASC: { price: 1 },
        PRICE_DESC: { price: -1 },
        CREATED_AT_ASC: { createdAt: 1 },
        CREATED_AT_DESC: { createdAt: -1 },
      };
      
      const [products, total] = await Promise.all([
        Product.find(query)
          .skip(skip)
          .limit(limit)
          .sort(sortMapping[sortBy]),
        Product.countDocuments(query),
      ]);
      
      return {
        data: products,
        pagination: {
          total,
          page,
          limit,
          totalPages: Math.ceil(total / limit),
        },
      };
    },
    
    product: async (_, { id }) => {
      const product = await Product.findById(id);
      if (!product) {
        throw new AppError('PRODUCT_NOT_FOUND', '产品不存在', 404);
      }
      return product;
    },
  },
  
  Mutation: {
    createUser: async (_, { input }) => {
      const existingUser = await User.findOne({ email: input.email });
      if (existingUser) {
        throw new AppError('EMAIL_EXISTS', '邮箱已注册', 400);
      }
      
      const user = new User(input);
      await user.save();
      
      const userObject = user.toObject();
      delete userObject.password;
      
      return userObject;
    },
    
    updateUser: async (_, { id, input }) => {
      const user = await User.findByIdAndUpdate(
        id,
        { $set: input },
        { new: true, runValidators: true }
      ).select('-password');
      
      if (!user) {
        throw new AppError('USER_NOT_FOUND', '用户不存在', 404);
      }
      
      return user;
    },
    
    deleteUser: async (_, { id }) => {
      const result = await User.deleteOne({ _id: id });
      return result.deletedCount > 0;
    },
    
    login: async (_, { email, password }) => {
      const user = await User.findOne({ email });
      if (!user) {
        throw new AppError('INVALID_CREDENTIALS', '邮箱或密码错误', 401);
      }
      
      const isValidPassword = await user.comparePassword(password);
      if (!isValidPassword) {
        throw new AppError('INVALID_CREDENTIALS', '邮箱或密码错误', 401);
      }
      
      const token = signToken({ userId: user.id, role: user.role });
      
      const userObject = user.toObject();
      delete userObject.password;
      
      return {
        token,
        user: userObject,
      };
    },
    
    register: async (_, { input }) => {
      const existingUser = await User.findOne({ email: input.email });
      if (existingUser) {
        throw new AppError('EMAIL_EXISTS', '邮箱已注册', 400);
      }
      
      const user = new User(input);
      await user.save();
      
      const token = signToken({ userId: user.id, role: user.role });
      
      const userObject = user.toObject();
      delete userObject.password;
      
      return {
        token,
        user: userObject,
      };
    },
    
    logout: () => {
      // 在实际应用中，可能需要将token加入黑名单
      return true;
    },
  },
  
  User: {
    profile: (user) => {
      // 延迟加载用户资料
      return UserProfile.findOne({ userId: user.id });
    },
  },
};
```

### 4. API测试自动化

#### 单元测试配置
```typescript
// test/setup.ts
import { MongoMemoryServer } from 'mongodb-memory-server';
import mongoose from 'mongoose';

let mongoServer: MongoMemoryServer;

beforeAll(async () => {
  mongoServer = await MongoMemoryServer.create();
  const mongoUri = mongoServer.getUri();
  
  await mongoose.connect(mongoUri);
});

afterAll(async () => {
  await mongoose.disconnect();
  await mongoServer.stop();
});

beforeEach(async () => {
  // 清空所有集合
  const collections = mongoose.connection.collections;
  
  for (const key in collections) {
    const collection = collections[key];
    await collection.deleteMany({});
  }
});
```

#### API接口测试
```typescript
// test/api/user.test.ts
import request from 'supertest';
import app from '../../src/app';
import { User } from '../../src/models/User';

describe('用户API测试', () => {
  let authToken: string;
  let testUser: any;

  beforeEach(async () => {
    // 创建测试用户
    testUser = await User.create({
      name: '测试用户',
      email: 'test@example.com',
      password: 'password123',
      role: 'user',
    });

    // 获取认证token
    const loginRes = await request(app)
      .post('/api/auth/login')
      .send({
        email: 'test@example.com',
        password: 'password123',
      });

    authToken = loginRes.body.data.token;
  });

  describe('GET /api/users', () => {
    it('应该返回用户列表', async () => {
      const response = await request(app)
        .get('/api/users')
        .set('Authorization', `Bearer ${authToken}`);

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.pagination).toBeDefined();
    });

    it('应该支持分页查询', async () => {
      const response = await request(app)
        .get('/api/users?page=1&limit=5')
        .set('Authorization', `Bearer ${authToken}`);

      expect(response.status).toBe(200);
      expect(response.body.pagination.page).toBe(1);
      expect(response.body.pagination.limit).toBe(5);
    });

    it('应该支持搜索', async () => {
      const response = await request(app)
        .get('/api/users?search=测试')
        .set('Authorization', `Bearer ${authToken}`);

      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/users/:id', () => {
    it('应该返回指定用户', async () => {
      const response = await request(app)
        .get(`/api/users/${testUser._id}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data._id).toBe(testUser._id.toString());
    });

    it('用户不存在时应返回404', async () => {
      const response = await request(app)
        .get('/api/users/507f1f77bcf86cd799439011')
        .set('Authorization', `Bearer ${authToken}`);

      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
    });
  });

  describe('POST /api/users', () => {
    it('应该创建新用户', async () => {
      const newUser = {
        name: '新用户',
        email: 'newuser@example.com',
        password: 'password123',
        role: 'user',
      };

      const response = await request(app)
        .post('/api/users')
        .set('Authorization', `Bearer ${authToken}`)
        .send(newUser);

      expect(response.status).toBe(201);
      expect(response.body.success).toBe(true);
      expect(response.body.data.email).toBe(newUser.email);

      // 验证数据库中是否存在
      const dbUser = await User.findOne({ email: newUser.email });
      expect(dbUser).toBeTruthy();
    });

    it('邮箱已存在时应返回错误', async () => {
      const duplicateUser = {
        name: '重复用户',
        email: 'test@example.com', // 已存在的邮箱
        password: 'password123',
      };

      const response = await request(app)
        .post('/api/users')
        .set('Authorization', `Bearer ${authToken}`)
        .send(duplicateUser);

      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
    });

    it('输入验证失败时应返回错误', async () => {
      const invalidUser = {
        name: '', // 空名称
        email: 'invalid-email', // 无效邮箱
        password: '123', // 密码太短
      };

      const response = await request(app)
        .post('/api/users')
        .set('Authorization', `Bearer ${authToken}`)
        .send(invalidUser);

      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('VALIDATION_ERROR');
    });
  });
});
```

### 5. 安全与认证配置

#### JWT认证中间件
```typescript
// src/middleware/auth.ts
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { User } from '../models/User';

export interface AuthRequest extends Request {
  user?: any;
}

export const authMiddleware = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({
        success: false,
        error: {
          code: 'NO_TOKEN',
          message: '未提供认证令牌',
        },
      });
      return;
    }
    
    const token = authHeader.split(' ')[1];
    
    // 验证token
    const decoded = jwt.verify(
      token,
      process.env.JWT_SECRET || 'your-secret-key'
    ) as { userId: string; role: string };
    
    // 获取用户信息
    const user = await User.findById(decoded.userId).select('-password');
    if (!user) {
      res.status(401).json({
        success: false,
        error: {
          code: 'USER_NOT_FOUND',
          message: '用户不存在',
        },
      });
      return;
    }
    
    req.user = user;
    next();
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      res.status(401).json({
        success: false,
        error: {
          code: 'INVALID_TOKEN',
          message: '无效的认证令牌',
        },
      });
    } else {
      next(error);
    }
  }
};

export const roleMiddleware = (roles: string[]) => {
  return (req: AuthRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: {
          code: 'NOT_AUTHENTICATED',
          message: '用户未认证',
        },
      });
      return;
    }
    
    if (!roles.includes(req.user.role)) {
      res.status(403).json({
        success: false,
        error: {
          code: 'INSUFFICIENT_PERMISSIONS',
          message: '权限不足',
        },
      });
      return;
    }
    
    next();
  };
};
```

#### 速率限制配置
```typescript
// src/middleware/rateLimit.ts
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import redisClient from '../utils/redis';

export const apiLimiter = rateLimit({
  store: new RedisStore({
    client: redisClient,
    prefix: 'ratelimit:api:',
  }),
  windowMs: 15 * 60 * 1000, // 15分钟
  max: 100, // 每个IP限制100次请求
  message: {
    success: false,
    error: {
      code: 'RATE_LIMIT_EXCEEDED',
      message: '请求过于频繁，请稍后再试',
    },
  },
  standardHeaders: true,
  legacyHeaders: false,
});

export const authLimiter = rateLimit({
  store: new RedisStore({
    client: redisClient,
    prefix: 'ratelimit:auth:',
  }),
  windowMs: 60 * 60 * 1000, // 1小时
  max: 5, // 每个IP限制5次登录尝试
  message: {
    success: false,
    error: {
      code: 'AUTH_RATE_LIMIT_EXCEEDED',
      message: '登录尝试过多，请1小时后再试',
    },
  },
});
```

## 📁 项目结构推荐

```
my-api/
├── src/
│   ├── config/
│   │   ├── database.ts
│   │   └── app.ts
│   ├── controllers/
│   │   ├── userController.ts
│   │   └── authController.ts
│   ├── services/
│   │   ├── userService.ts
│   │   └── authService.ts
│   ├── models/
│   │   ├── User.ts
│   │   └── Product.ts
│   ├── routes/
│   │   ├── index.ts
│   │   ├── userRoutes.ts
│   │   └── authRoutes.ts
│   ├── middleware/
│   │   ├── auth.ts
│   │   ├── validate.ts
│   │   └── errorHandler.ts
│   ├── utils/
│   │   ├── errors.ts
│   │   ├── validation.ts
│   │   └── logger.ts
│   ├── graphql/
│   │   ├── schema.graphql
│   │   ├── resolvers.ts
│   │   └── context.ts
│   ├── docs/
│   │   └── openapi.yaml
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── app.ts
│   └── server.ts
├── .env
├── .env.example
├── .eslintrc.js
├── .prettierrc
├── tsconfig.json
├── package.json
└── README.md
```

## 🚀 使用示例

### 场景1: 创建RESTful API
```
用户: "创建一个用户管理系统的RESTful API，包含增删改查和分页搜索"

技能自动执行:
1. 生成OpenAPI规范文档
2. 创建Express.js项目结构
3. 实现用户模型和Service层
4. 创建RESTful路由控制器
5. 配置认证和权限中间件
6. 生成单元测试和集成测试
```

### 场景2: 设计GraphQL API
```
用户: "设计一个电商平台的GraphQL API，包含用户、产品、订单管理"

技能自动执行:
1. 设计GraphQL Schema
2. 创建TypeScript类型定义
3. 实现Resolver函数
4. 配置数据加载器优化查询
5. 设置订阅功能实时更新
6. 生成API测试用例
```

### 场景3: API测试自动化
```
用户: "为现有API添加完整的测试套件"

技能自动执行:
1. 分析现有API结构
2. 生成测试配置和环境
3. 创建单元测试和集成测试
4. 设置性能测试和负载测试
5. 配置持续集成流程
6. 生成测试覆盖率报告
```

## 🔧 集成到AI Assistant工作流

### 智能识别API开发需求
当用户描述包含以下关键词时自动触发：
- "API设计"、"RESTful"、"GraphQL"
- "接口文档"、"OpenAPI"、"Swagger"
- "API测试"、"接口测试"、"Postman"
- "认证授权"、"JWT"、"OAuth"

### 与现有技能协同
- **数据库MCP**: 自动生成数据模型和查询
- **前端技能**: 生成客户端API调用代码
- **部署技能**: 配置API服务器部署
- **监控技能**: 设置API性能监控

---

**💡 提示**: 此技能已集成到AI Assistant的智能工作流系统中，可根据项目需求自动推荐和使用相应的API开发模式。