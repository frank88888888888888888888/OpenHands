# OpenHands 简化后端

这是一个基于 OpenHands 项目的简化后端版本，专门设计用于与 DeepSeek API 集成，提供 AI Agent 功能和事件流输出。

## 特性

- 🤖 **AI Agent**: 基于 OpenHands 的 CodeActAgent，能够执行代码、编辑文件、浏览网页等
- 🔄 **事件流**: 实时输出 AI Agent 的操作过程和思考步骤
- 🚀 **DeepSeek 集成**: 原生支持 DeepSeek API，包括 deepseek-chat、deepseek-coder 等模型
- 💻 **命令行界面**: 简单易用的命令行接口
- 🛠️ **本地运行时**: 在本地环境中执行任务，无需额外的容器或远程服务

## 安装和设置

### 1. 环境要求

- Python 3.8+
- OpenHands 项目代码（已包含在此目录中）

### 2. 设置 DeepSeek API 密钥

```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key-here"
```

### 3. 安装依赖

```bash
cd /workspace/project/OpenHands
pip install -e .
```

## 使用方法

### 基本用法

```bash
python openhands_backend.py "任务描述"
```

### 示例

```bash
# 创建一个简单的计算器程序
python openhands_backend.py "创建一个Python计算器程序，支持基本的四则运算"

# 分析和修复代码
python openhands_backend.py "分析当前目录下的Python文件，找出潜在的bug并修复"

# 创建网页应用
python openhands_backend.py "创建一个简单的HTML网页，包含一个待办事项列表功能"

# 数据处理任务
python openhands_backend.py "读取CSV文件data.csv，分析数据并生成可视化图表"
```

## 事件流输出

程序运行时会实时显示 AI Agent 的操作过程：

```
[14:30:15] 事件 #1: MessageAction
内容: 创建一个Python计算器程序，支持基本的四则运算
--------------------------------------------------------------------------------

[14:30:16] 事件 #2: CmdRunAction
命令: python -c "print('Hello, World!')"
--------------------------------------------------------------------------------

[14:30:17] 事件 #3: CmdRunObservation
内容: Hello, World!
--------------------------------------------------------------------------------

[14:30:18] 事件 #4: FileWriteAction
路径: calculator.py
内容: def add(a, b): return a + b...
--------------------------------------------------------------------------------
```

## 配置选项

### 模型选择

支持多种 DeepSeek 模型：

- `deepseek-chat`: 通用对话和代码生成
- `deepseek-coder`: 专门用于代码生成
- `deepseek-reasoner`: 适合复杂推理任务

修改 `openhands_backend.py` 中的模型参数：

```python
backend = OpenHandsBackend(deepseek_api_key, model="deepseek-coder")
```

### 自定义配置

编辑 `config.py` 文件来调整：

- API 配置
- 模型参数
- 事件流设置
- 工作空间配置

## 高级用法

### 编程接口

```python
from openhands_backend import OpenHandsBackend, EventStreamPrinter

# 创建后端实例
backend = OpenHandsBackend("your-api-key", model="deepseek-chat")

# 添加自定义事件处理器
def my_event_handler(event):
    print(f"收到事件: {event.__class__.__name__}")

backend.add_event_callback(my_event_handler)

# 执行任务
result = await backend.process_task("创建一个简单的网站")
```

### 批量任务处理

```python
import asyncio
from openhands_backend import OpenHandsBackend

async def process_multiple_tasks():
    backend = OpenHandsBackend("your-api-key")

    tasks = [
        "创建一个Python脚本来处理CSV文件",
        "编写单元测试",
        "生成项目文档"
    ]

    for task in tasks:
        print(f"处理任务: {task}")
        result = await backend.process_task(task)
        print(f"结果: {result['success']}")
```

## 故障排除

### 常见问题

1. **API 密钥错误**
   ```
   错误: 请设置环境变量 DEEPSEEK_API_KEY
   ```
   解决方案: 确保正确设置了环境变量

2. **依赖缺失**
   ```
   ModuleNotFoundError: No module named 'openhands'
   ```
   解决方案: 确保已安装 OpenHands 依赖

3. **权限错误**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   解决方案: 检查工作目录的读写权限

### 调试模式

启用详细日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 项目结构

```
/workspace/project/
├── openhands_backend.py    # 主入口文件
├── config.py              # 配置文件
├── README.md              # 说明文档
└── OpenHands/             # OpenHands 项目代码
    ├── openhands/         # 核心模块
    ├── tests/             # 测试文件
    └── ...
```

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 许可证

本项目基于 OpenHands 项目，遵循相同的开源许可证。

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
