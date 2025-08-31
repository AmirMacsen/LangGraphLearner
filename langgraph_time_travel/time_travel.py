"""
time travel 功能是结合thead_id 和 node执行的id可以再次对某一个node执行
"""
import os
import uuid

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel


class State(BaseModel):
    author: str
    joke: str
    score: float

load_dotenv()
model = init_chat_model(model="gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"),)


def generate_author(stat:State) -> State:
    """生成作者"""
    invoke = model.invoke("根据实际上著名的作家，帮我选取一个作家名称, 返回作家名称即可。")
    author = invoke.content
    return State(author=author, joke="", score=0)

def generate_joke(state: State) -> State:
    """生成笑话"""
    invoke = model.invoke(f"请用{state.author}的幽默感，生成一个笑话")
    joke = invoke.content
    return State(author=state.author, joke=joke, score=state.score)


# 对笑话的搞笑程度进行打分
def rate_joke(state: State) -> State:
    invoke = model.invoke(f"请对下面笑话进行打分，打分范围是0-10，0是最差，10是最好，请返回一个数字，不要返回其他内容。\n{state.joke}")
    score = float(invoke.content)
    return State(author=state.author, joke=state.joke, score=score)


builder = StateGraph(State)

builder.add_node("generate_author", generate_author)
builder.add_node("generate_joke", generate_joke)
builder.add_node("rate_joke", rate_joke)
builder.add_edge(START, "generate_author")
builder.add_edge("generate_author", "generate_joke")
builder.add_edge("generate_joke", "rate_joke")
builder.add_edge("rate_joke", END)


config:RunnableConfig = {
    "configurable": {
        "thread_id": uuid.uuid4()
    }
}
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

state = graph.invoke(input=State(author="", joke="", score=0), config=config)
print(state)

selected_state = None
if state.get("score") < 9:
    # 获取到 整个图的状态流程
    for history in graph.get_state_history(config=config):
        # 如果下一个是rate_joke， 实际上就是generate_joke
        if history.next and history.next[0] == "generate_joke":
            selected_state = history
            break

config = selected_state.config
# 更新作家名称 可选, values必须传递dict，这一步是更新状态，状态在内部是用dict保存的
new_config = graph.update_state(config=config, values={"author": "鲁迅", "joke": "", "score": 0})

# 从更新点开始执行
state = graph.invoke(None, config=new_config)
print(state)


