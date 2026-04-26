// Jest测试配置模板
// 支持TypeScript、React、覆盖率报告、多环境配置

/** @type {import('jest').Config} */
const config = {
  // 测试环境
  testEnvironment: 'node', // 'node' 或 'jsdom' (用于React)

  // 测试文件匹配模式
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{spec,test}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/__tests__/**/*.{js,jsx,ts,tsx}'
  ],

  // 测试文件忽略模式
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/',
    '/coverage/',
    '/.next/',
    '/out/',
    '/.cache/'
  ],

  // 模块文件扩展名
  moduleFileExtensions: [
    'js',
    'jsx',
    'ts',
    'tsx',
    'json',
    'node'
  ],

  // 模块名称映射 (别名)
  moduleNameMapper: {
    // 支持路径别名 (配合tsconfig或webpack配置)
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@utils/(.*)$': '<rootDir>/src/utils/$1',
    '^@hooks/(.*)$': '<rootDir>/src/hooks/$1',
    '^@pages/(.*)$': '<rootDir>/src/pages/$1',
    '^@styles/(.*)$': '<rootDir>/src/styles/$1',
    '^@types/(.*)$': '<rootDir>/src/types/$1',

    // 支持CSS模块 (用于React项目)
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',

    // 支持图片和字体文件
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$':
      '<rootDir>/__mocks__/fileMock.js',
  },

  // 测试前设置文件
  setupFiles: [
    // 全局测试设置
  ],

  // 测试环境设置文件
  setupFilesAfterEnv: [
    // 测试框架扩展 (如jest-dom用于React测试)
    // '@testing-library/jest-dom/extend-expect'
  ],

  // 转译配置
  transform: {
    // TypeScript支持
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: 'tsconfig.json',
      isolatedModules: true,
      diagnostics: {
        warnOnly: process.env.NODE_ENV === 'test'
      }
    }],
    // JavaScript支持
    '^.+\\.(js|jsx)$': ['babel-jest', {
      presets: ['@babel/preset-env', '@babel/preset-react'],
      plugins: [
        '@babel/plugin-proposal-class-properties',
        '@babel/plugin-transform-runtime'
      ]
    }]
  },

  // 覆盖率配置
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/*.test.{js,jsx,ts,tsx}',
    '!src/**/*.spec.{js,jsx,ts,tsx}',
    '!src/**/__tests__/**',
    '!src/**/__mocks__/**',
    '!src/**/types/**',
    '!src/**/constants/**',
    '!src/setupTests.{js,jsx,ts,tsx}',
    '!src/reportWebVitals.{js,jsx,ts,tsx}'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: [
    'text',
    'text-summary',
    'lcov',
    'html',
    'json',
    'clover'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    },
    './src/components/': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90
    },
    './src/utils/': {
      branches: 95,
      functions: 95,
      lines: 95,
      statements: 95
    }
  },

  // 测试运行器配置
  testRunner: 'jest-circus/runner',
  testTimeout: 10000, // 10秒超时

  // 快照序列化器
  snapshotSerializers: [
    // 例如: 'enzyme-to-json/serializer'
  ],

  // 模块解析
  moduleDirectories: [
    'node_modules',
    'src'
  ],

  // 全局变量
  globals: {
    'ts-jest': {
      isolatedModules: true
    }
  },

  // 观察模式配置
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ],

  // 性能优化
  maxWorkers: '50%', // 使用50%的CPU核心
  cacheDirectory: '/tmp/jest_rt',

  // 测试结果输出
  verbose: true,
  reporters: [
    'default',
    ['jest-junit', {
      outputDirectory: 'test-results',
      outputName: 'junit.xml',
      ancestorSeparator: ' › ',
      uniqueOutputName: 'false',
      suiteNameTemplate: '{filepath}',
      classNameTemplate: '{classname}',
      titleTemplate: '{title}'
    }]
  ],

  // 测试环境变量
  testEnvironmentOptions: {
    url: 'http://localhost:3000'
  },

  // 预设配置 (用于特定框架)
  preset: null // 例如: 'ts-jest', 'jest-puppeteer'
};

// 环境特定的配置覆盖
if (process.env.NODE_ENV === 'test') {
  // 测试环境的特殊配置
  config.testEnvironment = 'node';
  config.maxWorkers = 1; // 单线程运行
}

if (process.env.CI === 'true') {
  // CI环境的特殊配置
  config.collectCoverage = true;
  config.coverageReporters = ['text', 'lcov', 'cobertura'];
  config.reporters = [
    'default',
    ['jest-junit', {
      outputDirectory: 'test-results',
      outputName: 'junit.xml'
    }]
  ];
}

// React项目的特殊配置
const isReactProject = () => {
  try {
    require('react');
    return true;
  } catch {
    return false;
  }
};

if (isReactProject()) {
  config.testEnvironment = 'jsdom';
  config.setupFilesAfterEnv = [
    ...(config.setupFilesAfterEnv || []),
    '@testing-library/jest-dom/extend-expect'
  ];

  config.transform['^.+\\.(js|jsx)$'] = ['babel-jest', {
    presets: [
      ['@babel/preset-env', { targets: { node: 'current' } }],
      '@babel/preset-react'
    ]
  }];
}

module.exports = config;