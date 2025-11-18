#!/usr/bin/env python3
"""
OpenHands 后端测试脚本
"""

import asyncio
import os
import sys

# 添加路径
sys.path.insert(0, '/workspace/project/OpenHands')
sys.path.insert(0, '/workspace/project')


def test_imports():
    """测试所有必要的导入"""
    print('测试导入...')

    try:
        # 测试 OpenHands 核心导入
        import openhands.agenthub  # noqa: F401
        from openhands.core.config import LLMConfig, OpenHandsConfig  # noqa: F401
        from openhands.core.logger import openhands_logger  # noqa: F401
        from openhands.events.action import MessageAction  # noqa: F401

        print('✓ OpenHands 核心模块导入成功')

        # 测试后端导入
        from openhands_backend import EventStreamPrinter, OpenHandsBackend  # noqa: F401

        print('✓ 后端模块导入成功')

        # 测试配置导入
        from config import DEEPSEEK_CONFIG, validate_config  # noqa: F401

        print('✓ 配置模块导入成功')

        return True

    except ImportError as e:
        print(f'✗ 导入失败: {e}')
        return False


def test_config_creation():
    """测试配置创建"""
    print('\n测试配置创建...')

    try:
        from openhands_backend import OpenHandsBackend

        # 使用模拟的API密钥
        mock_api_key = 'sk-test-key-12345'
        backend = OpenHandsBackend(mock_api_key, model='deepseek-chat')

        # 检查配置
        assert backend.deepseek_api_key == mock_api_key
        assert backend.model == 'deepseek-chat'
        assert backend.config is not None

        print('✓ 配置创建成功')
        print(f'  - API密钥: {backend.deepseek_api_key[:10]}...')
        print(f'  - 模型: {backend.model}')
        print(f'  - 默认代理: {backend.config.default_agent}')

        return True

    except Exception as e:
        print(f'✗ 配置创建失败: {e}')
        return False


def test_event_stream_printer():
    """测试事件流打印器"""
    print('\n测试事件流打印器...')

    try:
        from openhands.events.action import MessageAction
        from openhands_backend import EventStreamPrinter

        # 创建打印器
        printer = EventStreamPrinter(show_details=False)

        # 创建模拟事件
        mock_event = MessageAction(content='测试消息')

        # 测试事件处理（捕获输出）
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            printer(mock_event)

        output = f.getvalue()
        assert 'MessageAction' in output
        assert '测试消息' in output

        print('✓ 事件流打印器工作正常')
        print(f'  - 事件计数: {printer.event_count}')

        return True

    except Exception as e:
        print(f'✗ 事件流打印器测试失败: {e}')
        return False


def test_llm_config():
    """测试LLM配置"""
    print('\n测试LLM配置...')

    try:
        from openhands.core.config import LLMConfig

        # 创建DeepSeek配置
        llm_config = LLMConfig(
            model='deepseek-chat',
            api_key='sk-test-key',
            base_url='https://api.deepseek.com',
            temperature=0.1,
            max_output_tokens=4096,
        )

        assert llm_config.model == 'deepseek-chat'
        assert llm_config.base_url == 'https://api.deepseek.com'
        assert llm_config.temperature == 0.1

        print('✓ LLM配置创建成功')
        print(f'  - 模型: {llm_config.model}')
        print(f'  - 基础URL: {llm_config.base_url}')
        print(f'  - 温度: {llm_config.temperature}')

        return True

    except Exception as e:
        print(f'✗ LLM配置测试失败: {e}')
        return False


async def test_backend_initialization():
    """测试后端初始化（异步）"""
    print('\n测试后端初始化...')

    try:
        from openhands_backend import OpenHandsBackend

        # 使用模拟API密钥
        mock_api_key = 'sk-test-key-12345'
        backend = OpenHandsBackend(mock_api_key)

        # 测试事件回调添加
        callback_called = False

        def test_callback(event):
            nonlocal callback_called
            callback_called = True

        backend.add_event_callback(test_callback)

        # 模拟事件
        from openhands.events.action import MessageAction

        mock_event = MessageAction(content='测试')

        # 调用回调
        for callback in backend.event_callbacks:
            callback(mock_event)

        assert callback_called, '事件回调未被调用'

        print('✓ 后端初始化成功')
        print(f'  - 事件回调数量: {len(backend.event_callbacks)}')

        return True

    except Exception as e:
        print(f'✗ 后端初始化测试失败: {e}')
        return False


def test_environment():
    """测试环境设置"""
    print('\n测试环境设置...')

    # 检查Python版本
    python_version = sys.version_info
    print(
        f'Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}'
    )

    if python_version < (3, 8):
        print('✗ Python版本过低，需要3.8+')
        return False

    # 检查关键路径
    openhands_path = '/workspace/project/OpenHands'
    if not os.path.exists(openhands_path):
        print(f'✗ OpenHands路径不存在: {openhands_path}')
        return False

    print(f'✓ OpenHands路径存在: {openhands_path}')

    # 检查环境变量（可选）
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    if deepseek_key:
        print(f'✓ DEEPSEEK_API_KEY已设置: {deepseek_key[:10]}...')
    else:
        print('⚠ DEEPSEEK_API_KEY未设置（测试时使用模拟密钥）')

    return True


async def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('OpenHands 后端集成测试')
    print('=' * 60)

    tests = [
        ('环境检查', test_environment),
        ('导入测试', test_imports),
        ('配置创建', test_config_creation),
        ('LLM配置', test_llm_config),
        ('事件流打印器', test_event_stream_printer),
        ('后端初始化', test_backend_initialization),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f'\n{"=" * 20} {test_name} {"=" * 20}')

        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            if result:
                passed += 1
                print(f'✓ {test_name} 通过')
            else:
                print(f'✗ {test_name} 失败')

        except Exception as e:
            print(f'✗ {test_name} 异常: {e}')

    print('\n' + '=' * 60)
    print(f'测试结果: {passed}/{total} 通过')

    if passed == total:
        print('🎉 所有测试通过！系统准备就绪。')
        return True
    else:
        print('❌ 部分测试失败，请检查配置。')
        return False


def main():
    """主函数"""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print('\n测试被用户中断')
        sys.exit(1)
    except Exception as e:
        print(f'\n测试执行错误: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
