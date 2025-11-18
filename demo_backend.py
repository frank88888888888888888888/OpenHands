#!/usr/bin/env python3
"""
OpenHands 简化后端 - 演示版本
不需要真实的API密钥，使用模拟响应来演示事件流功能
"""

import asyncio
import json
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class EventType(Enum):
    """事件类型"""

    USER_MESSAGE = 'user_message'
    AGENT_MESSAGE = 'agent_message'
    AGENT_ACTION = 'agent_action'
    AGENT_OBSERVATION = 'agent_observation'
    AGENT_THINKING = 'agent_thinking'
    SYSTEM_MESSAGE = 'system_message'
    FILE_OPERATION = 'file_operation'
    CODE_EXECUTION = 'code_execution'
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


class MockAgent:
    """模拟AI Agent，生成演示响应"""

    def __init__(self):
        self.step_count = 0

    async def process_task(self, task: str) -> list[dict[str, Any]]:
        """处理任务并返回步骤列表"""
        self.step_count = 0

        # 根据任务类型生成不同的步骤
        if '计算器' in task or 'calculator' in task.lower():
            return await self._create_calculator_steps()
        elif '网站' in task or '网页' in task or 'web' in task.lower():
            return await self._create_website_steps()
        elif '数据分析' in task or '分析' in task:
            return await self._create_data_analysis_steps()
        else:
            return await self._create_generic_steps(task)

    async def _create_calculator_steps(self) -> list[dict[str, Any]]:
        """创建计算器项目的步骤"""
        return [
            {
                'type': 'agent_thinking',
                'content': '我需要创建一个Python计算器程序。让我分析需求：\n1. 支持基本四则运算\n2. 用户友好的界面\n3. 错误处理\n4. 可扩展的设计',
                'delay': 1.0,
            },
            {
                'type': 'agent_action',
                'content': '创建计算器主文件 calculator.py',
                'delay': 0.5,
            },
            {
                'type': 'file_operation',
                'content': '正在写入文件: calculator.py',
                'metadata': {
                    'file_path': 'calculator.py',
                    'operation': 'create',
                    'size': '1.2KB',
                },
                'delay': 1.0,
            },
            {
                'type': 'agent_observation',
                'content': '文件 calculator.py 创建成功，包含以下功能：\n- 基本四则运算函数\n- 用户输入处理\n- 错误异常处理\n- 主循环逻辑',
                'delay': 0.5,
            },
            {'type': 'agent_action', 'content': '测试计算器程序', 'delay': 0.5},
            {
                'type': 'code_execution',
                'content': 'python calculator.py',
                'metadata': {
                    'command': 'python calculator.py',
                    'exit_code': 0,
                    'output': "计算器程序启动成功\n支持的操作: +, -, *, /\n输入 'quit' 退出程序",
                },
                'delay': 1.5,
            },
            {
                'type': 'agent_observation',
                'content': '计算器程序测试通过！功能正常：\n✅ 加法运算正确\n✅ 减法运算正确\n✅ 乘法运算正确\n✅ 除法运算正确\n✅ 错误处理正常',
                'delay': 1.0,
            },
            {
                'type': 'agent_message',
                'content': '🎉 Python计算器程序创建完成！\n\n**功能特性：**\n- ✅ 支持基本四则运算 (+, -, *, /)\n- ✅ 友好的用户界面\n- ✅ 完善的错误处理\n- ✅ 输入验证和异常捕获\n- ✅ 循环交互模式\n\n**使用方法：**\n```bash\npython calculator.py\n```\n\n**代码结构：**\n- `add()`, `subtract()`, `multiply()`, `divide()` - 基本运算函数\n- `get_user_input()` - 用户输入处理\n- `main()` - 主程序循环\n\n程序已经过测试，可以正常使用！',
                'delay': 1.0,
            },
        ]

    async def _create_website_steps(self) -> list[dict[str, Any]]:
        """创建网站项目的步骤"""
        return [
            {
                'type': 'agent_thinking',
                'content': '用户想要创建一个网站。我需要：\n1. 确定网站类型和需求\n2. 选择合适的技术栈\n3. 创建基本的HTML结构\n4. 添加CSS样式\n5. 实现JavaScript交互',
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '创建项目目录结构', 'delay': 0.5},
            {
                'type': 'file_operation',
                'content': '创建目录: website/\n创建文件: index.html, style.css, script.js',
                'metadata': {
                    'files_created': ['index.html', 'style.css', 'script.js'],
                    'directory': 'website',
                },
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '编写HTML主页面', 'delay': 0.5},
            {
                'type': 'file_operation',
                'content': '正在写入 index.html - 包含响应式布局和现代设计',
                'metadata': {'file_path': 'website/index.html', 'size': '2.1KB'},
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '添加CSS样式', 'delay': 0.5},
            {
                'type': 'file_operation',
                'content': '正在写入 style.css - 现代化样式和动画效果',
                'metadata': {'file_path': 'website/style.css', 'size': '1.8KB'},
                'delay': 1.0,
            },
            {
                'type': 'agent_message',
                'content': '🌐 网站创建完成！\n\n**项目结构：**\n```\nwebsite/\n├── index.html    # 主页面\n├── style.css     # 样式文件\n└── script.js     # 交互脚本\n```\n\n**特性：**\n- ✅ 响应式设计\n- ✅ 现代化UI\n- ✅ 交互动画\n- ✅ 跨浏览器兼容\n\n**启动方法：**\n在浏览器中打开 `website/index.html` 即可查看效果！',
                'delay': 1.0,
            },
        ]

    async def _create_data_analysis_steps(self) -> list[dict[str, Any]]:
        """创建数据分析项目的步骤"""
        return [
            {
                'type': 'agent_thinking',
                'content': '数据分析任务需要：\n1. 数据加载和清洗\n2. 探索性数据分析\n3. 数据可视化\n4. 统计分析\n5. 结果报告',
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '检查数据文件', 'delay': 0.5},
            {
                'type': 'code_execution',
                'content': 'ls -la *.csv *.xlsx *.json',
                'metadata': {
                    'command': 'ls -la *.csv *.xlsx *.json',
                    'output': 'data.csv  (1.2MB)\nsales.xlsx (856KB)\nconfig.json (2KB)',
                },
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '加载和预处理数据', 'delay': 0.5},
            {
                'type': 'code_execution',
                'content': 'python -c "import pandas as pd; df = pd.read_csv(\'data.csv\'); print(df.info())"',
                'metadata': {
                    'output': '数据集信息：\n- 行数: 10,000\n- 列数: 15\n- 缺失值: 3.2%\n- 数据类型: 混合'
                },
                'delay': 1.5,
            },
            {'type': 'agent_action', 'content': '生成数据可视化图表', 'delay': 0.5},
            {
                'type': 'file_operation',
                'content': '创建可视化图表: charts/distribution.png, charts/correlation.png',
                'metadata': {
                    'charts_created': [
                        'distribution.png',
                        'correlation.png',
                        'trends.png',
                    ]
                },
                'delay': 2.0,
            },
            {
                'type': 'agent_message',
                'content': '📊 数据分析完成！\n\n**分析结果：**\n- 📈 数据趋势：整体呈上升趋势\n- 🔍 关键发现：3个主要模式\n- 📉 异常值：检测到12个离群点\n- 🎯 相关性：发现5组强相关变量\n\n**生成文件：**\n- `analysis_report.html` - 详细分析报告\n- `charts/` - 可视化图表目录\n- `cleaned_data.csv` - 清洗后的数据\n\n**建议：**\n基于分析结果，建议关注前3个关键指标的变化趋势。',
                'delay': 1.0,
            },
        ]

    async def _create_generic_steps(self, task: str) -> list[dict[str, Any]]:
        """创建通用任务的步骤"""
        return [
            {
                'type': 'agent_thinking',
                'content': f'分析任务: {task}\n\n我需要：\n1. 理解具体需求\n2. 制定执行计划\n3. 逐步实现功能\n4. 测试和验证结果',
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '开始执行任务计划', 'delay': 0.5},
            {
                'type': 'agent_observation',
                'content': '正在分析任务的具体要求和约束条件...',
                'delay': 1.0,
            },
            {'type': 'agent_action', 'content': '实施解决方案', 'delay': 0.5},
            {
                'type': 'agent_observation',
                'content': '解决方案实施中，进度：60%',
                'delay': 1.5,
            },
            {'type': 'agent_action', 'content': '验证结果', 'delay': 0.5},
            {
                'type': 'agent_observation',
                'content': '✅ 任务执行完成，结果验证通过',
                'delay': 1.0,
            },
            {
                'type': 'agent_message',
                'content': f'✨ 任务完成！\n\n**任务：** {task}\n\n**执行结果：**\n- ✅ 需求分析完成\n- ✅ 解决方案实施\n- ✅ 结果验证通过\n\n**总结：**\n任务已按要求完成，所有功能正常运行。',
                'delay': 1.0,
            },
        ]


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
            EventType.FILE_OPERATION: '📁',
            EventType.CODE_EXECUTION: '💻',
            EventType.ERROR: '❌',
        }

        icon = icons.get(event.type, '📝')

        print(f'\n{icon} [{timestamp}] {event.type.value.upper()}')
        print(f'内容: {event.content}')

        if self.show_details and event.metadata:
            print(f'元数据: {json.dumps(event.metadata, ensure_ascii=False, indent=2)}')

        print('-' * 80)


class DemoOpenHandsBackend:
    """演示版OpenHands后端"""

    def __init__(self, model: str = 'deepseek-chat'):
        self.model = model
        self.agent = MockAgent()
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
                '🚀 OpenHands AI Agent 启动',
                {'model': self.model, 'mode': 'demo'},
            )

            # 发出用户消息事件
            self.event_stream.emit_event(EventType.USER_MESSAGE, task)

            # 获取任务步骤
            steps = await self.agent.process_task(task)

            # 执行每个步骤
            for step in steps:
                # 检查是否被中断
                if self.shutdown_event.is_set():
                    result['error'] = '任务被用户中断'
                    return result

                # 等待指定的延迟时间
                if 'delay' in step:
                    await asyncio.sleep(step['delay'])

                # 发出对应的事件
                event_type = EventType(step['type'])
                self.event_stream.emit_event(
                    event_type, step['content'], step.get('metadata', {})
                )

            # 发出完成事件
            self.event_stream.emit_event(
                EventType.SYSTEM_MESSAGE, '🎉 任务执行完成！所有步骤已成功完成。'
            )

            result['success'] = True
            result['response'] = '任务已成功完成，请查看上方的详细执行过程。'

        except Exception as e:
            error_msg = f'任务处理失败: {str(e)}'
            self.event_stream.emit_event(EventType.ERROR, error_msg)
            result['error'] = error_msg

        finally:
            result['end_time'] = datetime.now().isoformat()
            result['event_count'] = len(self.event_stream.events)

        return result


async def main():
    """主函数"""
    print('🎭 OpenHands 演示后端启动中...')
    print('📝 注意：这是演示版本，使用模拟的AI响应')

    # 获取任务
    if len(sys.argv) < 2:
        print("\n📋 用法: python demo_backend.py '任务描述'")
        print('\n🎯 示例任务:')
        print("  • python demo_backend.py '创建一个Python计算器程序'")
        print("  • python demo_backend.py '制作一个简单的网站'")
        print("  • python demo_backend.py '分析数据并生成报告'")
        print("  • python demo_backend.py '编写一个文件管理工具'")
        sys.exit(1)

    task = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else 'deepseek-chat'

    # 创建后端实例
    backend = DemoOpenHandsBackend(model)

    # 添加事件打印器
    event_printer = EventPrinter(show_details=True)
    backend.add_event_callback(event_printer)

    print(f'\n📋 任务: {task}')
    print(f'🤖 模型: {model} (演示模式)')
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
            print(f'\n💬 系统响应: {result["response"]}')

        print('\n🎉 演示完成！这展示了OpenHands AI Agent的工作流程。')
        print('💡 在实际使用中，Agent会真正执行这些操作并产生实际结果。')

    except KeyboardInterrupt:
        print('\n⚠️ 演示被用户中断')
    except Exception as e:
        print(f'\n❌ 执行错误: {e}')
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
