#!/usr/bin/env python3
"""
OpenHands 简化后端启动脚本
自动检测环境并选择合适的运行模式
"""

import os
import subprocess
import sys


def check_dependencies():
    """检查必要的依赖"""
    try:
        import httpx  # noqa: F401
        import pydantic  # noqa: F401

        return True
    except ImportError:
        return False


def install_dependencies():
    """安装必要的依赖"""
    print('🔧 正在安装必要的依赖...')
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', 'httpx', 'pydantic']
        )
        print('✅ 依赖安装成功！')
        return True
    except subprocess.CalledProcessError:
        print('❌ 依赖安装失败')
        return False


def main():
    """主函数"""
    print('🚀 OpenHands 简化后端启动器')
    print('=' * 50)

    # 检查参数
    if len(sys.argv) < 2:
        print('📋 用法:')
        print("  python start.py '任务描述'")
        print("  python start.py '任务描述' [模型名称]")
        print()
        print('🎯 示例任务:')
        print("  python start.py '创建一个Python计算器程序'")
        print("  python start.py '制作一个简单的网站'")
        print("  python start.py '分析数据并生成报告'")
        print("  python start.py '编写一个文件管理工具'")
        print()
        print('🎭 演示模式（无需API密钥）:')
        print("  python start.py demo '任务描述'")
        sys.exit(1)

    # 检查是否是演示模式
    if sys.argv[1].lower() == 'demo':
        if len(sys.argv) < 3:
            print('❌ 演示模式需要任务描述')
            print("例如: python start.py demo '创建一个计算器'")
            sys.exit(1)

        task = sys.argv[2]
        model = sys.argv[3] if len(sys.argv) > 3 else 'deepseek-chat'

        print('🎭 启动演示模式...')
        print(f'📋 任务: {task}')
        print(f'🤖 模型: {model}')
        print()

        # 检查依赖
        if not check_dependencies():
            if not install_dependencies():
                sys.exit(1)

        # 运行演示版本
        try:
            subprocess.run([sys.executable, 'demo_backend.py', task, model])
        except KeyboardInterrupt:
            print('\n⚠️ 演示被用户中断')
        except FileNotFoundError:
            print('❌ 找不到 demo_backend.py 文件')
            sys.exit(1)

        return

    # 正常模式
    task = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else 'deepseek-chat'

    # 检查API密钥
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print('⚠️ 未检测到 DEEPSEEK_API_KEY 环境变量')
        print()
        print('🔑 请选择运行模式:')
        print('1. 设置API密钥并使用真实模式')
        print('2. 使用演示模式（无需API密钥）')
        print()

        choice = input('请选择 (1/2): ').strip()

        if choice == '1':
            print()
            print('📝 请按以下步骤设置API密钥:')
            print('1. 访问 https://platform.deepseek.com/')
            print('2. 注册账号并获取API密钥')
            print("3. 运行: export DEEPSEEK_API_KEY='your-api-key-here'")
            print('4. 重新运行此脚本')
            sys.exit(1)
        elif choice == '2':
            print('🎭 切换到演示模式...')

            # 检查依赖
            if not check_dependencies():
                if not install_dependencies():
                    sys.exit(1)

            # 运行演示版本
            try:
                subprocess.run([sys.executable, 'demo_backend.py', task, model])
            except KeyboardInterrupt:
                print('\n⚠️ 演示被用户中断')
            except FileNotFoundError:
                print('❌ 找不到 demo_backend.py 文件')
                sys.exit(1)
            return
        else:
            print('❌ 无效选择')
            sys.exit(1)

    # 有API密钥，使用真实模式
    print('🔑 检测到 DEEPSEEK_API_KEY，使用真实模式')
    print(f'📋 任务: {task}')
    print(f'🤖 模型: {model}')
    print()

    # 检查依赖
    if not check_dependencies():
        if not install_dependencies():
            sys.exit(1)

    # 检查是否有完整的OpenHands环境
    try:
        import openhands  # noqa: F401

        print('✅ 检测到完整的OpenHands环境，使用完整版后端')
        backend_script = 'openhands_backend.py'
    except ImportError:
        print('📦 使用简化版后端（推荐）')
        backend_script = 'simple_backend.py'

    # 运行对应的后端
    try:
        subprocess.run([sys.executable, backend_script, task, model])
    except KeyboardInterrupt:
        print('\n⚠️ 任务被用户中断')
    except FileNotFoundError:
        print(f'❌ 找不到 {backend_script} 文件')
        sys.exit(1)


if __name__ == '__main__':
    main()
