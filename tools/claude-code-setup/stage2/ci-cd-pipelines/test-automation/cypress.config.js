// Cypress端到端测试配置模板
// 支持E2E测试、组件测试、多环境配置

const { defineConfig } = require('cypress')

module.exports = defineConfig({
  // 项目配置
  projectId: null, // Cypress Cloud项目ID (可选)

  // 视口配置
  viewportWidth: 1280,
  viewportHeight: 720,

  // 动画时间
  animationDistanceThreshold: 5,
  waitForAnimations: true,
  defaultCommandTimeout: 10000, // 10秒
  execTimeout: 60000, // 60秒
  pageLoadTimeout: 60000, // 60秒
  requestTimeout: 5000, // 5秒
  responseTimeout: 30000, // 30秒

  // 视频和截图配置
  video: true,
  videoCompression: 32,
  videosFolder: 'cypress/videos',
  screenshotOnRunFailure: true,
  screenshotsFolder: 'cypress/screenshots',
  trashAssetsBeforeRuns: true,

  // 重试配置
  retries: {
    runMode: 2, // CI环境重试次数
    openMode: 0  // 本地开发环境重试次数
  },

  // 环境变量
  env: {
    // 应用环境变量
    baseUrl: 'http://localhost:3000',
    apiUrl: 'http://localhost:5000/api',

    // 测试数据
    testUser: {
      email: 'test@example.com',
      password: 'Test123!'
    },

    // 功能标志
    enableExperimentalFeatures: false,

    // 第三方服务模拟
    mockExternalServices: true,

    // 性能阈值
    performanceThreshold: {
      pageLoad: 3000, // 3秒
      apiResponse: 1000 // 1秒
    }
  },

  // 实验性功能
  experimentalStudio: false,
  experimentalMemoryManagement: true,
  experimentalRunAllSpecs: true,
  experimentalCspAllowList: false,
  experimentalWebKitSupport: false,

  // 组件测试配置 (Cypress Component Testing)
  component: {
    devServer: {
      framework: 'react', // 'react', 'vue', 'angular', 'svelte'
      bundler: 'webpack' // 'webpack', 'vite'
    },
    specPattern: 'src/**/*.{spec,test,cy}.{js,jsx,ts,tsx}',
    indexHtmlFile: 'cypress/support/component-index.html'
  },

  // E2E测试配置
  e2e: {
    // 测试文件匹配模式
    specPattern: [
      'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
      'cypress/integration/**/*.{js,jsx,ts,tsx}',
      'tests/e2e/**/*.{js,jsx,ts,tsx}'
    ],

    // 排除的文件
    excludeSpecPattern: [
      '**/__snapshots__/**',
      '**/__image_snapshots__/**',
      '**/*.snap',
      '**/*.skip.{js,jsx,ts,tsx}'
    ],

    // 支持文件
    supportFile: 'cypress/support/e2e.{js,jsx,ts,tsx}',

    // 全局设置文件
    setupNodeEvents(on, config) {
      // 在这里添加插件配置

      // 自定义任务
      on('task', {
        log(message) {
          console.log(message)
          return null
        },

        table(message) {
          console.table(message)
          return null
        },

        // 数据库操作任务 (示例)
        queryDatabase(query) {
          // 这里添加数据库查询逻辑
          return Promise.resolve([])
        },

        // 文件系统操作任务 (示例)
        readFile(filename) {
          // 这里添加文件读取逻辑
          return Promise.resolve('')
        }
      })

      // 浏览器启动事件
      on('before:browser:launch', (browser = {}, launchOptions) => {
        // 浏览器启动配置
        if (browser.family === 'chromium' && browser.name !== 'electron') {
          // Chrome/Chromium特定配置
          launchOptions.args.push('--disable-dev-shm-usage')
          launchOptions.args.push('--no-sandbox')
          launchOptions.args.push('--disable-gpu')

          // 性能优化
          if (config.env.performanceMode) {
            launchOptions.args.push('--disable-extensions')
            launchOptions.args.push('--disable-background-networking')
          }
        }

        return launchOptions
      })

      // 测试运行事件
      on('after:run', (results) => {
        // 测试运行后的处理
        if (results) {
          console.log(`运行了 ${results.totalTests} 个测试`)
          console.log(`通过了 ${results.totalPassed} 个测试`)
          console.log(`失败了 ${results.totalFailed} 个测试`)
        }
      })

      // 环境特定配置
      if (config.env.environment === 'ci') {
        // CI环境配置
        config.video = true
        config.screenshotOnRunFailure = true
        config.defaultCommandTimeout = 15000
      }

      if (config.env.environment === 'local') {
        // 本地开发环境配置
        config.video = false
        config.screenshotOnRunFailure = false
      }

      return config
    }
  },

  // 浏览器配置
  chromeWebSecurity: false,
  blockHosts: [
    '*.google-analytics.com',
    '*.facebook.net',
    '*.doubleclick.net'
  ],
  modifyObstructiveCode: true,
  userAgent: null,

  // 网络配置
  numTestsKeptInMemory: 50,
  port: null,
  hosts: null,

  // 报告配置
  reporter: 'spec',
  reporterOptions: {
    mochaFile: 'cypress/results/junit-[hash].xml',
    toConsole: true,
    overwrite: false,
    html: false,
    json: true
  },

  // 并行测试配置 (需要Cypress Cloud)
  parallel: false,
  experimentalSessionAndOrigin: true,

  // 下载配置
  downloadsFolder: 'cypress/downloads',

  // 文件监控配置
  watchForFileChanges: true,

  // 场景测试配置
  scrollBehavior: 'center',

  // 截图配置
  screenshotOnRunFailure: true,
  screenshotsFolder: 'cypress/screenshots',

  // 慢速测试阈值
  slowTestThreshold: 10000, // 10秒

  // 支持的浏览器
  browsers: [
    {
      name: 'chrome',
      family: 'chromium',
      displayName: 'Chrome',
      version: 'latest',
      channel: 'stable'
    },
    {
      name: 'firefox',
      family: 'firefox',
      displayName: 'Firefox',
      version: 'latest',
      channel: 'stable'
    },
    {
      name: 'edge',
      family: 'chromium',
      displayName: 'Edge',
      version: 'latest',
      channel: 'stable'
    },
    {
      name: 'electron',
      family: 'chromium',
      displayName: 'Electron',
      version: 'latest',
      channel: 'stable'
    }
  ],

  // 测试运行器选项
  experimentalRunAllSpecs: true,
  experimentalInteractiveRunEvents: false,
  experimentalSourceRewriting: false,

  // 环境变量覆盖
  // 开发环境
  dev: {
    env: {
      baseUrl: 'http://localhost:3000',
      apiUrl: 'http://localhost:5000/api'
    }
  },

  // 测试环境
  staging: {
    env: {
      baseUrl: 'https://staging.example.com',
      apiUrl: 'https://api.staging.example.com/api'
    },
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 30000
  },

  // 生产环境
  production: {
    env: {
      baseUrl: 'https://example.com',
      apiUrl: 'https://api.example.com/api'
    },
    video: false,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 30000,
    retries: {
      runMode: 3
    }
  },

  // CI环境
  ci: {
    env: {
      environment: 'ci'
    },
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 30000,
    retries: {
      runMode: 2
    },
    reporter: 'junit',
    reporterOptions: {
      mochaFile: 'cypress/results/junit.xml'
    }
  }
})