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

def node1(state: MainState):
    state.answer.append("answer")
    return state


main_builder = StateGraph(MainState)
main_builder.add_node("node1", node1)
main_builder.add_edge(START, "node1")
main_builder.add_edge("node1", END)

main_graph = main_builder.compile()

for chunk in main_graph.stream(MainState(answer=["process node"]), stream_mode="updates"):
    print(chunk)
