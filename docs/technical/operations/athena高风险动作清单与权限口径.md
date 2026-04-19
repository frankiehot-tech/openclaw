# Athena 高风险动作清单与权限口径

## 1. 高风险动作清单

| 动作名称 | 风险性质 | 风险等级 | 描述 |
|---------|---------|---------|------|
| drag | 图标意外移动，导致桌面布局混乱；可能触发非预期排序或删除操作 | 高 | 拖拽图标进行位置调整 |
| long_press | 误触发上下文菜单或编辑模式；可能进入不可逆的操作状态 | 中 | 长按图标触发菜单或进入编辑模式 |
| multi_step_rearrangement | 多图标连续重排，错误传播范围广；恢复成本高 | 高 | 多个图标按顺序进行位置交换或重排 |
| folder_entry | 意外进入或退出文件夹；导致导航路径丢失或操作上下文错乱 | 中 | 点击进入文件夹或返回上级目录 |
| cross_page_swipe_for_rearrangement | 跨页面图标交换；可能导致图标丢失到错误页面，恢复困难 | 极高 | 通过滑动页面并拖拽图标进行跨页面重排 |

## 2. 动作准入条件表

| 动作名称 | 准入条件（全部满足） | 生效时机 | 失效条件 |
|---------|-------------------|---------|----------|
| drag | 1. `notification_closed` = true<br>2. `launcher_confirmed` = true<br>3. `icon_grid_confirmed` = true<br>4. `page1_confirmed` = true<br>5. `drag_enabled` = true | 所有条件同时为 true 时立即生效 | 任一条件变为 false 或不确定时立即失效 |
| long_press | 1. `notification_closed` = true<br>2. `launcher_confirmed` = true<br>3. `icon_grid_confirmed` = true<br>4. `long_press_enabled` = true | 所有条件同时为 true 时立即生效 | 任一条件变为 false 或不确定时立即失效 |
| multi_step_rearrangement | 1. `notification_closed` = true<br>2. `launcher_confirmed` = true<br>3. `icon_grid_confirmed` = true<br>4. `page1_confirmed` = true<br>5. `multi_step_enabled` = true | 所有条件同时为 true 时立即生效 | 任一条件变为 false 或不确定时立即失效 |
| folder_entry | 1. `notification_closed` = true<br>2. `launcher_confirmed` = true<br>3. `folder_navigation_enabled` = true<br>4. `current_folder_known` = true | 所有条件同时为 true 时立即生效 | 任一条件变为 false 或不确定时立即失效 |
| cross_page_swipe_for_rearrangement | 1. `notification_closed` = true<br>2. `launcher_confirmed` = true<br>3. `icon_grid_confirmed` = true<br>4. `page1_confirmed` = true<br>5. `page2_confirmed` = true<br>6. `cross_page_enabled` = true | 所有条件同时为 true 时立即生效 | 任一条件变为 false 或不确定时立即失效 |

## 3. 权限默认关闭原则

### 原则一：默认禁用
所有高风险动作在系统初始化时默认处于禁用状态。必须通过显式的状态确认和权限解锁流程才能启用。

### 原则二：显式条件解锁
高风险动作的权限必须通过满足明确的准入条件集合来解锁。条件必须全部满足，缺一不可。

### 原则三：权限状态记录
每个高风险动作的权限状态必须在系统状态机中有明确的布尔值记录。没有权限状态记录的高风险动作，一律视为未授权动作，禁止执行。

### 原则四：即时失效
当任一准入条件重新变为 false 或状态不确定时，对应高风险动作的权限立即失效，必须重新满足全部条件才能再次启用。

### 原则五：原子性校验
在执行任何高风险动作前，必须原子性地校验所有准入条件的当前值。校验期间状态发生变化，则视为校验失败，禁止执行。

### 原则六：独立权限域
每个高风险动作拥有独立的权限域，一个动作的权限解锁不自动授予其他动作的权限。必须分别满足各自的准入条件。

---
**版本**：1.0  
**生效日期**：2026年4月2日  
**状态**：冻结版统一标准