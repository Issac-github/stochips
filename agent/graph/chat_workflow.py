"""
LangGraph 聊天工作流示例

展示了 LangGraph 的核心概念:
- StateGraph 状态管理
- Node 节点定义
- Edge 边连接
- Conditional Edge 条件边
- 编译和执行
"""

import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置 Moonshot API
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
if not MOONSHOT_API_KEY:
    raise ValueError(
        "MOONSHOT_API_KEY environment variable is not set. "
        "Please set it in your .env file or environment."
    )

# 设置 Moonshot API 凭证
os.environ["OPENAI_API_KEY"] = MOONSHOT_API_KEY
os.environ["OPENAI_API_BASE"] = "https://api.moonshot.cn/v1"


# 定义状态类型
class AgentState(TypedDict):
    """图的状态"""
    messages: Annotated[Sequence[BaseMessage], "对话消息历史"]
    next_step: Annotated[str, "下一步操作"]
    context: Annotated[str, "上下文信息"]


# 初始化 LLM (使用 Moonshot/Kimi)
llm = ChatOpenAI(
    model="moonshot-v1-8k",
    temperature=0.7,
)


def classify_intent(state: AgentState) -> AgentState:
    """
    节点1: 识别用户意图
    """
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    # 简单意图分类逻辑
    if any(word in last_message.lower() for word in ["帮助", "help", "怎么", "how"]):
        state["next_step"] = "provide_help"
    elif any(word in last_message.lower() for word in ["天气", "weather", "温度", "temperature"]):
        state["next_step"] = "get_weather"
    elif any(word in last_message.lower() for word in ["退出", "exit", "再见", "bye"]):
        state["next_step"] = "goodbye"
    else:
        state["next_step"] = "general_chat"

    state["context"] = f"识别到的意图: {state['next_step']}"
    return state


def provide_help(state: AgentState) -> AgentState:
    """
    节点2: 提供帮助信息
    """
    help_message = """我可以帮你:
1. 回答一般问题
2. 提供天气信息(模拟)
3. 进行简单对话

输入 "退出" 结束对话。"""

    state["messages"] = list(state["messages"]) + [AIMessage(content=help_message)]
    return state


def get_weather(state: AgentState) -> AgentState:
    """
    节点3: 获取天气信息(模拟)
    """
    weather_info = "🌤️ 今天天气晴朗，温度 25°C，适合外出！"
    state["messages"] = list(state["messages"]) + [AIMessage(content=weather_info)]
    return state


def general_chat(state: AgentState) -> AgentState:
    """
    节点4: 一般对话
    """
    messages = state["messages"]

    # 调用 LLM 生成回复
    response = llm.invoke(messages)
    state["messages"] = list(messages) + [response]
    return state


def goodbye(state: AgentState) -> AgentState:
    """
    节点5: 结束对话
    """
    farewell = "👋 感谢使用，再见！"
    state["messages"] = list(state["messages"]) + [AIMessage(content=farewell)]
    return state


def should_continue(state: AgentState) -> str:
    """
    条件边: 根据意图决定下一步
    """
    next_step = state.get("next_step", "general_chat")

    if next_step == "provide_help":
        return "help"
    elif next_step == "get_weather":
        return "weather"
    elif next_step == "goodbye":
        return "end"
    else:
        return "chat"


def create_chat_graph():
    """
    创建聊天工作流图
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("classify", classify_intent)
    workflow.add_node("help", provide_help)
    workflow.add_node("weather", get_weather)
    workflow.add_node("chat", general_chat)
    workflow.add_node("goodbye", goodbye)

    # 添加边
    workflow.set_entry_point("classify")

    # 添加条件边
    workflow.add_conditional_edges(
        "classify",
        should_continue,
        {
            "help": "help",
            "weather": "weather",
            "chat": "chat",
            "end": "goodbye"
        }
    )

    # 添加结束边
    workflow.add_edge("help", END)
    workflow.add_edge("weather", END)
    workflow.add_edge("chat", END)
    workflow.add_edge("goodbye", END)

    # 编译图
    app = workflow.compile()
    return app


def main():
    """
    主函数: 运行交互式聊天
    """
    print("🤖 LangGraph 聊天机器人")
    print("输入 '帮助' 查看功能，输入 '退出' 结束对话")
    print("-" * 50)

    # 创建图
    chat_graph = create_chat_graph()

    # 初始化消息历史
    messages = [
        AIMessage(content="你好！我是你的AI助手。有什么可以帮助你的吗？")
    ]
    print(f"AI: {messages[0].content}")

    while True:
        # 获取用户输入
        user_input = input("\n你: ").strip()

        if not user_input:
            continue

        # 添加用户消息
        messages.append(HumanMessage(content=user_input))

        # 准备状态
        state: AgentState = {
            "messages": messages,
            "next_step": "",
            "context": ""
        }

        # 执行图
        result = chat_graph.invoke(state)

        # 更新消息历史
        messages = list(result["messages"])

        # 显示最新回复
        last_message = messages[-1]
        if isinstance(last_message, AIMessage):
            print(f"AI: {last_message.content}")

        # 检查是否结束
        if result.get("next_step") == "goodbye":
            break


if __name__ == "__main__":
    main()
