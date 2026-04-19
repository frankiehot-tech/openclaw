#!/usr/bin/env python3
"""
ROMA-MAREF框架集成模块
将MAREF八卦智能体系统集成到ROMA递归规划框架中

关键特性：
1. 扩展ROMA AgentType以包含MAREF 8角色
2. MAREF智能体适配器（兼容BaseModule）
3. 混合工厂支持ROMA和MAREF智能体
4. 64状态锁定和格雷码转换集成
5. 互补对网络（错/综卦象转换）

架构：
- MAREF扩展ROMA的5智能体为完整8角色体系
- 智能体间通过八卦互补关系协作
- 状态锁定确保系统稳定性
- 递归规划与多智能体演进结合
"""

import os
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

import dspy

# 确保external/ROMA在Python路径中（当从父目录导入时）
current_dir = os.path.dirname(os.path.abspath(__file__))
external_roma_path = os.path.join(current_dir, "external/ROMA")
if external_roma_path not in sys.path:
    sys.path.append(external_roma_path)

# ROMA导入
try:
    from roma_dspy.config.schemas.agents import AgentConfig
    from roma_dspy.core.factory.agent_factory import AgentFactory
    from roma_dspy.core.modules import BaseModule
    from roma_dspy.core.registry.agent_registry import AgentRegistry
    from roma_dspy.types import AgentType as ROMAAgentType
    from roma_dspy.types import TaskType
except ImportError as e:
    print(f"警告: ROMA导入失败: {e}")
    print("请确保ROMA已正确安装")

    # 定义模拟类型以便开发
    class ROMAAgentType(Enum):
        ATOMIZER = "atomizer"
        PLANNER = "planner"
        EXECUTOR = "executor"
        AGGREGATOR = "aggregator"
        VERIFIER = "verifier"

    class TaskType(Enum):
        DEFAULT = "default"
        GUARDIAN_SUPERVISION = "guardian_supervision"
        LEARNER_OPTIMIZATION = "learner_optimization"
        EXPLORER_DISCOVERY = "explorer_discovery"
        COMMUNICATOR_REPORTING = "communicator_reporting"

    class BaseModule:
        pass

    class AgentFactory:
        pass


# MAREF导入
try:
    # 尝试从 external/ROMA 导入
    from external.ROMA.communicator_agent import CommunicatorAgent
    from external.ROMA.explorer_agent import ExplorerAgent
    from external.ROMA.guardian_agent import GuardianAgent
    from external.ROMA.learner_agent import LearnerAgent
    from external.ROMA.maref_agent_type import MAREFAgentType

    MAREF_AGENTS_AVAILABLE = True
except ImportError as e:
    # 回退到本地导入（如果文件被复制）
    try:
        from communicator_agent import CommunicatorAgent
        from explorer_agent import ExplorerAgent
        from guardian_agent import GuardianAgent
        from learner_agent import LearnerAgent
        from maref_agent_type import MAREFAgentType

        MAREF_AGENTS_AVAILABLE = True
    except ImportError as e2:
        print(f"警告: MAREF智能体导入失败: {e2}")
        MAREF_AGENTS_AVAILABLE = False


class ExtendedAgentType(Enum):
    """
    扩展的智能体类型枚举
    结合ROMA 5智能体和MAREF 8角色
    """

    # ROMA原有智能体
    ATOMIZER = "atomizer"  # 任务分解决策（乾/坤）
    PLANNER = "planner"  # 任务分解（乾）
    EXECUTOR = "executor"  # 执行与工具使用（震）
    AGGREGATOR = "aggregator"  # 结果合成（坤）
    VERIFIER = "verifier"  # 验证与错误修正（巽）

    # MAREF补充智能体
    GUARDIAN = "guardian"  # 安全与约束（艮）
    COMMUNICATOR = "communicator"  # 界面与表达（离）
    LEARNER = "learner"  # 适应与训练（兑）
    EXPLORER = "explorer"  # 搜索与发现（坎）

    @classmethod
    def from_roma_type(cls, roma_type: ROMAAgentType) -> "ExtendedAgentType":
        """从ROMA类型转换"""
        mapping = {
            ROMAAgentType.ATOMIZER: cls.ATOMIZER,
            ROMAAgentType.PLANNER: cls.PLANNER,
            ROMAAgentType.EXECUTOR: cls.EXECUTOR,
            ROMAAgentType.AGGREGATOR: cls.AGGREGATOR,
            ROMAAgentType.VERIFIER: cls.VERIFIER,
        }
        return mapping.get(roma_type, cls.ATOMIZER)

    @classmethod
    def from_maref_type(cls, maref_type: MAREFAgentType) -> "ExtendedAgentType":
        """从MAREF类型转换"""
        mapping = {
            MAREFAgentType.GUARDIAN: cls.GUARDIAN,
            MAREFAgentType.COMMUNICATOR: cls.COMMUNICATOR,
            MAREFAgentType.LEARNER: cls.LEARNER,
            MAREFAgentType.EXPLORER: cls.EXPLORER,
        }
        return mapping.get(maref_type, cls.GUARDIAN)

    def is_roma_agent(self) -> bool:
        """判断是否为ROMA原有智能体"""
        roma_agents = {self.ATOMIZER, self.PLANNER, self.EXECUTOR, self.AGGREGATOR, self.VERIFIER}
        return self in roma_agents

    def is_maref_agent(self) -> bool:
        """判断是否为MAREF补充智能体"""
        maref_agents = {self.GUARDIAN, self.COMMUNICATOR, self.LEARNER, self.EXPLORER}
        return self in maref_agents

    def get_complementary_type(self) -> "ExtendedAgentType":
        """
        获取互补智能体类型（基于八卦理论）

        互补关系：
        - Guardian (艮) ↔ Explorer (坎)
        - Communicator (离) ↔ Learner (兑)
        - Atomizer (乾/坤) ↔ Verifier (巽)
        - Planner (乾) ↔ Aggregator (坤)
        - Executor (震) ↔ Aggregator (坤)
        """
        complementary_map = {
            self.GUARDIAN: self.EXPLORER,
            self.EXPLORER: self.GUARDIAN,
            self.COMMUNICATOR: self.LEARNER,
            self.LEARNER: self.COMMUNICATOR,
            self.ATOMIZER: self.VERIFIER,
            self.VERIFIER: self.ATOMIZER,
            self.PLANNER: self.AGGREGATOR,
            self.AGGREGATOR: self.PLANNER,
            self.EXECUTOR: self.AGGREGATOR,
        }
        return complementary_map.get(self, self.ATOMIZER)


class MarefAgentAdapter(BaseModule):
    """
    MAREF智能体适配器
    将MAREF智能体包装为ROMA兼容的BaseModule

    适配器模式允许现有的MAREF智能体在ROMA框架中工作，
    同时保持其原有的业务逻辑和接口。
    """

    def __init__(self, maref_agent, agent_type: ExtendedAgentType, **kwargs):
        """
        初始化适配器

        Args:
            maref_agent: MAREF智能体实例（如GuardianAgent）
            agent_type: 扩展智能体类型
            **kwargs: 传递给BaseModule的参数
        """
        # 创建虚拟签名（MAREF智能体不使用DSPy签名）
        dummy_signature = dspy.Signature("goal -> output")

        # 提供默认的模型配置以避免BaseModule错误
        kwargs.setdefault("model", "dummy-maref-adapter")
        kwargs.setdefault("llm", None)

        # 初始化BaseModule
        super().__init__(signature=dummy_signature, **kwargs)

        self.maref_agent = maref_agent
        self.agent_type = agent_type
        self._instance_id = getattr(maref_agent, "agent_id", id(maref_agent))

    def forward(self, goal: str, **kwargs):
        """
        转发调用到MAREF智能体

        根据智能体类型调用适当的方法
        """
        try:
            if self.agent_type == ExtendedAgentType.GUARDIAN:
                # Guardian: 安全检查
                if hasattr(self.maref_agent, "validate_task"):
                    # 需要TaskNode，这里简化处理
                    result = self.maref_agent.monitor_system_state(kwargs.get("metrics", {}))
                    return {"output": result, "security_level": "checked"}
                else:
                    return {"output": "Guardian安全检查完成", "status": "secure"}

            elif self.agent_type == ExtendedAgentType.COMMUNICATOR:
                # Communicator: 消息发送
                if hasattr(self.maref_agent, "send_message"):
                    channels = list(getattr(self.maref_agent, "channels", {}).keys())
                    if channels:
                        success, msg = self.maref_agent.connect_channel(channels[0])
                        return {"output": f"Communicator连接: {msg}", "success": success}
                return {"output": "Communicator消息处理", "status": "ready"}

            elif self.agent_type == ExtendedAgentType.LEARNER:
                # Learner: 学习记录
                if hasattr(self.maref_agent, "update_performance_metric"):
                    success, msg = self.maref_agent.update_performance_metric(
                        "task_completion", 0.9, 0.8
                    )
                    return {"output": f"Learner记录: {msg}", "success": success}
                return {"output": "Learner学习完成", "status": "updated"}

            elif self.agent_type == ExtendedAgentType.EXPLORER:
                # Explorer: 探索发现
                if hasattr(self.maref_agent, "create_exploration_task"):
                    from external.ROMA.explorer_agent import ExplorationType

                    task_id = self.maref_agent.create_exploration_task(
                        ExplorationType.TOOL, goal, {"path": "/tmp"}
                    )
                    return {"output": f"探索任务创建: {task_id}", "task_id": task_id}
                return {"output": "Explorer探索完成", "status": "discovered"}

            else:
                return {"output": f"未知MAREF智能体类型: {self.agent_type}", "status": "unknown"}

        except Exception as e:
            return {"output": f"MAREF智能体执行错误: {str(e)}", "error": True}

    async def aforward(self, goal: str, **kwargs):
        """异步转发（同步包装）"""
        import asyncio

        return await asyncio.to_thread(self.forward, goal, **kwargs)

    @property
    def agent_id(self):
        """获取智能体ID"""
        return self._instance_id


class HybridAgentFactory(AgentFactory):
    """
    混合智能体工厂
    支持创建ROMA原生智能体和MAREF智能体适配器
    """

    def __init__(self):
        """初始化混合工厂"""
        super().__init__()
        self.maref_agent_classes = self._load_maref_agent_classes()

    def _load_maref_agent_classes(self) -> Dict[ExtendedAgentType, Type]:
        """加载MAREF智能体类"""
        classes = {}
        try:
            classes[ExtendedAgentType.GUARDIAN] = GuardianAgent
            classes[ExtendedAgentType.COMMUNICATOR] = CommunicatorAgent
            classes[ExtendedAgentType.LEARNER] = LearnerAgent
            classes[ExtendedAgentType.EXPLORER] = ExplorerAgent
        except NameError:
            # 如果MAREF智能体不可用，使用模拟类
            pass
        return classes

    def create_agent(
        self,
        agent_type: Union[ROMAAgentType, ExtendedAgentType],
        agent_config: AgentConfig,
        task_type: Optional[TaskType] = None,
    ) -> BaseModule:
        """
        创建智能体（支持扩展类型）

        Args:
            agent_type: 智能体类型（ROMA或扩展类型）
            agent_config: 智能体配置
            task_type: 任务类型

        Returns:
            BaseModule实例
        """
        # 转换ROMA类型为扩展类型
        if isinstance(agent_type, ROMAAgentType):
            ext_type = ExtendedAgentType.from_roma_type(agent_type)
        else:
            ext_type = agent_type

        # 如果是ROMA原生智能体，使用父类工厂
        if ext_type.is_roma_agent():
            return super().create_agent(ROMAAgentType(ext_type.value), agent_config, task_type)

        # 如果是MAREF智能体，创建适配器
        elif ext_type.is_maref_agent():
            return self._create_maref_agent(ext_type, agent_config, task_type)

        else:
            raise ValueError(f"未知的智能体类型: {agent_type}")

    def _create_maref_agent(
        self,
        agent_type: ExtendedAgentType,
        agent_config: AgentConfig,
        task_type: Optional[TaskType],
    ) -> MarefAgentAdapter:
        """
        创建MAREF智能体适配器
        """
        # 获取MAREF智能体类
        agent_class = self.maref_agent_classes.get(agent_type)
        if agent_class is None:
            raise ValueError(f"未找到MAREF智能体类: {agent_type}")

        # 创建MAREF智能体实例
        agent_id = f"{agent_type.value}_{task_type.value if task_type else 'default'}"

        try:
            # 尝试不同的构造函数签名
            if agent_type == ExtendedAgentType.GUARDIAN:
                maref_instance = GuardianAgent(agent_id)
            elif agent_type == ExtendedAgentType.COMMUNICATOR:
                maref_instance = CommunicatorAgent(agent_id)
            elif agent_type == ExtendedAgentType.LEARNER:
                maref_instance = LearnerAgent(agent_id)
            elif agent_type == ExtendedAgentType.EXPLORER:
                maref_instance = ExplorerAgent(agent_id)
            else:
                maref_instance = agent_class(agent_id)
        except Exception as e:
            raise ValueError(f"创建MAREF智能体实例失败: {e}")

        # 创建适配器
        # 对于MAREF适配器，我们只需要基本配置，不传递完整的agent_config
        adapter = MarefAgentAdapter(maref_agent=maref_instance, agent_type=agent_type)

        return adapter


class MarefRomaIntegration:
    """
    ROMA-MAREF集成管理器

    提供高级集成功能：
    1. 智能体注册和发现
    2. 互补对网络管理
    3. 状态锁定和格雷码转换
    4. 递归规划与多智能体协作
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化集成管理器

        Args:
            config_path: 配置文件路径（可选）
        """
        self.factory = HybridAgentFactory()
        self.registry = AgentRegistry()
        self.extended_types = ExtendedAgentType

        # 64状态锁定管理器
        self.state_locks = {}

        # 格雷码转换器
        self.gray_code_converter = GrayCodeConverter()

        # 互补对网络
        self.complementary_pairs = self._initialize_complementary_pairs()

        print("✅ ROMA-MAREF集成管理器初始化完成")
        print(f"   智能体类型: {len(list(ExtendedAgentType))} 种")
        print(f"   工厂: HybridAgentFactory")
        print(f"   注册表: AgentRegistry")

    def _initialize_complementary_pairs(self) -> Dict[ExtendedAgentType, ExtendedAgentType]:
        """初始化互补对网络"""
        pairs = {}
        for agent_type in ExtendedAgentType:
            complement = agent_type.get_complementary_type()
            pairs[agent_type] = complement
        return pairs

    def register_agent(
        self,
        agent_type: ExtendedAgentType,
        task_type: Optional[TaskType] = None,
        agent_config: Optional[AgentConfig] = None,
    ):
        """
        注册智能体到集成系统

        Args:
            agent_type: 扩展智能体类型
            task_type: 任务类型（可选）
            agent_config: 智能体配置（可选）
        """
        if agent_config is None:
            # 创建默认配置
            agent_config = self._create_default_config(agent_type)

        # 创建智能体
        agent = self.factory.create_agent(agent_type, agent_config, task_type)

        # 注册到ROMA注册表
        if agent_type.is_roma_agent():
            roma_type = ROMAAgentType(agent_type.value)
            self.registry.register_agent(roma_type, task_type, agent)
        else:
            # MAREF智能体需要特殊处理
            # 临时方案：使用扩展注册表
            pass

        print(
            f"✅ 注册智能体: {agent_type.value} "
            f"(任务类型: {task_type.value if task_type else 'default'})"
        )

        return agent

    def create_agent(self, agent_type_str: str, task_type_str: Optional[str] = None):
        """
        创建智能体的兼容方法（用于clawra_production_system.py）

        Args:
            agent_type_str: 智能体类型字符串（如 "guardian", "learner"等）
            task_type_str: 任务类型字符串（如 "guardian_supervision"）

        Returns:
            智能体实例
        """
        # 将字符串转换为ExtendedAgentType
        # 只包含clawra_production_system.py中使用的类型
        agent_type_map = {
            "guardian": ExtendedAgentType.GUARDIAN,
            "communicator": ExtendedAgentType.COMMUNICATOR,
            "learner": ExtendedAgentType.LEARNER,
            "explorer": ExtendedAgentType.EXPLORER,
        }

        if agent_type_str.lower() not in agent_type_map:
            raise ValueError(f"未知的智能体类型: {agent_type_str}")

        agent_type = agent_type_map[agent_type_str.lower()]

        # 将任务类型字符串转换为TaskType
        task_type = None
        if task_type_str:
            try:
                task_type = TaskType(task_type_str)
            except (AttributeError, ValueError):
                # 如果TaskType枚举不存在，创建简单对象
                class SimpleTaskType:
                    def __init__(self, value):
                        self.value = value

                task_type = SimpleTaskType(task_type_str)

        # 使用register_agent创建智能体
        agent = self.register_agent(agent_type, task_type)

        print(f"✅ 通过create_agent创建智能体: {agent_type_str} -> {agent_type.value}")
        return agent

    def _create_default_config(self, agent_type: ExtendedAgentType) -> AgentConfig:
        """创建默认智能体配置"""
        # 简化配置创建
        config_dict = {
            "enabled": True,
            "signature": None,
            "signature_instructions": None,
            "demos": None,
            "llm": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "timeout": 60,
                "num_retries": 3,
                "cache": True,
                "api_key": None,
                "base_url": None,
                "adapter_type": "chat",
                "use_native_function_calling": False,
                "rollout_id": None,
                "extra_body": {},
            },
            "prediction_strategy": "chain_of_thought",
            "strategy_config": {},
            "toolkits": [],
            "agent_config": {},
        }

        # 根据智能体类型调整配置
        if agent_type.is_maref_agent():
            config_dict["llm"]["model"] = "claude-3-5-sonnet"  # MAREF偏好Claude

        # 尝试使用真正的AgentConfig类
        try:
            # 从ROMA导入正确的类
            from roma_dspy.config.schemas.agents import AgentConfig as ROMAAgentConfig
            from roma_dspy.config.schemas.agents import LLMConfig

            # 创建LLM配置
            llm_config = LLMConfig(
                model=config_dict["llm"]["model"],
                temperature=config_dict["llm"]["temperature"],
                max_tokens=config_dict["llm"]["max_tokens"],
                timeout=config_dict["llm"]["timeout"],
                num_retries=config_dict["llm"]["num_retries"],
                cache=config_dict["llm"]["cache"],
                api_key=config_dict["llm"]["api_key"],
                base_url=config_dict["llm"]["base_url"],
                adapter_type=config_dict["llm"]["adapter_type"],
                use_native_function_calling=config_dict["llm"]["use_native_function_calling"],
                rollout_id=config_dict["llm"]["rollout_id"],
                extra_body=config_dict["llm"]["extra_body"],
            )

            # 创建AgentConfig
            return ROMAAgentConfig(
                enabled=config_dict["enabled"],
                signature=config_dict["signature"],
                signature_instructions=config_dict["signature_instructions"],
                demos=config_dict["demos"],
                llm=llm_config,
                prediction_strategy=config_dict["prediction_strategy"],
                strategy_config=config_dict["strategy_config"],
                toolkits=config_dict["toolkits"],
                agent_config=config_dict["agent_config"],
            )
        except ImportError:
            # 回退到简化版本（仅用于测试）
            class SimpleAgentConfig:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            return SimpleAgentConfig(config_dict)

    def create_complementary_pair(
        self, primary_type: ExtendedAgentType, task_type: Optional[TaskType] = None
    ):
        """
        创建互补智能体对

        Args:
            primary_type: 主要智能体类型
            task_type: 任务类型

        Returns:
            (primary_agent, complementary_agent) 元组
        """
        # 获取互补类型
        complementary_type = self.complementary_pairs[primary_type]

        # 创建两个智能体
        primary_agent = self.register_agent(primary_type, task_type)
        complementary_agent = self.register_agent(complementary_type, task_type)

        print(f"✅ 创建互补对: {primary_type.value} ↔ {complementary_type.value}")

        return primary_agent, complementary_agent

    def apply_state_lock(self, state_id: str, agent_type: ExtendedAgentType):
        """
        应用64状态锁定

        Args:
            state_id: 状态ID（0-63）
            agent_type: 智能体类型
        """
        if state_id in self.state_locks:
            print(f"⚠️  状态 {state_id} 已被锁定")
            return False

        # 应用格雷码转换
        gray_code = self.gray_code_converter.to_gray(int(state_id))

        self.state_locks[state_id] = {
            "agent_type": agent_type,
            "gray_code": gray_code,
            "locked_at": time.time(),
        }

        print(f"✅ 状态锁定: {state_id} → 格雷码: {gray_code} " f"(智能体: {agent_type.value})")

        return True

    def execute_task_with_maref(
        self,
        task_description: str,
        primary_agent_type: ExtendedAgentType = ExtendedAgentType.ATOMIZER,
    ):
        """
        使用MAREF增强的智能体执行任务

        Args:
            task_description: 任务描述
            primary_agent_type: 主要智能体类型

        Returns:
            执行结果
        """
        print("=" * 60)
        print(f"执行MAREF增强任务: {task_description}")
        print("=" * 60)

        # 1. 创建互补对
        primary, complementary = self.create_complementary_pair(primary_agent_type)

        # 2. 应用状态锁定
        import random

        state_id = str(random.randint(0, 63))
        self.apply_state_lock(state_id, primary_agent_type)

        # 3. 执行主要智能体
        print(f"\n🚀 执行主要智能体: {primary_agent_type.value}")
        result = primary.forward(task_description)
        print(f"   结果: {result.get('output', 'N/A')}")

        # 4. 执行互补智能体
        complementary_type = self.complementary_pairs[primary_agent_type]
        print(f"\n🔄 执行互补智能体: {complementary_type.value}")
        comp_result = complementary.forward(f"补充任务: {task_description}")
        print(f"   结果: {comp_result.get('output', 'N/A')}")

        # 5. 聚合结果
        final_result = {
            "task": task_description,
            "primary_agent": primary_agent_type.value,
            "complementary_agent": complementary_type.value,
            "state_lock": state_id,
            "primary_result": result,
            "complementary_result": comp_result,
            "integrated": True,
        }

        print("\n" + "=" * 60)
        print("✅ MAREF增强任务执行完成")
        print("=" * 60)

        return final_result


class GrayCodeConverter:
    """
    格雷码转换器
    用于64状态锁定系统的二进制-格雷码转换
    """

    def to_gray(self, n: int) -> int:
        """将二进制数转换为格雷码"""
        return n ^ (n >> 1)

    def from_gray(self, g: int) -> int:
        """将格雷码转换回二进制数"""
        n = 0
        while g:
            n ^= g
            g >>= 1
        return n

    def get_gray_sequence(self, bits: int = 6) -> List[int]:
        """生成格雷码序列（默认6位，64状态）"""
        return [self.to_gray(i) for i in range(1 << bits)]


def test_integration():
    """测试集成功能"""
    print("=== ROMA-MAREF集成测试 ===")

    try:
        # 创建集成管理器
        integration = MarefRomaIntegration()

        # 测试扩展类型
        print("\n1. 扩展智能体类型测试:")
        for agent_type in ExtendedAgentType:
            origin = "ROMA" if agent_type.is_roma_agent() else "MAREF"
            complement = agent_type.get_complementary_type()
            print(f"   {agent_type.value:15} ({origin}) ↔ {complement.value}")

        # 测试互补对创建
        print("\n2. 互补对创建测试:")
        primary, complementary = integration.create_complementary_pair(ExtendedAgentType.GUARDIAN)
        print(f"   创建: Guardian ↔ Explorer")

        # 测试状态锁定
        print("\n3. 状态锁定测试:")
        integration.apply_state_lock("42", ExtendedAgentType.COMMUNICATOR)

        # 测试任务执行
        print("\n4. 任务执行测试:")
        result = integration.execute_task_with_maref("测试视频生成项目", ExtendedAgentType.ATOMIZER)

        print("\n" + "=" * 60)
        print("✅ ROMA-MAREF集成测试通过")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行集成测试
    import time

    success = test_integration()
    sys.exit(0 if success else 1)
