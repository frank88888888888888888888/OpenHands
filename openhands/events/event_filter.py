"""
事件过滤器模块

这个模块提供了 EventFilter 类，用于在事件流中过滤事件对象。
EventFilter 是一个强大的工具，可以根据多种条件筛选事件，包括：

1. 事件类型过滤：包含或排除特定类型的事件
2. 来源过滤：根据事件来源（Agent、用户、环境）筛选
3. 时间范围过滤：根据开始和结束日期筛选事件
4. 内容搜索：在事件内容中搜索特定文本
5. 隐藏状态过滤：排除标记为隐藏的事件

主要用途：
- 事件流搜索和查询
- 日志分析和调试
- 数据导出和报告生成
- 用户界面中的事件展示控制
"""

import json
from dataclasses import dataclass

from openhands.events.event import Event
from openhands.events.serialization.event import event_to_dict


@dataclass
class EventFilter:
    """事件流中 Event 对象的过滤器。

    EventFilter 提供了一种灵活的方式来根据各种条件过滤事件，
    如事件类型、来源、日期范围和内容。它可以用于根据指定的条件
    包含或排除搜索结果中的事件。

    属性:
        exclude_hidden (bool): 是否排除标记为隐藏的事件。默认为 False。
        query (str | None): 在事件内容中搜索的文本字符串。不区分大小写。默认为 None。
        include_types (tuple[type[Event], ...] | None): 要包含的事件类型元组。
            只有这些类型的事件才会通过过滤器。默认为 None（包含所有类型）。
        exclude_types (tuple[type[Event], ...] | None): 要排除的事件类型元组。
            这些类型的事件将被过滤掉。默认为 None（不排除任何类型）。
        source (str | None): 按事件来源过滤（例如 'agent'、'user'、'environment'）。
            默认为 None。
        start_date (str | None): ISO 格式的日期字符串。只有此日期之后的事件
            才会通过过滤器。默认为 None。
        end_date (str | None): ISO 格式的日期字符串。只有此日期之前的事件
            才会通过过滤器。默认为 None。

    使用示例:
        # 创建一个过滤器，只包含 Agent 的思考动作
        filter = EventFilter(
            include_types=(AgentThinkAction,),
            source='agent'
        )

        # 创建一个过滤器，搜索包含特定文本的事件
        search_filter = EventFilter(query='error')

        # 创建一个时间范围过滤器
        date_filter = EventFilter(
            start_date='2024-01-01T00:00:00Z',
            end_date='2024-01-31T23:59:59Z'
        )
    """

    exclude_hidden: bool = False
    query: str | None = None
    include_types: tuple[type[Event], ...] | None = None
    exclude_types: tuple[type[Event], ...] | None = None
    source: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    def include(self, event: Event) -> bool:
        """根据过滤条件确定是否应该包含某个事件。

        此方法检查给定的事件是否匹配所有过滤条件。
        如果任何条件失败，事件将被排除。

        参数:
            event (Event): 要根据过滤条件检查的事件对象

        返回:
            bool: 如果事件通过所有过滤条件并应该被包含则返回 True，
                  否则返回 False

        过滤逻辑:
        1. 类型包含检查：如果设置了 include_types，事件必须是指定类型之一
        2. 类型排除检查：如果设置了 exclude_types，事件不能是指定类型之一
        3. 来源检查：如果设置了 source，事件来源必须匹配
        4. 开始日期检查：如果设置了 start_date，事件时间戳必须晚于此日期
        5. 结束日期检查：如果设置了 end_date，事件时间戳必须早于此日期
        6. 隐藏状态检查：如果 exclude_hidden 为 True，隐藏事件将被排除
        7. 文本搜索检查：如果设置了 query，事件内容必须包含搜索文本
        """
        # 1. 检查事件类型是否在包含列表中
        if self.include_types and not isinstance(event, self.include_types):
            return False

        # 2. 检查事件类型是否在排除列表中
        if self.exclude_types is not None and isinstance(event, self.exclude_types):
            return False

        # 3. 检查事件来源是否匹配
        if self.source:
            if event.source is None or event.source.value != self.source:
                return False

        # 4. 检查事件时间戳是否在开始日期之后
        if (
            self.start_date
            and event.timestamp is not None
            and event.timestamp < self.start_date
        ):
            return False

        # 5. 检查事件时间戳是否在结束日期之前
        if (
            self.end_date
            and event.timestamp is not None
            and event.timestamp > self.end_date
        ):
            return False

        # 6. 检查是否需要排除隐藏事件
        if self.exclude_hidden and getattr(event, 'hidden', False):
            return False

        # 7. 在事件内容中进行文本搜索（如果提供了查询字符串）
        if self.query:
            # 将事件转换为字典格式，然后转换为 JSON 字符串进行搜索
            event_dict = event_to_dict(event)
            event_str = json.dumps(event_dict).lower()
            # 不区分大小写的文本搜索
            if self.query.lower() not in event_str:
                return False

        # 所有条件都通过，包含此事件
        return True

    def exclude(self, event: Event) -> bool:
        """根据过滤条件确定是否应该排除某个事件。

        这是 include 方法的反向操作。提供此方法是为了方便使用，
        当需要明确表达"排除"语义时使用。

        参数:
            event (Event): 要根据过滤条件检查的事件对象

        返回:
            bool: 如果事件应该被排除则返回 True，如果应该被包含则返回 False

        注意:
            此方法的返回值与 include() 方法完全相反。
            exclude(event) 等价于 not include(event)
        """
        return not self.include(event)
