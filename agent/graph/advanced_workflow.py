"""
LangGraph 高级工作流示例

展示高级功能:
- 并行执行 (Fan-out/Fan-in)
- 循环和迭代
- 工具调用集成
- 更复杂的状态管理
"""

import os
import asyncio
from typing import TypedDict, Annotated, Sequence, List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

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


# 定义工具
@tool
def search_web(query: str) -> str:
    """搜索网络信息"""
    return f"搜索 '{query}' 的结果: 这是模拟的搜索结果..."


@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except:
        return f"无法计算: {expression}"


@tool
def save_note(content: str) -> str:
    """保存笔记"""
    return f"笔记已保存: {content[:50]}..."


# 工具集合
tools = [search_web, calculate, save_note]


# 定义状态
class AdvancedState(TypedDict):
    """高级工作流状态"""
    messages: Annotated[Sequence[BaseMessage], "消息历史"]
    query: Annotated[str, "用户查询"]
    search_results: Annotated[List[str], "搜索结果"]
    calculation_results: Annotated[List[str], "计算结果"]
    iteration_count: Annotated[int, "迭代计数"]
    should_continue: Annotated[bool, "是否继续"]
    final_answer: Annotated[str, "最终答案"]


# 初始化 LLM (使用 Moonshot/Kimi)
llm = ChatOpenAI(
    model="moonshot-v1-8k",
    temperature=0.7,
)

# 绑定工具的 LLM
llm_with_tools = llm.bind_tools(tools)


def analyze_query(state: AdvancedState) -> AdvancedState:
    """
    分析查询,决定执行路径
    """
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    state["query"] = last_message
    state["iteration_count"] = 0
    state["search_results"] = []
    state["calculation_results"] = []

    # 分析查询类型
    needs_search = any(word in last_message for word in ["搜索", "查找", "search", "find"])
    needs_calculate = any(word in last_message for word in ["计算", "算", "calculate", "math"])

    if needs_search and needs_calculate:
        state["should_continue"] = True
    elif needs_search or needs_calculate:
        state["should_continue"] = True
    else:
        state["should_continue"] = False

    return state


def parallel_tools(state: AdvancedState) -> AdvancedState:
    """
    并行调用多个工具
    """
    query = state["query"]

    # 使用 LLM 决定调用哪些工具
    response = llm_with_tools.invoke([
        HumanMessage(content=f"基于这个查询,决定使用什么工具: {query}")
    ])

    state["messages"] = list(state["messages"]) + [response]

    # 如果有工具调用,这里会包含 tool_calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['arguments'] if 'arguments' in tool_call else tool_call.get('args', '{}')

            if tool_name == 'search_web':
                result = search_web.invoke(tool_args)
                state["search_results"].append(result)
            elif tool_name == 'calculate':
                result = calculate.invoke(tool_args)
                state["calculation_results"].append(result)
            elif tool_name == 'save_note':
                result = save_note.invoke(tool_args)

    return state


def process_results(state: AdvancedState) -> AdvancedState:
    """
    处理工具执行结果
    """
    results = []

    if state["search_results"]:
        results.append("🔍 搜索结果:")
        for r in state["search_results"]:
            results.append(f"  - {r}")

    if state["calculation_results"]:
        results.append("🧮 计算结果:")
        for r in state["calculation_results"]:
            results.append(f"  - {r}")

    if not results:
        results.append("🤔 没有需要处理的工具结果")

    result_text = "\n".join(results)
    state["final_answer"] = result_text

    # 添加 AI 回复
    state["messages"] = list(state["messages"]) + [
        AIMessage(content=f"处理完成!\n{result_text}")
    ]

    return state


def check_iteration(state: AdvancedState) -> str:
    """
    检查是否需要继续迭代
    """
    state["iteration_count"] += 1

    # 最多迭代 3 次
    if state["iteration_count"] < 3 and state["should_continue"]:
        return "continue"
    else:
        return "finish"


def refine_query(state: AdvancedState) -> AdvancedState:
    """
    优化查询以进行下一轮迭代
    """
    # 模拟查询优化
    state["query"] = f"优化后的查询: {state['query']}"
    return state


def generate_final_response(state: AdvancedState) -> AdvancedState:
    """
    生成最终响应
    """
    if not state.get("final_answer"):
        # 如果没有工具结果,直接生成回复
        response = llm.invoke(state["messages"])
        state["messages"] = list(state["messages"]) + [response]
    else:
        # 基于工具结果生成综合回复
        summary = f"""
基于分析,我为你整理了以下信息:

{state['final_answer']}

需要我进一步解释什么吗？
        """
        state["messages"] = list(state["messages"]) + [AIMessage(content=summary)]

    return state


def create_advanced_graph():
    """
    创建高级工作流图
    """
    workflow = StateGraph(AdvancedState)

    # 添加节点
    workflow.add_node("analyze", analyze_query)
    workflow.add_node("tools", parallel_tools)
    workflow.add_node("process", process_results)
    workflow.add_node("refine", refine_query)
    workflow.add_node("finalize", generate_final_response)

    # 设置入口点
    workflow.set_entry_point("analyze")

    # 添加边
    workflow.add_edge("analyze", "tools")
    workflow.add_edge("tools", "process")

    # 添加条件边 - 循环或结束
    workflow.add_conditional_edges(
        "process",
        check_iteration,
        {
            "continue": "refine",
            "finish": "finalize"
        }
    )

    workflow.add_edge("refine", "tools")  # 循环回工具调用
    workflow.add_edge("finalize", END)

    # 编译图
    app = workflow.compile()
    return app


def main():
    """
    运行高级工作流示例
    """
    print("🚀 LangGraph 高级工作流示例")
    print("=" * 50)

    # 创建图
    advanced_graph = create_advanced_graph()

    # 示例查询
    test_queries = [
        "帮我搜索 Python 编程的资料,并计算 25 * 48",
        "计算 123 + 456",
        "今天天气怎么样？"  # 这个不会触发工具
    ]

    for query in test_queries:
        print(f"\n👤 用户: {query}")
        print("-" * 50)

        # 初始化状态
        state: AdvancedState = {
            "messages": [HumanMessage(content=query)],
            "query": "",
            "search_results": [],
            "calculation_results": [],
            "iteration_count": 0,
            "should_continue": False,
            "final_answer": ""
        }

        # 执行图
        result = advanced_graph.invoke(state)

        # 显示结果
        messages = result["messages"]
        for msg in messages:
            if isinstance(msg, AIMessage):
                print(f"🤖 AI: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"🔧 Tool: {msg.content[:100]}...")

        print("=" * 50)


if __name__ == "__main__":
    main()
