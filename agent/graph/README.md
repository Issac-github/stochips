# LangGraph 使用案例

本目录包含 LangGraph 的使用示例,展示如何构建基于 LLM 的工作流应用。

## 📁 文件说明

### 1. chat_workflow.py - 基础聊天工作流
展示 LangGraph 的核心概念:
- **StateGraph**: 状态图管理
- **Node**: 节点定义和实现
- **Edge**: 普通边连接
- **Conditional Edge**: 条件边路由
- **状态管理**: TypedDict 定义状态

**功能**:
- 意图识别和分类
- 多路径路由(帮助、天气、对话、退出)
- 对话状态保持
- 交互式命令行界面

**运行方式**:
```bash
cd /Users/linzeyu/Desktop/stochips/agent
python -m graph.chat_workflow
```

### 2. advanced_workflow.py - 高级工作流
展示 LangGraph 的高级特性:
- **工具集成**: 使用 @tool 装饰器定义工具
- **并行执行**: 多个工具同时调用
- **循环迭代**: 条件循环直到满足退出条件
- **复杂状态**: 多字段状态管理
- **ToolNode**: 预构建的工具节点

**功能**:
- 自动工具选择和调用
- 搜索结果和计算结果并行处理
- 迭代优化查询
- 结果汇总和回复生成

**运行方式**:
```bash
cd /Users/linzeyu/Desktop/stochips/agent
python -m graph.advanced_workflow
```

## 🏗️ 核心概念

### 状态 (State)
所有节点共享的状态对象,使用 TypedDict 定义:
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "消息历史"]
    next_step: Annotated[str, "下一步操作"]
    # ... 其他字段
```

### 节点 (Node)
处理状态的函数:
```python
def my_node(state: AgentState) -> AgentState:
    # 处理逻辑
    state["field"] = new_value
    return state
```

### 边 (Edge)
连接节点,控制流程:
```python
# 普通边
workflow.add_edge("node_a", "node_b")

# 条件边
workflow.add_conditional_edges(
    "node_a",
    decision_function,
    {"option1": "node_b", "option2": "node_c"}
)
```

### 编译和执行
```python
# 编译图
app = workflow.compile()

# 执行
result = app.invoke(initial_state)
```

## 🔧 环境要求

确保已安装依赖:
```bash
cd /Users/linzeyu/Desktop/stochips/agent
poetry install
```

依赖包括:
- `langgraph>=1.1.6` - 图工作流框架
- `langchain>=1.2.15` - LangChain 核心
- `langchain-openai>=1.1.12` - OpenAI 集成
- `python-dotenv` - 环境变量管理

## 📝 环境变量

在项目根目录创建 `.env` 文件:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## 🎯 扩展建议

### 添加新节点
1. 定义节点函数 `def my_node(state: AgentState) -> AgentState`
2. 使用 `workflow.add_node("node_name", my_node)` 添加
3. 使用 `workflow.add_edge()` 或 `workflow.add_conditional_edges()` 连接

### 添加工具
1. 使用 `@tool` 装饰器定义函数
2. 将工具添加到工具列表
3. 使用 `llm.bind_tools(tools)` 绑定到 LLM

### 持久化
可以集成检查点(checkpointing)来保存对话状态:
```python
from langgraph.checkpoint import MemorySaver

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

## 📚 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph 概念指南](https://langchain-ai.github.io/langgraph/concepts/)
- [LangGraph 示例库](https://github.com/langchain-ai/langgraph/tree/main/examples)

## 💡 使用场景

1. **多步骤对话**: 需要上下文管理的复杂对话
2. **工具调用**: 需要调用外部 API 或函数
3. **工作流**: 有明确步骤的业务流程
4. **决策系统**: 需要条件判断和路由
5. **循环处理**: 需要迭代直到满足条件

## ⚠️ 注意事项

1. 确保 API 密钥配置正确
2. 注意迭代次数限制,避免无限循环
3. 状态对象是可变的,注意数据一致性
4. 工具调用需要正确处理参数和结果
