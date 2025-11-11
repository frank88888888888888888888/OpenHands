"""
OpenHands 事件序列化模块

这个模块提供了 OpenHands 事件系统的序列化和反序列化功能。
OpenHands 中的所有交互都通过事件（Event）来表示，包括：
- Action（动作）：Agent 执行的操作，如运行命令、编辑文件等
- Observation（观察）：环境对 Action 的响应，如命令输出、文件内容等

主要功能：
1. 将事件对象转换为字典格式（序列化）
2. 将字典格式转换回事件对象（反序列化）
3. 生成用于轨迹记录的事件表示
4. 处理向后兼容性和数据格式转换

这个模块是 OpenHands 事件系统的核心组件，确保事件数据能够在不同组件间
正确传递，并能够持久化存储和恢复。
"""

from openhands.events.serialization.action import (
    action_from_dict,  # 从字典创建 Action 对象
)
from openhands.events.serialization.event import (
    event_from_dict,  # 从字典创建 Event 对象（自动识别 Action 或 Observation）
    event_to_dict,  # 将 Event 对象转换为字典
    event_to_trajectory,  # 将 Event 对象转换为轨迹格式（用于训练和分析）
)
from openhands.events.serialization.observation import (
    observation_from_dict,  # 从字典创建 Observation 对象
)

__all__ = [
    'action_from_dict',  # Action 反序列化函数
    'event_from_dict',  # Event 反序列化函数
    'event_to_dict',  # Event 序列化函数
    'event_to_trajectory',  # Event 轨迹格式转换函数
    'observation_from_dict',  # Observation 反序列化函数
]
