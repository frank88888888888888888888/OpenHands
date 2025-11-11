"""
Action 序列化模块

这个模块负责处理 OpenHands 中所有 Action（动作）类型的序列化和反序列化。
Action 代表 Agent 可以执行的各种操作，包括：

1. 命令执行：运行 bash 命令、Python 代码
2. 文件操作：读取、写入、编辑文件
3. 浏览器操作：访问网页、与页面交互
4. Agent 控制：思考、完成任务、委托、状态变更
5. 消息传递：发送消息、系统消息
6. 特殊操作：MCP 调用、任务跟踪、循环恢复等

主要功能：
- 维护所有 Action 类型的注册表
- 处理 Action 的反序列化（从字典创建 Action 对象）
- 处理向后兼容性和废弃参数
- 处理安全风险等级的序列化
"""

from typing import Any

from openhands.core.exceptions import LLMMalformedActionError
from openhands.events.action.action import Action, ActionSecurityRisk
from openhands.events.action.agent import (
    AgentDelegateAction,  # Agent 委托动作
    AgentFinishAction,  # Agent 完成任务动作
    AgentRejectAction,  # Agent 拒绝动作
    AgentThinkAction,  # Agent 思考动作
    ChangeAgentStateAction,  # 改变 Agent 状态动作
    CondensationAction,  # 压缩动作
    CondensationRequestAction,  # 压缩请求动作
    LoopRecoveryAction,  # 循环恢复动作
    RecallAction,  # 回忆动作
    TaskTrackingAction,  # 任务跟踪动作
)
from openhands.events.action.browse import (  # 浏览器动作
    BrowseInteractiveAction,
    BrowseURLAction,
)
from openhands.events.action.commands import (
    CmdRunAction,  # 命令运行动作
    IPythonRunCellAction,  # IPython 代码执行动作
)
from openhands.events.action.empty import NullAction  # 空动作
from openhands.events.action.files import (
    FileEditAction,  # 文件编辑动作
    FileReadAction,  # 文件读取动作
    FileWriteAction,  # 文件写入动作
)
from openhands.events.action.mcp import MCPAction  # MCP（Model Context Protocol）动作
from openhands.events.action.message import (  # 消息动作
    MessageAction,
    SystemMessageAction,
)

# 所有支持的 Action 类型的元组
# 这个元组定义了 OpenHands 系统中所有可用的 Action 类型
actions = (
    NullAction,  # 空操作（无实际动作）
    CmdRunAction,  # 运行命令行命令
    IPythonRunCellAction,  # 运行 IPython 代码单元
    BrowseURLAction,  # 浏览器访问 URL
    BrowseInteractiveAction,  # 浏览器交互操作
    FileReadAction,  # 读取文件
    FileWriteAction,  # 写入文件
    FileEditAction,  # 编辑文件
    AgentThinkAction,  # Agent 思考过程
    AgentFinishAction,  # Agent 完成任务
    AgentRejectAction,  # Agent 拒绝执行
    AgentDelegateAction,  # Agent 委托任务
    RecallAction,  # 回忆/检索信息
    ChangeAgentStateAction,  # 改变 Agent 状态
    MessageAction,  # 发送消息
    SystemMessageAction,  # 系统消息
    CondensationAction,  # 内容压缩
    CondensationRequestAction,  # 请求内容压缩
    MCPAction,  # MCP 协议调用
    TaskTrackingAction,  # 任务跟踪
    LoopRecoveryAction,  # 循环恢复
)

# Action 类型名称到类的映射字典
# 用于根据字符串类型名称快速查找对应的 Action 类
# 例如：'run' -> CmdRunAction, 'edit' -> FileEditAction
ACTION_TYPE_TO_CLASS = {action_class.action: action_class for action_class in actions}  # type: ignore[attr-defined]


def handle_action_deprecated_args(args: dict[str, Any]) -> dict[str, Any]:
    """处理 Action 参数中的废弃字段。

    这个函数负责处理向后兼容性，移除或转换已废弃的参数，确保旧版本的
    序列化数据能够正确反序列化为新版本的 Action 对象。

    参数:
        args (dict[str, Any]): Action 的参数字典

    返回:
        dict[str, Any]: 处理后的参数字典

    处理的废弃字段：
    1. keep_prompt: 已在 PR #4881 中废弃，直接移除
    2. task_completed: 已废弃，移除以保持向后兼容性
    3. translated_ipython_code: 处理旧版本的 IPython 代码转换格式
    4. command='view': 转换为 FileReadAction（不需要 command 参数）
    """
    # keep_prompt 已在 https://github.com/OpenHands/OpenHands/pull/4881 中废弃
    if 'keep_prompt' in args:
        args.pop('keep_prompt')

    # task_completed 已废弃 - 移除以保持向后兼容性
    if 'task_completed' in args:
        args.pop('task_completed')

    # 处理 translated_ipython_code 废弃字段
    if 'translated_ipython_code' in args:
        code = args.pop('translated_ipython_code')

        # 检查是否是 file_editor 调用（使用前缀检查提高效率）
        file_editor_prefix = 'print(file_editor(**'
        if (
            code is not None
            and code.startswith(file_editor_prefix)
            and code.endswith('))')
        ):
            try:
                # 提取并解析字典字符串
                import ast

                # 提取前缀和结束括号之间的字典字符串
                dict_str = code[len(file_editor_prefix) : -2]  # 移除前缀和 '))'
                file_args = ast.literal_eval(dict_str)

                # 用提取的文件编辑器参数更新 args
                args.update(file_args)
            except (ValueError, SyntaxError):
                # 如果解析失败，只是移除 translated_ipython_code
                pass

        # 处理 'view' 命令的特殊情况
        if args.get('command') == 'view':
            args.pop(
                'command'
            )  # "view" 将被转换为 FileReadAction，它不需要 command 参数

    return args


def action_from_dict(action: dict) -> Action:
    """从字典数据创建 Action 对象。

    这是 Action 反序列化的核心函数，负责将字典格式的数据转换为具体的
    Action 对象。函数会进行严格的验证，处理向后兼容性，并正确设置
    各种属性。

    参数:
        action (dict): 包含 Action 数据的字典，必须包含 'action' 键

    返回:
        Action: 创建的 Action 对象

    异常:
        LLMMalformedActionError: 当输入数据格式错误或无法创建 Action 时抛出

    处理的特殊字段：
    - action: Action 类型名称（必需）
    - args: Action 参数字典
    - timeout: 超时设置
    - timestamp: 时间戳
    - security_risk: 安全风险等级
    - 各种向后兼容性字段
    """
    # 验证输入必须是字典
    if not isinstance(action, dict):
        raise LLMMalformedActionError('action must be a dictionary')

    # 创建副本以避免修改原始数据
    action = action.copy()

    # 验证必需的 'action' 键
    if 'action' not in action:
        raise LLMMalformedActionError(f"'action' key is not found in {action=}")

    # 验证 action 类型必须是字符串
    if not isinstance(action['action'], str):
        raise LLMMalformedActionError(
            f"'{action['action']=}' is not defined. Available actions: {ACTION_TYPE_TO_CLASS.keys()}"
        )

    # 查找对应的 Action 类
    action_class = ACTION_TYPE_TO_CLASS.get(action['action'])
    if action_class is None:
        raise LLMMalformedActionError(
            f"'{action['action']=}' is not defined. Available actions: {ACTION_TYPE_TO_CLASS.keys()}"
        )

    # 获取 Action 参数
    args = action.get('args', {})

    # 从参数中移除时间戳（如果存在）
    # 时间戳会单独处理，不作为构造参数
    timestamp = args.pop('timestamp', None)

    # 向后兼容性处理：旧版本事件流的兼容性
    # is_confirmed 已重命名为 confirmation_state
    is_confirmed = args.pop('is_confirmed', None)
    if is_confirmed is not None:
        args['confirmation_state'] = is_confirmed

    # images_urls 已重命名为 image_urls
    if 'images_urls' in args:
        args['image_urls'] = args.pop('images_urls')

    # 处理安全风险等级的反序列化
    if 'security_risk' in args and args['security_risk'] is not None:
        try:
            # 将数值（int）转换回枚举
            args['security_risk'] = ActionSecurityRisk(args['security_risk'])
        except (ValueError, TypeError):
            # 如果转换失败，移除无效值
            args.pop('security_risk')

    # 处理废弃的参数
    args = handle_action_deprecated_args(args)

    try:
        # 创建 Action 对象
        decoded_action = action_class(**args)

        # 如果有超时设置，应用硬超时
        if 'timeout' in action:
            blocking = args.get('blocking', False)
            decoded_action.set_hard_timeout(action['timeout'], blocking=blocking)

        # 如果提供了时间戳，设置私有时间戳属性
        if timestamp:
            decoded_action._timestamp = timestamp

    except TypeError as e:
        # 如果参数错误，抛出格式错误异常
        raise LLMMalformedActionError(
            f'action={action} has the wrong arguments: {str(e)}'
        )

    # 确保返回的是 Action 实例
    assert isinstance(decoded_action, Action)
    return decoded_action
