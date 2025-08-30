import operator
import os
import threading
from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel


class State(BaseModel):
    messages: Annotated[list, operator.add]

load_dotenv()
llm = init_chat_model(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"),)
checkpointer = InMemorySaver()

"""
最终返回的状态就是输出
"""
def call_llm(state: State) -> State:
    response = llm.invoke(state.messages)
    print(response)
    state.messages.append({"role": "assistant", "content": response.content})
    return state

builder = StateGraph(State)
builder.add_node("call_llm", call_llm)
builder.add_edge(START, "call_llm")
builder.add_edge("call_llm", END)

graph = builder.compile(checkpointer=checkpointer)
config = {
    "configurable": {
        "thread_id": threading.current_thread().ident
    }
}
while True:
    user_input = input("User: ")
    if user_input == "exit":
        break
    invoke = graph.invoke(State(messages=[{"role": "user", "content": user_input}]), config=config)
    print(invoke)

