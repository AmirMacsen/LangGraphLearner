from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel


class InputState(BaseModel):
    """
    The state of the agent.
    """
    input_str: str

class OverallState(BaseModel):
    foo:str
    input_str: str
    answer:str


class EndState(BaseModel):
    answer:str


builder = StateGraph(OverallState, input_schema=InputState, output_schema=EndState)

def node1(state: InputState) -> OverallState:
    return OverallState(foo=state.input_str + "> node1", input_str=state.input_str, answer="")

def node2(state: OverallState) -> EndState:
    return EndState(answer=state.foo + "> node2")

# 添加node
builder.add_node("node1", node1)
builder.add_node("node2", node2)

# 添加edge
builder.add_edge(START, "node1")
builder.add_edge("node1", "node2")
builder.add_edge("node2", END)

graph = builder.compile()

# 绘制流程图
graph_png = graph.get_graph().draw_mermaid_png()
with open("state_graph.png", "wb") as f:
    f.write(graph_png)

invoke = graph.invoke(InputState(input_str="Hello"))
print(invoke)
