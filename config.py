"""
OpenHands 后端配置文件
"""

import os
from typing import Any

# DeepSeek API 配置
DEEPSEEK_CONFIG = {
    'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
    'base_url': 'https://api.deepseek.com',
    'models': {
        'deepseek-chat': {
            'name': 'deepseek-chat',
            'description': 'DeepSeek Chat 模型，适合对话和代码生成',
            'max_tokens': 4096,
            'temperature': 0.1,
        },
        'deepseek-coder': {
            'name': 'deepseek-coder',
            'description': 'DeepSeek Coder 模型，专门用于代码生成',
            'max_tokens': 4096,
            'temperature': 0.1,
        },
        'deepseek-reasoner': {
            'name': 'deepseek-reasoner',
            'description': 'DeepSeek Reasoner 模型，适合复杂推理任务',
            'max_tokens': 8192,
            'temperature': 0.0,
        },
    },
}

# OpenHands 配置
OPENHANDS_CONFIG = {
    'default_agent': 'CodeActAgent',
    'runtime': 'local',
    'max_iterations': 50,
    'max_budget_per_task': 10.0,
    'workspace_dir': '/tmp/openhands_workspace',
    'log_level': 'INFO',
}

# 事件流配置
EVENT_STREAM_CONFIG = {
    'show_details': True,
    'save_to_file': False,
    'output_file': 'openhands_events.json',
    'filter_events': [],  # 可以过滤特定类型的事件
}


def get_model_config(model_name: str) -> dict[str, Any]:
    """获取指定模型的配置"""
    return DEEPSEEK_CONFIG['models'].get(
        model_name, DEEPSEEK_CONFIG['models']['deepseek-chat']
    )


def validate_config() -> bool:
    """验证配置是否有效"""
    if not DEEPSEEK_CONFIG['api_key']:
        print('错误: 未设置 DEEPSEEK_API_KEY 环境变量')
        return False

    return True
