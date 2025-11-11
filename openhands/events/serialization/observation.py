"""
Observation 序列化模块

这个模块负责处理 OpenHands 中所有 Observation（观察）类型的序列化和反序列化。
Observation 代表环境对 Agent 动作的响应和反馈，包括：

1. 命令执行结果：bash 命令输出、Python 代码执行结果
2. 文件操作结果：文件读取内容、写入确认、编辑结果
3. 浏览器操作结果：页面内容、交互反馈
4. Agent 状态变化：思考过程、状态改变、委托结果
5. 系统反馈：成功、错误、拒绝、下载等
6. 特殊观察：任务跟踪、循环检测、MCP 响应等

主要功能：
- 维护所有 Observation 类型的注册表
- 处理 Observation 的反序列化（从字典创建 Observation 对象）
- 处理向后兼容性和废弃字段
- 处理复杂对象（如元数据、枚举）的转换
"""

import copy
from typing import Any

from openhands.events.event import RecallType
from openhands.events.observation.agent import (
    AgentCondensationObservation,  # Agent 内容压缩观察
    AgentStateChangedObservation,  # Agent 状态变更观察
    AgentThinkObservation,  # Agent 思考过程观察
    MicroagentKnowledge,  # 微代理知识对象
    RecallObservation,  # 回忆/检索观察
)
from openhands.events.observation.browse import (
    BrowserOutputObservation,  # 浏览器输出观察
)
from openhands.events.observation.commands import (
    CmdOutputMetadata,  # 命令输出元数据
    CmdOutputObservation,  # 命令输出观察
    IPythonRunCellObservation,  # IPython 代码执行观察
)
from openhands.events.observation.delegate import (
    AgentDelegateObservation,  # Agent 委托观察
)
from openhands.events.observation.empty import (
    NullObservation,  # 空观察
)
from openhands.events.observation.error import ErrorObservation  # 错误观察
from openhands.events.observation.file_download import (
    FileDownloadObservation,  # 文件下载观察
)
from openhands.events.observation.files import (
    FileEditObservation,  # 文件编辑观察
    FileReadObservation,  # 文件读取观察
    FileWriteObservation,  # 文件写入观察
)
from openhands.events.observation.loop_recovery import (
    LoopDetectionObservation,  # 循环检测观察
)
from openhands.events.observation.mcp import MCPObservation  # MCP 协议观察
from openhands.events.observation.observation import Observation  # 基础观察类
from openhands.events.observation.reject import UserRejectObservation  # 用户拒绝观察
from openhands.events.observation.success import SuccessObservation  # 成功观察
from openhands.events.observation.task_tracking import (
    TaskTrackingObservation,  # 任务跟踪观察
)

# 所有支持的 Observation 类型的元组
# 这个元组定义了 OpenHands 系统中所有可用的 Observation 类型
observations = (
    NullObservation,  # 空观察（无实际内容）
    CmdOutputObservation,  # 命令执行输出
    IPythonRunCellObservation,  # IPython 代码执行结果
    BrowserOutputObservation,  # 浏览器操作结果
    FileReadObservation,  # 文件读取结果
    FileWriteObservation,  # 文件写入结果
    FileEditObservation,  # 文件编辑结果
    AgentDelegateObservation,  # Agent 委托结果
    SuccessObservation,  # 成功执行反馈
    ErrorObservation,  # 错误信息
    AgentStateChangedObservation,  # Agent 状态变更通知
    UserRejectObservation,  # 用户拒绝反馈
    AgentCondensationObservation,  # Agent 内容压缩结果
    AgentThinkObservation,  # Agent 思考过程
    RecallObservation,  # 回忆/检索结果
    MCPObservation,  # MCP 协议响应
    FileDownloadObservation,  # 文件下载结果
    TaskTrackingObservation,  # 任务跟踪状态
    LoopDetectionObservation,  # 循环检测结果
)

# Observation 类型名称到类的映射字典
# 用于根据字符串类型名称快速查找对应的 Observation 类
# 例如：'run' -> CmdOutputObservation, 'read' -> FileReadObservation
OBSERVATION_TYPE_TO_CLASS = {
    observation_class.observation: observation_class  # type: ignore[attr-defined]
    for observation_class in observations
}


def _update_cmd_output_metadata(
    metadata: dict[str, Any] | CmdOutputMetadata | None, **kwargs: Any
) -> dict[str, Any] | CmdOutputMetadata:
    """更新 CmdOutputObservation 的元数据。

    这是一个辅助函数，用于处理命令输出观察的元数据更新。
    支持多种输入格式，确保元数据能够正确更新或创建。

    参数:
        metadata: 现有的元数据，可以是 None、字典或 CmdOutputMetadata 实例
        **kwargs: 要更新的键值对

    返回:
        dict[str, Any] | CmdOutputMetadata: 更新后的元数据

    处理逻辑:
    - 如果 metadata 是 None，创建新的 CmdOutputMetadata 实例
    - 如果 metadata 是字典，直接更新字典
    - 如果 metadata 是 CmdOutputMetadata 实例，更新实例属性
    """
    if metadata is None:
        return CmdOutputMetadata(**kwargs)

    if isinstance(metadata, dict):
        metadata.update(**kwargs)
    elif isinstance(metadata, CmdOutputMetadata):
        for key, value in kwargs.items():
            setattr(metadata, key, value)
    return metadata


def handle_observation_deprecated_extras(extras: dict) -> dict:
    """处理 Observation 额外属性中的废弃字段。

    这个函数负责处理向后兼容性，将废弃的字段转换为新的格式，
    确保旧版本的序列化数据能够正确反序列化。

    参数:
        extras (dict): Observation 的额外属性字典

    返回:
        dict: 处理后的额外属性字典

    处理的废弃字段：
    1. exit_code: 已废弃，转换为 metadata.exit_code
    2. command_id: 已废弃，转换为 metadata.pid
    3. formatted_output_and_error: 已完全废弃，直接移除
    """
    # 这些字段在 https://github.com/OpenHands/OpenHands/pull/4881 中被废弃

    # exit_code 废弃处理：转换为元数据中的 exit_code
    if 'exit_code' in extras:
        extras['metadata'] = _update_cmd_output_metadata(
            extras.get('metadata', None), exit_code=extras.pop('exit_code')
        )

    # command_id 废弃处理：转换为元数据中的 pid
    if 'command_id' in extras:
        extras['metadata'] = _update_cmd_output_metadata(
            extras.get('metadata', None), pid=extras.pop('command_id')
        )

    # formatted_output_and_error 在 https://github.com/OpenHands/OpenHands/pull/6671 中被废弃
    # 直接移除，不再使用
    if 'formatted_output_and_error' in extras:
        extras.pop('formatted_output_and_error')

    return extras


def observation_from_dict(observation: dict) -> Observation:
    """从字典数据创建 Observation 对象。

    这是 Observation 反序列化的核心函数，负责将字典格式的数据转换为
    具体的 Observation 对象。函数会进行严格的验证，处理向后兼容性，
    并正确转换各种复杂对象。

    参数:
        observation (dict): 包含 Observation 数据的字典，必须包含 'observation' 键

    返回:
        Observation: 创建的 Observation 对象

    异常:
        KeyError: 当缺少必需的键或 Observation 类型未定义时抛出

    处理的特殊字段：
    - observation: Observation 类型名称（必需）
    - content: 观察内容
    - extras: 额外属性字典
    - metadata: 命令输出元数据（针对 CmdOutputObservation）
    - recall_type: 回忆类型枚举（针对 RecallObservation）
    - microagent_knowledge: 微代理知识列表（针对 RecallObservation）
    """
    # 创建副本以避免修改原始数据
    observation = observation.copy()

    # 验证必需的 'observation' 键
    if 'observation' not in observation:
        raise KeyError(f"'observation' key is not found in {observation=}")

    # 查找对应的 Observation 类
    observation_class = OBSERVATION_TYPE_TO_CLASS.get(observation['observation'])
    if observation_class is None:
        raise KeyError(
            f"'{observation['observation']=}' is not defined. Available observations: {OBSERVATION_TYPE_TO_CLASS.keys()}"
        )

    # 移除已处理的字段
    observation.pop('observation')  # 移除类型标识
    observation.pop('message', None)  # 移除消息字段（如果存在）

    # 提取内容和额外属性
    content = observation.pop('content', '')
    extras = copy.deepcopy(observation.pop('extras', {}))

    # 处理废弃的额外属性
    extras = handle_observation_deprecated_extras(extras)

    # 针对 CmdOutputObservation 的特殊处理
    # 确保 metadata 字段是 CmdOutputMetadata 实例
    if observation_class is CmdOutputObservation:
        if 'metadata' in extras and isinstance(extras['metadata'], dict):
            # 字典转换为 CmdOutputMetadata 实例
            extras['metadata'] = CmdOutputMetadata(**extras['metadata'])
        elif 'metadata' in extras and isinstance(extras['metadata'], CmdOutputMetadata):
            # 已经是正确类型，无需处理
            pass
        else:
            # 没有 metadata，创建默认实例
            extras['metadata'] = CmdOutputMetadata()

    # 针对 RecallObservation 的特殊处理
    if observation_class is RecallObservation:
        # 处理枚举转换
        if 'recall_type' in extras:
            extras['recall_type'] = RecallType(extras['recall_type'])

        # 将 microagent_knowledge 中的字典转换为 MicroagentKnowledge 对象
        if 'microagent_knowledge' in extras and isinstance(
            extras['microagent_knowledge'], list
        ):
            extras['microagent_knowledge'] = [
                MicroagentKnowledge(**item) if isinstance(item, dict) else item
                for item in extras['microagent_knowledge']
            ]

    # 创建 Observation 对象
    obs = observation_class(content=content, **extras)

    # 确保返回的是 Observation 实例
    assert isinstance(obs, Observation)
    return obs
