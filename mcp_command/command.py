"""
在node中实现跳转，不用构建node的连接关系
"""
import operator
from typing import Annotated

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Command
from pydantic import BaseModel


class InputState(BaseModel):
    input_text: str


class OverallState(BaseModel):
    answer: Annotated[list, operator.add]
    foo:  Annotated[list, operator.add]
    input_str:  Annotated[list, operator.add]
    count:  Annotated[int, lambda x, y : x + y]


def node1(state: InputState) -> OverallState:

    answer = [state.input_text + " > answer"]
    foo = [state.input_text + " > foo"]
    input_str = [state.input_text]

    return OverallState(
        answer=answer,
        foo=foo,
        input_str=input_str,
        count=1,
    )


def node2(state: OverallState):
    if state.count < 3:
        return Command(
            goto="node1",
            update=InputState(
                input_text=state.input_str[-1] + " > node2 to node1"
            ),
        )
    else:
        return Command(
            goto=END,
            update=OverallState
        )


builder = StateGraph(OverallState,input_schema=InputState, output_schema=OverallState)

builder.add_node("node1", node1)
builder.add_node("node2", node2)

builder.add_edge(START, "node1")
builder.add_edge("node1", "node2")
builder.add_edge("node2", END)

graph = builder.compile()
png = graph.get_graph().draw_mermaid_png()
with open("dynamic_router.png", "wb") as f:
    f.write(png)
invoke = graph.invoke(InputState(input_text="Hello"))
print(invoke)