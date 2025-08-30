from langgraph.constants import START, END
from langgraph.errors import GraphRecursionError
from langgraph.graph import StateGraph
from pydantic import BaseModel


class InputState(BaseModel):
    count:int = 0
    input_str: str

class OverallState(BaseModel):
    answer:str
    foo:str
    input_str: str
    count:int = 0

class EndState(BaseModel):
    answer:str


def node1(state: InputState) -> OverallState:
    state.count += 1
    state.input_str += "1"
    print("node1",  state)
    return OverallState(answer="answer", foo="foo", input_str=state.input_str, count=state.count)

def node2(state: OverallState) -> EndState:
    return EndState(answer=state.answer)


builder = StateGraph(OverallState,input_schema=InputState, output_schema=EndState)


builder.add_node("node1", node1)
builder.add_node("node2", node2)

def node_router(state: OverallState) -> str:
    if len(state.input_str) > 2:
        return "node1"
    else:
        return "node2"
builder.add_edge(START, "node1")
# 添加条件边
builder.add_conditional_edges("node1", node_router, )
builder.add_edge("node2", END)

graph = builder.compile()

png = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png)

### 设置循环最大次数
config = {"recursion_limit": 10}

try:
    invoke = graph.invoke(InputState(input_str="111"), config=config)
    print(invoke)
except GraphRecursionError as e:
    print("循环次数超过限制")

