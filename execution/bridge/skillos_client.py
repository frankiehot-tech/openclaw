"""
SkillOS Bridge Client — openclaw 执行层调用 SkillOS API 的客户端

openclaw (执行层) 通过此桥接层与 SkillOS (开源操作系统) 通信。

接口定义:
- 20/80 自然语言入口
- 技能蒸馏
- 碳硅就业匹配
- 利他收益分配
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

SKILLOS_BASE_URL = os.environ.get("SKILLOS_API_URL", "http://localhost:8000")


class SkillOSClient:
    """SkillOS API 客户端"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or SKILLOS_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Source": "openclaw-execution-layer",
        })

    def health_check(self) -> Dict[str, Any]:
        """检查 SkillOS 服务是否可达"""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return {"ok": resp.ok, "status": resp.status_code}
        except requests.RequestException as e:
            return {"ok": False, "error": str(e)}

    def submit_skill_input(self, input_text: str, user_id: str) -> Dict[str, Any]:
        """提交技能输入 (20/80 自然语言入口)"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/v1/skills/input",
                json={"text": input_text, "user_id": user_id},
                timeout=30,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def distill_github_repo(self, repo_url: str) -> Dict[str, Any]:
        """触发技能蒸馏 (从 GitHub 仓库提取技能)"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/v1/distillation/github",
                json={"repo_url": repo_url},
                timeout=120,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_job_match(self, skill_id: str, requirements: list) -> Dict[str, Any]:
        """碳硅就业匹配"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/v1/matching/carbon-silicon",
                json={"skill_id": skill_id, "requirements": requirements},
                timeout=30,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def calculate_distribution(self, revenue: float, contributors: list) -> Dict[str, Any]:
        """利他收益分配计算"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/v1/distribution/calculate",
                json={"revenue": revenue, "contributors": contributors},
                timeout=10,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}
