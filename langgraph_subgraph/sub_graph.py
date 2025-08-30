""""
sub graph
"""
import operator
from typing import Annotated

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel


class MainState(BaseModel):
    answer: Annotated[list, operator.add]

class SubState(BaseModel):
    foo: Annotated[list, operator.add]


def node1(state: MainState):
    state.answer.append("answer")
    #### important ####
    #### 这里为什么不会传递answer到子图中去？
    #### 因为每个graph维护了一个状态模板，每个图的状态模板不会传递给其他图
    return SubState(foo=state.answer)

def node2(state: SubState):
    state.foo.append("foo")
    print("node2:", state)
    return state



sub_builder = StateGraph(SubState)
sub_builder.add_node("node2", node2)
sub_builder.add_edge(START, "node2")
sub_builder.add_edge("node2", END)
sub_graph = sub_builder.compile()


main_builder = StateGraph(MainState)
main_builder.add_node("node1", node1)
main_builder.add_node("sub_node", sub_graph)
main_builder.add_edge(START, "node1")
main_builder.add_edge("node1", "sub_node")
main_builder.add_edge("sub_node", END)

main_graph = main_builder.compile()

invoke = main_graph.invoke(MainState(answer=["process node1"]))
print(invoke)
