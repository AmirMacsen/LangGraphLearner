import os
import threading

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, create_react_agent

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

agent = create_react_agent(
    model=model,
    tools=[add],
    prompt="你是一个聪明的人工智能助手",
    checkpointer=checkpointer,
)

invoke_1 = agent.invoke({"messages": [{"role": "user", "content": "请计算1+1"}]}, config=config)
print(invoke_1["messages"][-1].pretty_print())
invoke_2 = agent.invoke({"messages": [{"role": "user", "content": "再+10等于多少"}]}, config=config)
print(invoke_2["messages"][-1].pretty_print())