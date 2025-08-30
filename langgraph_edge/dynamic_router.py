import operator
from typing import Annotated, List, Optional, Any

from langchain_core.runnables import RunnableConfig
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Send
from pydantic import BaseModel, field_validator



class InputState(BaseModel):
    input_text: str  
    count: int

    @field_validator('input_text')
    def input_text_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError('input_text必须是字符串类型')
        return v



class OverallState(BaseModel):
    
    answer_list: Annotated[List[str],  operator.add] = []
    
    foo_list: Annotated[List[str],  operator.add] = []
    
    input_str_list: Annotated[List[str],  operator.add] = []
    
    count: Annotated[int,  lambda curr, upd: curr + upd] = 0

    
    @field_validator('answer_list', 'foo_list', 'input_str_list')
    def fields_must_be_list(cls, v):
        if not isinstance(v, list):
            raise ValueError(f'字段必须是列表类型，当前类型：{type(v).__name__}，值：{v}')
        for item in v:
            if not isinstance(item, str):
                raise ValueError(f'列表元素必须是字符串，当前元素类型：{type(item).__name__}，元素：{item}')
        return v

    @field_validator('count')
    def count_must_be_int(cls, v):
        if not isinstance(v, int):
            raise ValueError(f'count必须是整数类型，当前类型：{type(v).__name__}，值：{v}')
        return v



class FinishState(BaseModel):
    final_answer: str  
    final_inputs: str  
    total_count: int  



def print_state_debug(name: str, state: Any, stage: str):
    print(f"\n=== 调试日志：{name} - {stage} ===")
    if isinstance(state, OverallState):
        print(f"answer_list类型：{type(state.answer_list).__name__}，值：{state.answer_list}")
        print(f"foo_list类型：{type(state.foo_list).__name__}，值：{state.foo_list}")
        print(f"input_str_list类型：{type(state.input_str_list).__name__}，值：{state.input_str_list}")
        print(f"count类型：{type(state.count).__name__}，值：{state.count}")
    elif isinstance(state, InputState):
        print(f"input_text类型：{type(state.input_text).__name__}，值：{state.input_text}")
        print(f"count类型：{type(state.count).__name__}，值：{state.count}")
    elif isinstance(state, FinishState):
        print(f"final_answer类型：{type(state.final_answer).__name__}，值：{state.final_answer}")
        print(f"final_inputs类型：{type(state.final_inputs).__name__}，值：{state.final_inputs}")
        print(f"total_count类型：{type(state.total_count).__name__}，值：{state.total_count}")
    else:
        print(f"未知状态类型：{type(state).__name__}")



def node1(state: InputState) -> OverallState:
    new_count = state.count + 1
    new_input_str = state.input_text + "1"

    print_state_debug("node1", state, "输入状态")
    result = OverallState(
        answer_list=[f"answer_{new_count}"],  
        foo_list=[f"foo_{new_count}"],  
        input_str_list=[new_input_str],  
        count=new_count
    )
    print_state_debug("node1", result, "返回状态")
    return result



def debug_node(state: OverallState) -> OverallState:
    print_state_debug("debug_node", state, "并行合并后状态")
    return state



def node2(state: OverallState) -> FinishState:
    print_state_debug("node2", state, "输入状态")
    
    merged_answer = ", ".join(state.answer_list) if state.answer_list else "无结果"
    merged_inputs = " | ".join(state.input_str_list) if state.input_str_list else "无输入"
    
    result = FinishState(
        final_answer=merged_answer,  
        final_inputs=merged_inputs,  
        total_count=state.count  
    )
    print_state_debug("node2", result, "返回状态")
    return result



def node_router(state: InputState) -> List[Send] | str:
    print_state_debug("router", state, "输入状态")
    if state.count < 1:
        return [
            Send("node1", InputState(
                input_text=state.input_text,
                count=state.count
            )) for _ in range(3)
        ]
    return "node2"






builder = StateGraph(
    state_schema=OverallState,
    input_schema=InputState,
    output_schema=FinishState,
)


builder.add_node("node1", node1)
builder.add_node("debug_node", debug_node)
builder.add_node("node2", node2)


builder.add_conditional_edges(START, node_router)
builder.add_edge("node1", "debug_node")
builder.add_edge("debug_node", "node2")
builder.add_edge("node2", END)


graph = builder.compile()

try:
    print("=== 开始执行流程 ===")

    ### 最终的执行结果会被转换为dict类型
    result = graph.invoke(InputState(input_text="Hello", count=0))

    print("\n=== 执行成功！最终结果 ===")
    print(f"最终答案：{result.get('final_answer')}")
    print(f"最终输入：{result.get('final_inputs')}")
    print(f"总计数：{result.get('total_count')}")
except Exception as e:
    print(f"\n=== 执行错误 ===")
    print(f"错误类型：{type(e).__name__}")
    print(f"错误详情：{str(e)}")
    import traceback

    traceback.print_exc()