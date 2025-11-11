"""
异步事件存储包装器模块

这个模块提供了 AsyncEventStoreWrapper 类，用于将同步的 EventStore
包装成异步迭代器。这样可以在异步环境中使用同步的事件存储操作，
避免阻塞事件循环。

主要功能：
1. 将同步的事件搜索操作转换为异步迭代器
2. 使用线程池执行器避免阻塞主事件循环
3. 提供异步迭代接口，方便在 async/await 代码中使用

使用场景：
- 在异步 Web 应用中流式传输事件数据
- 异步处理大量事件而不阻塞其他操作
- 与异步框架（如 FastAPI、aiohttp）集成
- 实现事件的实时推送和订阅功能

设计模式：
- 适配器模式：将同步接口适配为异步接口
- 迭代器模式：提供逐个访问事件的方式
- 包装器模式：在不修改原有代码的情况下增加异步功能
"""

import asyncio
from typing import Any, AsyncIterator

from openhands.events.event import Event
from openhands.events.event_store import EventStore


class AsyncEventStoreWrapper:
    """异步事件存储包装器类。

    这个类将同步的 EventStore 包装成异步迭代器，允许在异步环境中
    使用事件存储的搜索功能而不阻塞事件循环。

    属性:
        event_store (EventStore): 被包装的同步事件存储实例
        args (tuple): 传递给 search_events 方法的位置参数
        kwargs (dict): 传递给 search_events 方法的关键字参数

    使用示例:
        # 创建异步包装器
        async_wrapper = AsyncEventStoreWrapper(
            event_store,
            filter=event_filter,
            limit=100
        )

        # 异步迭代事件
        async for event in async_wrapper:
            await process_event(event)
    """

    def __init__(self, event_store: EventStore, *args: Any, **kwargs: Any) -> None:
        """初始化异步事件存储包装器。

        参数:
            event_store (EventStore): 要包装的同步事件存储实例
            *args: 传递给 search_events 方法的位置参数
            **kwargs: 传递给 search_events 方法的关键字参数

        注意:
            传入的参数将在异步迭代时传递给 event_store.search_events() 方法
        """
        self.event_store = event_store
        self.args = args
        self.kwargs = kwargs

    async def __aiter__(self) -> AsyncIterator[Event]:
        """实现异步迭代器协议。

        返回:
            AsyncIterator[Event]: 异步事件迭代器

        工作原理:
        1. 获取当前运行的事件循环
        2. 在同步的 event_store.search_events() 中迭代事件
        3. 对每个事件，使用线程池执行器异步返回
        4. 这样避免了阻塞主事件循环

        注意:
            虽然底层的 search_events() 是同步的，但通过线程池执行器
            确保了不会阻塞异步事件循环。每个事件的返回都是异步的。
        """
        loop = asyncio.get_running_loop()

        # 创建一个异步生成器来产生事件
        for event in self.event_store.search_events(*self.args, **self.kwargs):
            # 在线程池中运行阻塞的 search_events() 操作
            def get_event(e: Event = event) -> Event:
                """内部函数：返回事件对象。

                这个函数的目的是创建一个可以在线程池中执行的函数，
                避免直接在线程池中传递事件对象可能导致的问题。

                参数:
                    e (Event): 要返回的事件对象（通过默认参数捕获）

                返回:
                    Event: 相同的事件对象
                """
                return e

            # 使用线程池执行器异步返回事件，避免阻塞事件循环
            yield await loop.run_in_executor(None, get_event)
