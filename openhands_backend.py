#!/usr/bin/env python3
"""
OpenHands 简化后端主入口
支持 DeepSeek API 和事件流输出
"""

import asyncio
import json
import os
import signal
import sys
from datetime import datetime
from typing import Any

# 添加 OpenHands 路径
sys.path.insert(0, '/workspace/project/OpenHands')

import openhands.agenthub  # noqa F401
from openhands.core.config import OpenHandsConfig, LLMConfig
from openhands.core.logger import openhands_logger as logger
from openhands.core.loop import run_agent_until_done
from openhands.core.schema import AgentState
from openhands.core.setup import (
    create_agent,
    create_controller,
    create_memory,
    create_runtime,
    generate_sid,
    get_provider_tokens,
)
from openhands.events import EventSource, EventStreamSubscriber
from openhands.events.action import MessageAction
from openhands.events.event import Event
from openhands.events.observation import AgentStateChangedObservation
from openhands.utils.async_utils import call_async_from_sync
from openhands.utils.utils import create_registry_and_conversation_stats


class OpenHandsBackend:
    """OpenHands 后端核心类"""

    def __init__(self, deepseek_api_key: str, model: str = 'deepseek-chat'):
        """
        初始化 OpenHands 后端

        Args:
            deepseek_api_key: DeepSeek API 密钥
            model: 使用的模型名称，默认为 deepseek-chat
        """
        self.deepseek_api_key = deepseek_api_key
        self.model = model
        self.config = self._create_config()
        self.event_callbacks = []
        self.shutdown_event = asyncio.Event()
        self.sigint_count = 0

    def _create_config(self) -> OpenHandsConfig:
        """创建 OpenHands 配置"""
        # 创建 LLM 配置
        llm_config = LLMConfig(
            model=self.model,
            api_key=self.deepseek_api_key,
            base_url='https://api.deepseek.com',
            temperature=0.1,
            max_output_tokens=4096,
        )

        # 创建主配置
        config = OpenHandsConfig(
            default_agent='CodeActAgent',
            runtime='local',
            max_iterations=50,
            max_budget_per_task=10.0,
            llms={'main': llm_config},
        )

        return config

    def add_event_callback(self, callback):
        """添加事件回调函数"""
        self.event_callbacks.append(callback)

    def _signal_handler(self):
        """处理中断信号"""
        self.sigint_count += 1

        if self.sigint_count == 1:
            logger.info('收到中断信号 (Ctrl+C)，正在优雅关闭...')
            logger.info('再次按 Ctrl+C 强制退出')
            self.shutdown_event.set()
        else:
            logger.info('收到第二次中断信号，强制退出...')
            sys.exit(1)

    async def process_task(self, task: str) -> dict[str, Any]:
        """
        处理单个任务

        Args:
            task: 任务描述

        Returns:
            包含执行结果的字典
        """
        logger.info(f'开始处理任务: {task}')

        # 生成会话ID
        sid = generate_sid(self.config)

        # 创建注册表和统计信息
        llm_registry, conversation_stats, config = (
            create_registry_and_conversation_stats(self.config, sid, None)
        )

        # 创建代理
        agent = create_agent(config, llm_registry)

        # 创建运行时
        repo_tokens = get_provider_tokens()
        runtime = create_runtime(
            config,
            llm_registry,
            sid=sid,
            headless_mode=True,
            agent=agent,
            git_provider_tokens=repo_tokens,
        )

        # 连接运行时
        call_async_from_sync(runtime.connect)

        # 获取事件流
        event_stream = runtime.event_stream

        # 创建内存
        memory = create_memory(
            runtime=runtime,
            event_stream=event_stream,
            sid=sid,
            selected_repository=None,
            repo_directory=None,
            conversation_instructions=None,
            working_dir=str(runtime.workspace_root),
        )

        # 创建控制器
        controller, initial_state = create_controller(
            agent, runtime, config, conversation_stats
        )

        # 设置信号处理器
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, self._signal_handler)

        # 事件处理器
        def on_event(event: Event) -> None:
            # 调用所有注册的回调函数
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f'事件回调错误: {e}')

            # 处理用户输入请求
            if isinstance(event, AgentStateChangedObservation):
                if event.agent_state == AgentState.AWAITING_USER_INPUT:
                    # 自动继续执行
                    message = (
                        'Please continue with your approach. '
                        'If you think the task is complete, please finish.'
                    )
                    action = MessageAction(content=message)
                    event_stream.add_event(action, EventSource.USER)

        # 订阅事件
        event_stream.subscribe(EventStreamSubscriber.MAIN, on_event, sid)

        # 添加初始任务
        initial_action = MessageAction(content=task)
        event_stream.add_event(initial_action, EventSource.USER)

        # 定义结束状态
        end_states = [
            AgentState.FINISHED,
            AgentState.REJECTED,
            AgentState.ERROR,
            AgentState.PAUSED,
            AgentState.STOPPED,
        ]

        result = {
            'success': False,
            'error': None,
            'final_state': None,
            'session_id': sid,
            'start_time': datetime.now().isoformat(),
        }

        try:
            # 创建代理任务
            agent_task = asyncio.create_task(
                run_agent_until_done(controller, runtime, memory, end_states)
            )

            # 等待完成或中断
            done, pending = await asyncio.wait(
                [agent_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 取消待处理的任务
            for task_obj in pending:
                task_obj.cancel()

            await asyncio.gather(*pending, return_exceptions=True)

            # 检查是否被中断
            if self.shutdown_event.is_set():
                logger.info('任务被用户中断')
                result['error'] = 'Task interrupted by user'
            else:
                result['success'] = True
                logger.info('任务执行完成')

        except Exception as e:
            logger.error(f'任务执行异常: {e}')
            result['error'] = str(e)

        finally:
            # 清理资源
            try:
                await controller.close(set_stop_state=False)
                event_stream.close()
                runtime.close()
            except Exception as e:
                logger.warning(f'资源清理错误: {e}')

            # 获取最终状态
            final_state = controller.get_state()
            result['final_state'] = (
                final_state.agent_state.value if final_state else None
            )
            result['end_time'] = datetime.now().isoformat()

        return result


class EventStreamPrinter:
    """事件流打印器 - 实时输出AI Agent的操作过程"""

    def __init__(self, show_details: bool = True):
        self.show_details = show_details
        self.event_count = 0

    def __call__(self, event: Event):
        """事件回调函数"""
        self.event_count += 1
        timestamp = datetime.now().strftime('%H:%M:%S')

        print(f'\n[{timestamp}] 事件 #{self.event_count}: {event.__class__.__name__}')

        # 根据事件类型显示不同信息
        if hasattr(event, 'content') and event.content:
            print(f'内容: {event.content}')

        if hasattr(event, 'command') and event.command:
            print(f'命令: {event.command}')

        if hasattr(event, 'path') and event.path:
            print(f'路径: {event.path}')

        if hasattr(event, 'agent_state'):
            print(f'代理状态: {event.agent_state}')

        if self.show_details and hasattr(event, '__dict__'):
            # 显示事件的详细信息（排除一些内部属性）
            details = {
                k: v
                for k, v in event.__dict__.items()
                if not k.startswith('_')
                and k not in ['content', 'command', 'path', 'agent_state']
            }
            if details:
                print(
                    f'详细信息: {json.dumps(details, default=str, ensure_ascii=False, indent=2)}'
                )

        print('-' * 80)


def main():
    """主函数"""
    print('OpenHands 简化后端启动中...')

    # 检查环境变量中的API密钥
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    if not deepseek_api_key:
        print('错误: 请设置环境变量 DEEPSEEK_API_KEY')
        print("例如: export DEEPSEEK_API_KEY='your-api-key-here'")
        sys.exit(1)

    # 获取命令行参数
    if len(sys.argv) < 2:
        print("用法: python openhands_backend.py '任务描述'")
        print("例如: python openhands_backend.py '创建一个简单的Python计算器程序'")
        sys.exit(1)

    task = sys.argv[1]

    # 创建后端实例
    backend = OpenHandsBackend(deepseek_api_key)

    # 添加事件流打印器
    event_printer = EventStreamPrinter(show_details=True)
    backend.add_event_callback(event_printer)

    print(f'任务: {task}')
    print(f'模型: {backend.model}')
    print('=' * 80)

    # 运行任务
    try:
        result = asyncio.run(backend.process_task(task))

        print('\n' + '=' * 80)
        print('任务执行结果:')
        print(f'成功: {result["success"]}')
        print(f'会话ID: {result["session_id"]}')
        print(f'开始时间: {result["start_time"]}')
        print(f'结束时间: {result["end_time"]}')
        print(f'最终状态: {result["final_state"]}')

        if result['error']:
            print(f'错误: {result["error"]}')

        print(f'总事件数: {event_printer.event_count}')

    except KeyboardInterrupt:
        print('\n任务被用户中断')
    except Exception as e:
        print(f'\n执行错误: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
