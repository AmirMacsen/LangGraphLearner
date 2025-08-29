"""
该示例存在的问题：
工具函数报错了，但是大模型依然会拿着我们的问题和工具的输出做逻辑推理，它依然会给出准确的答案
"""
import os

from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import ToolNode

load_dotenv()
model = init_chat_model(model="gpt-4", api_key=os.environ.get("OPENAI_API_KEY"),
                        base_url=os.environ.get("OPENAI_BASE_URL"), )


def handle_tool_errors(error: Exception) -> str:
    """Handle tool errors."""
    if isinstance(error, ZeroDivisionError):
        return  str(error)
    else:
        return "未知错误"

def add(a: int, b: int)-> int:
    """Add two numbers."""
    return a + b


def divide(a: int, b: int) -> int:
    """Divide two numbers."""
    if b==1:
        raise ZeroDivisionError("除数不能为1")
    return a / b

tools = ToolNode(
    tools=[divide, add],
    handle_tool_errors=handle_tool_errors
)
agent = create_react_agent(model=model,tools=tools, prompt="你是一个数学高手")

for chunk in agent.stream({
    "messages": [{"role": "user", "content": "请计算1/1"}]
}):
    print(chunk)
