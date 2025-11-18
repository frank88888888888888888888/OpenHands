#!/usr/bin/env python3
"""
OpenHands 简化后端 - 最小化版本
只使用基本依赖，专注于DeepSeek API集成和事件流输出
"""

import asyncio
import json
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

# 基本依赖
try:
    import httpx
    from pydantic import BaseModel
except ImportError as e:
    print(f'缺少必要依赖: {e}')
    print('请安装: pip install httpx pydantic')
    sys.exit(1)


class EventType(Enum):
    """事件类型"""

    USER_MESSAGE = 'user_message'
    AGENT_MESSAGE = 'agent_message'
    AGENT_ACTION = 'agent_action'
    AGENT_OBSERVATION = 'agent_observation'
    AGENT_THINKING = 'agent_thinking'
    SYSTEM_MESSAGE = 'system_message'
    ERROR = 'error'


@dataclass
class Event:
    """事件数据结构"""

    type: EventType
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DeepSeekConfig(BaseModel):
    """DeepSeek API 配置"""

    api_key: str
    base_url: str = 'https://api.deepseek.com'
    model: str = 'deepseek-chat'
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 30


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json',
            },
            timeout=config.timeout,
        )

    async def chat_completion(self, messages: list[dict[str, str]]) -> str:
        """发送聊天完成请求"""
        try:
            response = await self.client.post(
                '/chat/completions',
                json={
                    'model': self.config.model,
                    'messages': messages,
                    'temperature': self.config.temperature,
                    'max_tokens': self.config.max_tokens,
                    'stream': False,
                },
            )
            response.raise_for_status()

            data = response.json()
            return data['choices'][0]['message']['content']

        except httpx.HTTPError as e:
            raise Exception(f'DeepSeek API 请求失败: {e}')
        except KeyError as e:
            raise Exception(f'DeepSeek API 响应格式错误: {e}')

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class SimpleAgent:
    """简化的AI Agent"""

    def __init__(self, deepseek_client: DeepSeekClient):
        self.client = deepseek_client
        self.conversation_history = []
        self.system_prompt = """你是一个AI助手，专门帮助用户完成各种任务。

你的能力包括：
1. 代码编写和调试
2. 文件操作和管理
3. 数据分析和处理
4. 问题解决和推理
5. 项目规划和执行

请按照以下格式回应：
1. 首先分析用户的需求
2. 制定解决方案
3. 逐步执行任务
4. 提供最终结果

在执行过程中，请详细说明你的思考过程和每一步的操作。
"""

    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({'role': role, 'content': content})

    async def process_task(self, task: str) -> str:
        """处理用户任务"""
        # 构建消息列表
        messages = [{'role': 'system', 'content': self.system_prompt}]

        # 添加对话历史（保留最近的10条消息）
        recent_history = (
            self.conversation_history[-10:]
            if len(self.conversation_history) > 10
            else self.conversation_history
        )
        messages.extend(recent_history)

        # 添加当前任务
        messages.append({'role': 'user', 'content': task})

        # 调用DeepSeek API
        response = await self.client.chat_completion(messages)

        # 更新对话历史
        self.add_message('user', task)
        self.add_message('assistant', response)

        return response


class EventStream:
    """事件流管理器"""

    def __init__(self):
        self.events: list[Event] = []
        self.callbacks: list[Callable[[Event], None]] = []

    def add_callback(self, callback: Callable[[Event], None]):
        """添加事件回调"""
        self.callbacks.append(callback)

    def emit_event(
        self, event_type: EventType, content: str, metadata: dict[str, Any] = None
    ):
        """发出事件"""
        event = Event(
            type=event_type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        self.events.append(event)

        # 调用所有回调函数
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f'事件回调错误: {e}')


class EventPrinter:
    """事件打印器"""

    def __init__(self, show_details: bool = True):
        self.show_details = show_details
        self.event_count = 0

    def __call__(self, event: Event):
        """处理事件"""
        self.event_count += 1
        timestamp = event.timestamp.strftime('%H:%M:%S')

        # 根据事件类型使用不同的颜色和图标
        icons = {
            EventType.USER_MESSAGE: '👤',
            EventType.AGENT_MESSAGE: '🤖',
            EventType.AGENT_ACTION: '⚡',
            EventType.AGENT_OBSERVATION: '👁️',
            EventType.AGENT_THINKING: '🧠',
            EventType.SYSTEM_MESSAGE: '⚙️',
            EventType.ERROR: '❌',
        }

        icon = icons.get(event.type, '📝')

        print(f'\n{icon} [{timestamp}] {event.type.value.upper()}')
        print(f'内容: {event.content}')

        if self.show_details and event.metadata:
            print(f'元数据: {json.dumps(event.metadata, ensure_ascii=False, indent=2)}')

        print('-' * 80)


class SimpleOpenHandsBackend:
    """简化的OpenHands后端"""

    def __init__(self, deepseek_api_key: str, model: str = 'deepseek-chat'):
        self.config = DeepSeekConfig(api_key=deepseek_api_key, model=model)
        self.client = DeepSeekClient(self.config)
        self.agent = SimpleAgent(self.client)
        self.event_stream = EventStream()
        self.shutdown_event = asyncio.Event()
        self.sigint_count = 0

    def add_event_callback(self, callback: Callable[[Event], None]):
        """添加事件回调"""
        self.event_stream.add_callback(callback)

    def _signal_handler(self):
        """处理中断信号"""
        self.sigint_count += 1

        if self.sigint_count == 1:
            self.event_stream.emit_event(
                EventType.SYSTEM_MESSAGE, '收到中断信号 (Ctrl+C)，正在优雅关闭...'
            )
            self.shutdown_event.set()
        else:
            self.event_stream.emit_event(
                EventType.SYSTEM_MESSAGE, '收到第二次中断信号，强制退出...'
            )
            sys.exit(1)

    async def process_task(self, task: str) -> dict[str, Any]:
        """处理任务"""
        result = {
            'success': False,
            'error': None,
            'response': None,
            'start_time': datetime.now().isoformat(),
            'event_count': 0,
        }

        try:
            # 设置信号处理器
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, self._signal_handler)

            # 发出开始事件
            self.event_stream.emit_event(
                EventType.SYSTEM_MESSAGE,
                f'开始处理任务: {task}',
                {'model': self.config.model},
            )

            # 发出用户消息事件
            self.event_stream.emit_event(EventType.USER_MESSAGE, task)

            # 发出思考事件
            self.event_stream.emit_event(
                EventType.AGENT_THINKING, '正在分析任务需求...'
            )

            # 模拟一些处理时间
            await asyncio.sleep(0.5)

            # 检查是否被中断
            if self.shutdown_event.is_set():
                result['error'] = '任务被用户中断'
                return result

            # 调用AI Agent处理任务
            self.event_stream.emit_event(
                EventType.AGENT_ACTION, '调用DeepSeek API处理任务...'
            )

            response = await self.agent.process_task(task)

            # 发出响应事件
            self.event_stream.emit_event(EventType.AGENT_MESSAGE, response)

            # 发出完成事件
            self.event_stream.emit_event(EventType.SYSTEM_MESSAGE, '任务处理完成')

            result['success'] = True
            result['response'] = response

        except Exception as e:
            error_msg = f'任务处理失败: {str(e)}'
            self.event_stream.emit_event(EventType.ERROR, error_msg)
            result['error'] = error_msg

        finally:
            result['end_time'] = datetime.now().isoformat()
            result['event_count'] = len(self.event_stream.events)

            # 清理资源
            await self.client.close()

        return result


async def main():
    """主函数"""
    print('🚀 OpenHands 简化后端启动中...')

    # 检查API密钥
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    if not deepseek_api_key:
        print('❌ 错误: 请设置环境变量 DEEPSEEK_API_KEY')
        print("例如: export DEEPSEEK_API_KEY='your-api-key-here'")
        sys.exit(1)

    # 获取任务
    if len(sys.argv) < 2:
        print("📝 用法: python simple_backend.py '任务描述'")
        print("例如: python simple_backend.py '创建一个简单的Python计算器程序'")
        sys.exit(1)

    task = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else 'deepseek-chat'

    # 创建后端实例
    backend = SimpleOpenHandsBackend(deepseek_api_key, model)

    # 添加事件打印器
    event_printer = EventPrinter(show_details=True)
    backend.add_event_callback(event_printer)

    print(f'📋 任务: {task}')
    print(f'🤖 模型: {model}')
    print('=' * 80)

    # 处理任务
    try:
        result = await backend.process_task(task)

        print('\n' + '=' * 80)
        print('📊 任务执行结果:')
        print(f'✅ 成功: {result["success"]}')
        print(f'⏰ 开始时间: {result["start_time"]}')
        print(f'⏰ 结束时间: {result["end_time"]}')
        print(f'📈 事件总数: {result["event_count"]}')

        if result['error']:
            print(f'❌ 错误: {result["error"]}')

        if result['response']:
            print('\n🎯 AI响应:')
            print(result['response'])

    except KeyboardInterrupt:
        print('\n⚠️ 任务被用户中断')
    except Exception as e:
        print(f'\n❌ 执行错误: {e}')
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
