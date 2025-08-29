import asyncio
import os
import threading
from typing import Sequence

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()
model = init_chat_model(model="gpt-4",
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=os.environ.get("OPENAI_BASE_URL"))

mcp_config = {
    "math": {
        "command": "python",
        "args": ["D:\\workspace\\py\\PythonProject\\langgraph_demo\\langgraph_mcp\\math_server.py"],
        "transport": "stdio"
    },
    "weather": {
        "url": "http://localhost:8000/mcp",
        "transport": "streamable_http"
    }
}

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
        max_tokens=384,
        start_on="human",
        end_on=("human", "tool"),
    )
    return {"llm_input_messages": trimmed_messages}

checkpointer = InMemorySaver()

mcp_client = MultiServerMCPClient(connections=mcp_config)

async def get_mcp_tools(client:MultiServerMCPClient) -> Sequence[BaseTool]:
    mcp_tools = await client.get_tools()
    return mcp_tools

async def main():
    mcp_tools = await get_mcp_tools(mcp_client)
    print(mcp_tools)
    agent = create_react_agent(
        model=model,
        tools=mcp_tools,
        prompt="你是一个聪明的人工智能助手",
        checkpointer=checkpointer,
        pre_model_hook=pre_model_hook,
    )

    def print_invoke(invoke):
        for key, val in invoke.items():
            print(key)
            for item in val:
                print(f"type: {type(item)}, value: {item}")

    while True:
        query = input("请输入你的问题：")
        message = {"messages": [{"role": "user", "content": query}]}
        # 必须使用异步调用
        invoke = await agent.ainvoke(message, config=config)
        print_invoke(invoke)
        print("=="*20)

if __name__ == '__main__':
    asyncio.run(main())
