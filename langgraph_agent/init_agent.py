import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

load_dotenv()

def add(a: int, b: int)-> int:
    """Add two numbers together."""
    return a + b

# 创建一个model， 调用的是langchain能力
model = init_chat_model(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"),)

# 创建一个React代理，langgraph的能力
agent = create_react_agent(
    model=model,
    tools = [add],
    prompt="你是一个聪明的人工智能助手",
)

# 用户发起请求
def query_and_print(query):
    invoke = agent.invoke({"messages": [{"role": "user", "content": "请计算1+1"}]})

    print(invoke)

# 流式输出
"""
stream_mode 包含几种模式："values", "updates", "checkpoints", "tasks", "debug", "messages", "custom"
updates：流式输出每个工具的调用过程
messages: 流式输出模型输出的每个token
values: 每一次拿到的chunks
custom: 自定义输出，可以使用get_stream_writer输出流，添加自定义的内容
"""
def query_and_print_stream(query):
    for chunk in agent.stream({
        "messages": [{"role": "user", "content": query}],
    }, stream_mode="values"):
        print(chunk)

if __name__ == '__main__':
    query_and_print("请计算1+1")
    query_and_print_stream("请计算1+1")


