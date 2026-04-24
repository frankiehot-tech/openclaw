# SkillOS Bridge

openclaw 执行层与 SkillOS 的接口层。

## 接口定义

openclaw 通过本桥接层调用 SkillOS 的以下能力：

| openclaw 调用意图 | SkillOS API | 接口文件 |
|-------------------|-------------|---------|
| 用户技能输入 | `/api/v1/skills/input` | `skillos_client.py` |
| GitHub 技能蒸馏 | `/api/v1/distillation/github` | `skillos_client.py` |
| 碳硅就业匹配 | `/api/v1/matching/carbon-silicon` | `skillos_client.py` |
| 收益分配计算 | `/api/v1/distribution/calculate` | `skillos_client.py` |

## 使用

```python
from execution.bridge.skillos_client import SkillOSClient

client = SkillOSClient(base_url="http://localhost:8000")

# 检查服务状态
health = client.health_check()

# 提交技能输入
result = client.submit_skill_input(
    input_text="帮我写一个 Python 爬虫",
    user_id="user-001"
)
```
