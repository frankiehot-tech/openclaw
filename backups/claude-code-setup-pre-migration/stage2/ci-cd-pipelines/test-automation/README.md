# 测试自动化配置模板

本目录包含各种测试框架的配置文件模板，用于CI/CD流水线中的测试自动化。

## 可用配置文件

### 1. JavaScript/TypeScript测试 (Jest)
- **文件**: `jest.config.js`
- **描述**: Jest测试配置模板，支持TypeScript、React、覆盖率报告和多环境配置
- **特点**:
  - 支持TypeScript和React
  - 路径别名配置
  - CSS模块模拟
  - 覆盖率报告
  - 快照测试
  - 多环境配置（开发、测试、CI）

### 2. Python测试 (Pytest)
- **文件**: `pytest.ini`
- **描述**: Pytest配置模板，支持Python项目单元测试、集成测试和覆盖率报告
- **特点**:
  - 测试发现配置
  - 覆盖率报告
  - 测试标记（unit, integration, slow）
  - 并行测试执行
  - 多环境配置

### 3. 端到端测试 (Cypress)
- **文件**: `cypress.config.js`
- **描述**: Cypress端到端测试配置，支持组件测试和E2E测试
- **特点**:
  - 组件测试配置
  - E2E测试配置
  - 浏览器支持（Chrome, Firefox, Edge, Electron）
  - 视频录制和截图
  - 多环境配置

### 4. 性能测试 (k6)
- **文件**: `k6-script.js`
- **描述**: k6性能测试脚本模板，支持负载测试、压力测试和峰值测试
- **特点**:
  - 多种测试场景：烟雾测试、负载测试、压力测试、峰值测试
  - 自定义指标和阈值
  - 多环境配置
  - 结果输出格式

### 5. Java/Kotlin测试 (JUnit 5)
- **文件**: `junit-platform.properties`
- **描述**: JUnit Platform配置，用于JUnit 5测试执行
- **特点**:
  - 并行测试执行
  - 测试发现配置
  - 超时配置
  - 扩展自动检测

### 6. Maven项目测试 (Surefire插件)
- **文件**: `maven-surefire-config.xml`
- **描述**: Maven Surefire插件配置模板，用于Java项目单元测试
- **特点**:
  - 测试过滤和包含/排除规则
  - 并行测试执行
  - 报告配置
  - 系统属性和环境变量配置

### 7. Gradle项目测试
- **文件**: `gradle-test-config.gradle`
- **描述**: Gradle测试配置模板，用于Java/Kotlin项目
- **特点**:
  - JUnit平台配置
  - 并行执行配置
  - 测试覆盖率报告（JaCoCo）
  - 测试任务变体（unitTest, integrationTest, e2eTest）

## 使用方法

### 1. 直接使用
将相应的配置文件复制到您的项目中，并根据需要进行修改：

```bash
# 例如，使用Jest配置
cp jest.config.js /your-project/
```

### 2. 通过CI/CD技能包生成
在AI Assistant中使用CI/CD设计技能生成测试配置：

```
使用CI/CD设计技能
为我的JavaScript项目配置Jest测试
```

### 3. 自定义配置
每个配置文件都包含详细的注释，说明各个配置项的作用。您可以根据项目需求调整：

1. 打开配置文件
2. 查看注释说明
3. 修改相应的配置项
4. 保存并应用到项目

## 配置建议

### 测试分层
- **单元测试**: 使用Jest、Pytest、JUnit进行快速测试
- **集成测试**: 标记为`integration`或使用专用配置文件
- **端到端测试**: 使用Cypress进行UI测试
- **性能测试**: 使用k6定期运行

### CI/CD集成
- 在CI流水线中运行单元测试
- 在合并请求时运行集成测试
- 在预发布环境运行端到端测试
- 定期运行性能测试

### 环境配置
- **开发环境**: 快速反馈，并行执行
- **CI环境**: 详细报告，失败重试
- **生产环境**: 监控和告警

## 最佳实践

1. **测试命名约定**: 使用一致的命名模式（*.test.js, *.spec.js等）
2. **测试隔离**: 每个测试应该独立运行，不依赖外部状态
3. **并行执行**: 配置并行测试以提高执行速度
4. **覆盖率报告**: 设置合理的覆盖率阈值（通常80%以上）
5. **失败重试**: 在CI环境中配置失败测试的重试机制
6. **资源清理**: 测试后清理创建的资源（文件、数据库记录等）

## 故障排除

### 常见问题

1. **测试超时**: 增加测试超时时间或优化测试代码
2. **内存不足**: 增加JVM堆大小或减少并行测试数量
3. **依赖冲突**: 确保测试依赖与项目依赖版本兼容
4. **环境差异**: 使用环境变量或配置文件管理不同环境的差异

### 调试建议

- 启用详细日志输出
- 检查测试发现模式
- 验证测试依赖
- 检查环境变量配置

## 相关资源

- [Jest文档](https://jestjs.io/)
- [Pytest文档](https://docs.pytest.org/)
- [Cypress文档](https://docs.cypress.io/)
- [k6文档](https://k6.io/docs/)
- [JUnit 5文档](https://junit.org/junit5/)
- [Maven Surefire插件文档](https://maven.apache.org/surefire/maven-surefire-plugin/)
- [Gradle测试文档](https://docs.gradle.org/current/userguide/java_testing.html)

---

*此README由CI/CD流水线技能包自动生成*