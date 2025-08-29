import os
import threading

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langmem.short_term import SummarizationNode, RunningSummary

load_dotenv()
@tool()
def add(a: int, b: int)-> int:
    """
    计算两个int数的和
    :param a:
    :param b:
    :return: 返回int
    """
    return a + b

model = init_chat_model(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))

tool_node = ToolNode(
    tools=[add],
)

# 构建一个记忆存储组件
checkpointer = InMemorySaver()

# 必须创建一个配置对象，主要是为了多个会话不会互相干扰，并且在需要的时候恢复之前的对话状态。
config = {
    "configurable": {
        "thread_id": threading.current_thread().ident
    }
}

def pre_model_hook(state):
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=100,
        start_on="human",
        end_on=("human", "tool"),
    )
    return {"llm_input_messages": trimmed_messages}

agent = create_react_agent(
    model=model,
    tools=[add],
    prompt="你是一个聪明的人工智能助手",
    checkpointer=checkpointer,
    pre_model_hook=pre_model_hook,
)


def print_invoke(invoke):
    for key, val in invoke.items():
        print(key)
        for item in val:
            print(f"type: {type(item)}, value: {item}")


# 第一次计算
print("=== 第一次计算 ===")
invoke_1 = agent.invoke({"messages": [{"role": "user", "content": "请计算1+1"}]}, config=config)
print_invoke(invoke_1)

# 第二次计算（基于之前的对话历史）
print("\n=== 第二次计算 ===")
invoke_2 = agent.invoke({"messages": [{"role": "user", "content": "请将刚才的结果再加10"}]}, config=config)
print_invoke(invoke_2)

# 第三次计算（继续增加对话历史）
print("\n=== 第三次计算 ===")
invoke_3 = agent.invoke({"messages": [{"role": "user", "content": "请将刚才的结果再加100"}]}, config=config)
print_invoke(invoke_3)

# 第四次计算（继续增加对话历史）
print("\n=== 第四次计算 ===")
invoke_4 = agent.invoke({"messages": [{"role": "user", "content": "请将刚才的结果再加1000"}]}, config=config)
print_invoke(invoke_4)

# 第五次计算（继续增加对话历史）
print("\n=== 第五次计算 ===")
invoke_5 = agent.invoke({"messages": [{"role": "user", "content": "请将刚才的结果再加10000"}]}, config=config)
print_invoke(invoke_5)

# 第六次计算（继续增加对话历史，这时应该触发trim）
print("\n=== 第六次计算 ===")
invoke_6 = agent.invoke({"messages": [{"role": "user", "content": "请将刚才的结果再加100000"}]}, config=config)
print_invoke(invoke_6)