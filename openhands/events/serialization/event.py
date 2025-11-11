"""
事件序列化核心模块

这个模块提供了 OpenHands 事件系统的核心序列化功能，包括：
1. 事件对象与字典格式之间的转换
2. 轨迹数据的生成和清理
3. 向后兼容性处理
4. 元数据和指标的序列化

主要处理的数据类型：
- Event: 基础事件类，包含 Action 和 Observation
- EventSource: 事件来源（Agent、User、Environment）
- ToolCallMetadata: 工具调用元数据
- LLM Metrics: 语言模型使用指标（成本、延迟、token 使用量等）
"""

from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from openhands.events import Event, EventSource
from openhands.events.serialization.action import action_from_dict
from openhands.events.serialization.observation import observation_from_dict
from openhands.events.serialization.utils import remove_fields
from openhands.events.tool import ToolCallMetadata
from openhands.llm.metrics import Cost, Metrics, ResponseLatency, TokenUsage

# TODO: move `content` into `extras`
# 序列化时的顶级字段，这些字段会直接出现在序列化字典的顶层
TOP_KEYS = [
    'id',  # 事件唯一标识符
    'timestamp',  # 事件时间戳
    'source',  # 事件来源（Agent/User/Environment）
    'message',  # 事件消息内容
    'cause',  # 导致此事件的原因事件ID
    'action',  # 动作类型（如果是Action事件）
    'observation',  # 观察类型（如果是Observation事件）
    'tool_call_metadata',  # 工具调用元数据
    'llm_metrics',  # LLM使用指标
]

# 这些字段在事件对象中以下划线前缀存储（私有属性）
UNDERSCORE_KEYS = [
    'id',  # _id
    'timestamp',  # _timestamp
    'source',  # _source
    'cause',  # _cause
    'tool_call_metadata',  # _tool_call_metadata
    'llm_metrics',  # _llm_metrics
]

# 生成轨迹数据时需要从 extras 中删除的字段
# 这些字段通常包含大量数据或敏感信息，不适合包含在训练轨迹中
DELETE_FROM_TRAJECTORY_EXTRAS = {
    'dom_object',  # DOM对象（浏览器相关）
    'axtree_object',  # 可访问性树对象
    'active_page_index',  # 活动页面索引
    'last_browser_action',  # 最后的浏览器动作
    'last_browser_action_error',  # 最后的浏览器动作错误
    'focused_element_bid',  # 聚焦元素的浏览器ID
    'extra_element_properties',  # 额外的元素属性
}

# 生成轨迹数据时需要删除的字段（包括截图）
# 截图数据通常很大，在某些情况下需要排除
DELETE_FROM_TRAJECTORY_EXTRAS_AND_SCREENSHOTS = DELETE_FROM_TRAJECTORY_EXTRAS | {
    'screenshot',  # 截图数据（base64编码）
    'set_of_marks',  # 标记集合（浏览器相关）
}


def event_from_dict(data: dict[str, Any]) -> 'Event':
    """从字典数据创建事件对象。

    这是事件反序列化的核心函数，能够自动识别事件类型（Action 或 Observation）
    并创建相应的事件对象。同时处理各种元数据的反序列化，包括时间戳、事件来源、
    工具调用元数据和 LLM 指标等。

    参数:
        data (dict[str, Any]): 包含事件数据的字典

    返回:
        Event: 创建的事件对象（Action 或 Observation 的子类）

    异常:
        ValueError: 当无法识别事件类型时抛出

    处理的特殊字段:
    - timestamp: 时间戳，支持 datetime 对象转换为 ISO 格式
    - source: 事件来源，转换为 EventSource 枚举
    - tool_call_metadata: 工具调用元数据，转换为 ToolCallMetadata 对象
    - llm_metrics: LLM 指标，重建完整的 Metrics 对象
    """
    evt: Event

    # 根据字典中的键自动识别事件类型
    if 'action' in data:
        # 包含 'action' 键的是 Action 事件
        evt = action_from_dict(data)
    elif 'observation' in data:
        # 包含 'observation' 键的是 Observation 事件
        evt = observation_from_dict(data)
    else:
        # 无法识别的事件类型
        raise ValueError(f'Unknown event type: {data}')

    # 处理需要特殊反序列化的私有属性
    for key in UNDERSCORE_KEYS:
        if key in data:
            value = data[key]

            # 时间戳处理：如果是 datetime 对象，转换为 ISO 格式字符串
            if key == 'timestamp' and isinstance(value, datetime):
                value = value.isoformat()

            # 事件来源处理：转换为 EventSource 枚举
            if key == 'source':
                value = EventSource(value)

            # 工具调用元数据处理：从字典创建 ToolCallMetadata 对象
            if key == 'tool_call_metadata':
                value = ToolCallMetadata(**value)

            # LLM 指标处理：重建完整的 Metrics 对象
            if key == 'llm_metrics':
                metrics = Metrics()
                if isinstance(value, dict):
                    # 设置累计成本
                    metrics.accumulated_cost = value.get('accumulated_cost', 0.0)
                    # 设置每任务最大预算（如果可用）
                    metrics.max_budget_per_task = value.get('max_budget_per_task')

                    # 重建成本记录列表
                    for cost in value.get('costs', []):
                        metrics._costs.append(Cost(**cost))

                    # 重建响应延迟记录列表
                    metrics.response_latencies = [
                        ResponseLatency(**latency)
                        for latency in value.get('response_latencies', [])
                    ]

                    # 重建 token 使用记录列表
                    metrics.token_usages = [
                        TokenUsage(**usage) for usage in value.get('token_usages', [])
                    ]

                    # 设置累计 token 使用量（如果可用）
                    if 'accumulated_token_usage' in value:
                        metrics._accumulated_token_usage = TokenUsage(
                            **value.get('accumulated_token_usage', {})
                        )
                value = metrics

            # 设置私有属性（以下划线前缀）
            setattr(evt, '_' + key, value)

    return evt


def _convert_pydantic_to_dict(obj: BaseModel | dict) -> dict:
    """将 Pydantic 模型转换为字典。

    这是一个辅助函数，用于处理序列化过程中可能遇到的 Pydantic 模型对象。
    如果对象是 Pydantic 模型，则调用其 model_dump() 方法转换为字典；
    如果已经是字典，则直接返回。

    参数:
        obj (BaseModel | dict): 要转换的对象

    返回:
        dict: 转换后的字典
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    return obj


def event_to_dict(event: 'Event') -> dict:
    """将事件对象转换为字典格式。

    这是事件序列化的核心函数，将事件对象转换为可以存储或传输的字典格式。
    函数会处理各种特殊字段的序列化，包括时间戳、枚举值、Pydantic 模型等，
    并确保向后兼容性。

    参数:
        event (Event): 要序列化的事件对象

    返回:
        dict: 序列化后的字典

    异常:
        ValueError: 当事件既不是 Action 也不是 Observation 时抛出

    序列化规则:
    - Action 事件：参数放在 'args' 字段中，超时信息单独处理
    - Observation 事件：内容放在 'content' 字段，其他属性放在 'extras' 中
    - 特殊字段处理：时间戳转 ISO 格式，枚举转值，Pydantic 模型转字典
    """
    # 将事件对象转换为字典（包含所有字段）
    props = asdict(event)
    d = {}

    # 处理顶级字段
    for key in TOP_KEYS:
        # 优先使用公共属性，如果不存在则使用私有属性（下划线前缀）
        if hasattr(event, key) and getattr(event, key) is not None:
            d[key] = getattr(event, key)
        elif hasattr(event, f'_{key}') and getattr(event, f'_{key}') is not None:
            d[key] = getattr(event, f'_{key}')

        # 特殊字段处理

        # ID 处理：如果是无效 ID (-1)，则不包含在序列化结果中
        if key == 'id' and d.get('id') == -1:
            d.pop('id', None)

        # 时间戳处理：datetime 对象转换为 ISO 格式字符串
        if key == 'timestamp' and 'timestamp' in d:
            if isinstance(d['timestamp'], datetime):
                d['timestamp'] = d['timestamp'].isoformat()

        # 事件来源处理：枚举转换为字符串值
        if key == 'source' and 'source' in d:
            d['source'] = d['source'].value

        # 回忆类型处理：枚举转换为字符串值
        if key == 'recall_type' and 'recall_type' in d:
            d['recall_type'] = d['recall_type'].value

        # 工具调用元数据处理：Pydantic 模型转换为字典
        if key == 'tool_call_metadata' and 'tool_call_metadata' in d:
            d['tool_call_metadata'] = d['tool_call_metadata'].model_dump()

        # LLM 指标处理：调用 get() 方法获取序列化数据
        if key == 'llm_metrics' and 'llm_metrics' in d:
            d['llm_metrics'] = d['llm_metrics'].get()

        # 从 props 中移除已处理的顶级字段
        props.pop(key, None)

    # 向后兼容性处理：移除 None 值的字段

    # 移除 None 值的安全风险字段
    if 'security_risk' in props and props['security_risk'] is None:
        props.pop('security_risk')

    # 移除 None 值的任务完成字段（向后兼容性）
    if 'task_completed' in props and props['task_completed'] is None:
        props.pop('task_completed')

    # 根据事件类型进行不同的序列化处理
    if 'action' in d:
        # Action 事件的序列化

        # 处理 Action 的安全风险字段：将枚举转换为值并包含在 args 中
        if 'security_risk' in props:
            props['security_risk'] = props['security_risk'].value

        # 将剩余属性作为 Action 的参数
        d['args'] = props

        # 如果有超时设置，单独添加
        if event.timeout is not None:
            d['timeout'] = event.timeout

    elif 'observation' in d:
        # Observation 事件的序列化

        # 内容字段单独处理
        d['content'] = props.pop('content', '')

        # 处理额外属性：
        # - 枚举类型转换为值
        # - Pydantic 模型转换为字典
        # - 其他复杂对象也进行相应转换
        d['extras'] = {
            k: (v.value if isinstance(v, Enum) else _convert_pydantic_to_dict(v))
            for k, v in props.items()
        }

        # 为 CmdOutputObservation 包含 success 字段
        if hasattr(event, 'success'):
            d['success'] = event.success
    else:
        # 无法识别的事件类型
        raise ValueError(f'Event must be either action or observation. has: {event}')

    return d


def event_to_trajectory(event: 'Event', include_screenshots: bool = False) -> dict:
    """将事件对象转换为轨迹格式。

    轨迹格式是用于训练和分析的特殊序列化格式，会移除一些不必要的字段
    以减少数据大小和避免包含敏感信息。这个函数基于 event_to_dict 的结果，
    进一步清理数据。

    参数:
        event (Event): 要转换的事件对象
        include_screenshots (bool): 是否在轨迹中包含截图数据，默认为 False

    返回:
        dict: 轨迹格式的字典

    清理规则:
    - 总是移除：DOM 对象、可访问性树、浏览器状态等大型对象
    - 可选移除：截图和标记数据（根据 include_screenshots 参数）
    """
    # 首先进行标准序列化
    d = event_to_dict(event)

    # 如果有 extras 字段，则清理不需要的字段
    if 'extras' in d:
        remove_fields(
            d['extras'],
            # 根据是否包含截图选择不同的清理规则
            DELETE_FROM_TRAJECTORY_EXTRAS
            if include_screenshots
            else DELETE_FROM_TRAJECTORY_EXTRAS_AND_SCREENSHOTS,
        )
    return d


def truncate_content(content: str, max_chars: int | None = None) -> str:
    """截断观察内容的中间部分（如果内容过长）。

    这个函数用于处理过长的观察内容，通过截断中间部分来控制内容长度，
    同时保留开头和结尾的重要信息。截断时会插入一条说明消息。

    参数:
        content (str): 要截断的内容
        max_chars (int | None): 最大字符数，如果为 None 或负数则不截断

    返回:
        str: 截断后的内容

    截断策略:
    - 保留前半部分和后半部分的内容
    - 在中间插入截断说明消息
    - 如果内容长度不超过限制，则不进行截断

    使用示例:
    >>> long_text = "A" * 1000
    >>> truncated = truncate_content(long_text, 100)
    >>> # 结果包含前50个字符 + 截断消息 + 后50个字符
    """
    # 如果没有设置最大字符数，或内容长度未超过限制，或最大字符数为负数，则不截断
    if max_chars is None or len(content) <= max_chars or max_chars < 0:
        return content

    # 截断中间部分并包含一条给 LLM 的说明消息
    half = max_chars // 2
    return (
        content[:half]
        + '\n[... Observation truncated due to length ...]\n'
        + content[-half:]
    )
