import os
import threading

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages.utils import count_tokens_approximately
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

# 需要 pip install langmem
### 总结对话，而不传入所有内容
summary = SummarizationNode(
    token_counter=count_tokens_approximately, # 计算token数量
    model=model,
    max_tokens=256,
    max_tokens_before_summary=256,
    max_summary_tokens=128,
)

class State(AgentState):
    # 摘要存储
    context: dict[str, RunningSummary]

# 必须创建一个配置对象，主要是为了多个会话不会互相干扰，并且在需要的时候恢复之前的对话状态。
config = {
    "configurable": {
        "thread_id": threading.current_thread().ident
    }
}

agent = create_react_agent(
    model=model,
    tools=[add],
    prompt="你是一个聪明的人工智能助手",
    checkpointer=checkpointer,
    pre_model_hook=summary,
    state_schema=State,
)


def print_invoke(invoke):
    for key, val in invoke.items():
        print(key)
        for item in val:
            print(f"type: {type(item)}, value: {item}")

invoke_1 = agent.invoke({"messages": [{"role": "user", "content": "请计算1+1"}]}, config=config)
print_invoke(invoke_1)
print("==="*20)
invoke_2 = agent.invoke({"messages": [{"role": "user", "content": "再+10等于多少"}]}, config=config)
print_invoke(invoke_2)