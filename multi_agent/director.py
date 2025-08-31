import operator
import os
import uuid
from typing import TypedDict, Annotated, List

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

load_dotenv()
class State(TypedDict):
    messages:Annotated[List[AnyMessage], operator.add]
    type:str


llm = init_chat_model(
    model="gpt-4",
    temperature=0.7,
    streaming=True,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE"),
)

node_types = ["supervisor", "weather", "joke", "couplet", "other"]

def supervisor_node(state: State):
    print(">>> supervisor node <<<")
    writer=get_stream_writer()
    writer({"node": "supervisor node"})
    ### 根据用户的问题对问题进行分类，分类结果保存在state的type字段
    prompt = """你是一个专业的客服助手，负责对用户的问题进行分类，并将任务分给其他Agent执行。
    如果用户的问题与天气相关，返回weather
    如果用户的问题是希望讲一个笑话，返回joke
    如果用户的问题是希望对对联，返回couplet
    如果用户的问题是其他的问题，返回other
    除了以上选项，不要返回其他任何内容
    """

    # 如果type已经存在，则返回
    if state.get("type"):
        writer({"node": "supervisor node", "message": f"已经处理过了，type: {state.get('type')}"})
        return {"type": END}

    message = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": state.get("messages")[-1].content}
    ]
    ai_response = llm.invoke(message)

    if ai_response.content not in node_types:
        writer({"node": "supervisor node", "message": f"无法识别的type: {ai_response.content}"})
        raise ValueError(f"模型无法识别的type: {ai_response.content}, 必须在以下选项中选择：{'/'.join(node_types)}")
    writer({"node": "supervisor node", "message": f"type: {ai_response.content}"})
    return {
        "messages": [ai_response],
        "type": ai_response.content,
    }


def weather_node(state: State):
    import asyncio
    async def _weather():
        writer = get_stream_writer()
        writer({"node": "weather node"})
        mcp_client = MultiServerMCPClient({
            "weather": {
                "url": "https://dashscope.aliyuncs.com/api/v1/mcps/zuimei-getweather/sse",
                "transport": "sse",
                "headers": {"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"}
            }
        })
        mcp_tools = await mcp_client.get_tools()
        agent = create_react_agent(
            model=llm,
            tools=mcp_tools,
            prompt="你是一个专业的天气预报专家，请根据用户问题给出天气预报。",
        )
        messages = [{"role": "user", "content": state.get("messages")[0].content}]
        final_result = None
        async for chunk in agent.astream({"messages": messages}):
            print(">>> weather agent chunk >>>")
            final_result = chunk
            print(chunk)
        return {"messages": [final_result.get("messages")], "type": state.get("type")}

    return asyncio.run(_weather())


def joke_node(state: State):
    print(">>> joke node <<<")
    writer=get_stream_writer()
    writer({"node": "joke node"})

    messages = [
        {"role": "system", "content": "你是一个讲笑话的大师，可以根据用户问题讲一个笑话"},
        {"role": "user", "content": state.get("messages")[-1].content}
    ]

    ai_response = llm.invoke(messages)
    writer({"node": "joke node", "message": ai_response.content})
    return {
        "messages": [ai_response],
        "type": state.get("type")
    }

def couplet_node(state: State):
    print(">>> couplet node <<<")
    writer=get_stream_writer()
    writer({"node": "couplet node"})
    return {
        "messages": [HumanMessage(content="couplet_node")],
        "type": "other"
    }

def other_node(state: State):
    print(">>> other node <<<")
    writer=get_stream_writer()
    writer({"node": "other node"})
    return {
        "messages": [HumanMessage(content="我暂时无法回答这个问题")],
        "type": "other"
    }

def routing_func(state: State):
    print(">>> routing func <<<")
    writer=get_stream_writer()
    writer({"node": "routing func"})
    if "type" in state and state["type"] == "weather":
        return "weather_node"
    elif "type" in state and state["type"] == "joke":
        return "joke_node"
    elif "type" in state and state["type"] == "couplet":
        return "couplet_node"
    return "other_node"

builder = StateGraph(State)
builder.add_node("supervisor_node", supervisor_node)
builder.add_node("weather_node", weather_node)
builder.add_node("joke_node", joke_node)
builder.add_node("couplet_node", couplet_node)
builder.add_node("other_node", other_node)

# 添加边
builder.add_edge(START, "supervisor_node")
builder.add_conditional_edges("supervisor_node", routing_func,
                              ["weather_node", "joke_node", "couplet_node", "other_node", END])

checkpointer = InMemorySaver()
config:RunnableConfig = {
    "configurable": {
        "thread_id": uuid.uuid4()
    }
}
graph = builder.compile(checkpointer=checkpointer)


if __name__ == '__main__':
    for chunk in graph.stream(input=State(messages=[HumanMessage(content="帮我查一下深圳的天气")]),
                              config=config, stream_mode="custom"):

        print('---------------')
        print(chunk)