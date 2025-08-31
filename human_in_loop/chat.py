# ------------------------------
# 1. 核心依赖导入
# ------------------------------
from typing import TypedDict, Literal
import uuid
import json  # 新增：替换eval，安全解析JSON
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command, Interrupt  # 显式导入Interrupt类型


# ------------------------------
# 2. 定义图状态（存储工具调用全流程数据）
# ------------------------------
class ToolReviewState(TypedDict):
    tool_calls: list[dict]
    human_approval: Literal["approve", "modify", "reject"] | None
    human_modified_tool_calls: list[dict] | None
    tool_exec_result: str | None


# ------------------------------
# 3. 核心节点函数（流程逻辑）
# ------------------------------
def llm_suggest_tool(state: ToolReviewState) -> ToolReviewState:
    """模拟 LLM 生成工具调用建议（真实场景替换为LLM调用）"""
    suggested_tool = [
        {
            "name": "get_weather",
            "params": {
                "city": "Shanghai",
                "date": "2024-06-01",
                "unit": "celsius"
            }
        }
    ]
    print(f"✅ LLM 生成待审查工具调用：")
    print(f"   工具名：{suggested_tool[0]['name']}")
    print(f"   参数：{suggested_tool[0]['params']}\n")
    return ToolReviewState(
        tool_calls=suggested_tool,
        human_approval=None,
        human_modified_tool_calls=None,
        tool_exec_result=None
    )



def human_review_tool(state: ToolReviewState) -> Command[Literal["execute_tool", "end"]]:
    """人类审查工具调用（核心 interrupt 节点）"""
    # 调用 interrupt：向用户传递审查信息
    print(f"执行工具审查")
    user_raw_input = interrupt(
        {
            "审查任务": "请确认是否允许执行以下工具调用",
            "待审查工具": state["tool_calls"][0]["name"],
            "待审查参数": state["tool_calls"][0]["params"],
            "可选操作": {
                "approve": "批准执行（直接运行工具）",
                "reject": "拒绝执行（流程终止）",
                "modify": "修改参数后执行（需按格式补充新参数）"
            },
            "输入格式说明": [
                "1. 批准：直接输入 approve",
                "2. 拒绝：直接输入 reject",
                "3. 修改：输入 modify|新工具调用JSON（示例：modify|[{\"name\":\"get_weather\",\"params\":{\"city\":\"Beijing\",\"date\":\"2024-06-01\"}}]）"
            ]
        }
    )

    # 解析用户输入（用json.loads替换eval，解决安全风险）
    if user_raw_input.strip() == "approve":
        return Command(
            goto="execute_tool",
            update={"human_approval": "approve"}
        )
    elif user_raw_input.strip() == "reject":
        return Command(
            goto="end",
            update={
                "human_approval": "reject",
                "tool_exec_result": "❌ 工具未执行（用户拒绝）"
            }
        )
    elif user_raw_input.startswith("modify|"):
        try:
            _, modified_tool_json = user_raw_input.split("|", 1)
            modified_tool = json.loads(modified_tool_json)  # 安全解析JSON（修复原eval风险）
            if not isinstance(modified_tool, list) or len(modified_tool) == 0:
                raise ValueError("修改后的工具调用必须是非空列表")
            return Command(
                goto="execute_tool",
                update={
                    "human_approval": "modify",
                    "human_modified_tool_calls": modified_tool,
                    "tool_calls": modified_tool
                }
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ JSON格式错误：{str(e)}，请检查参数格式")
        except Exception as e:
            raise ValueError(f"❌ 修改参数错误：{str(e)}，请重新输入")
    else:
        raise ValueError(f"❌ 无效操作：{user_raw_input}，仅支持 approve/reject/modify")


def execute_tool(state: ToolReviewState) -> ToolReviewState:
    """执行工具调用（仅在用户批准/修改后触发）"""
    tool = state["tool_calls"][0]
    tool_name = tool["name"]
    tool_params = tool["params"]

    print(f"🔧 开始执行工具：{tool_name}")
    print(f"   执行参数：{tool_params}")
    try:
        if tool_name == "get_weather":
            exec_result = f"✅ 工具执行成功：{tool_params['city']} {tool_params['date']} 的天气为 25℃，晴"
        else:
            exec_result = f"❌ 工具执行失败：未知工具 {tool_name}"
    except Exception as e:
        exec_result = f"❌ 工具执行异常：{str(e)}"

    print(f"   执行结果：{exec_result}\n")
    return {**state, "tool_exec_result": exec_result}


# ------------------------------
# 4. 构建 LangGraph 图
# ------------------------------
def build_tool_review_graph() -> StateGraph:
    graph_builder = StateGraph(ToolReviewState)

    # 添加节点
    graph_builder.add_node("llm_suggest_tool", llm_suggest_tool)
    graph_builder.add_node("human_review_tool", human_review_tool)
    graph_builder.add_node("execute_tool", execute_tool)
    graph_builder.add_node("end", lambda x: x)

    # 定义流向
    graph_builder.add_edge(START, "llm_suggest_tool")
    graph_builder.add_edge("llm_suggest_tool", "human_review_tool")
    graph_builder.add_edge("execute_tool", "end")
    graph_builder.add_edge("end", END)

    # 配置状态保存
    checkpointer = MemorySaver()
    graph = graph_builder.compile(
        checkpointer=checkpointer,
    )
    return graph


# ------------------------------
# 5. 运行流程图（主入口：修复IndexError核心部分）
# ------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("📌 LangGraph 工具执行审查流程启动")
    print("=" * 60 + "\n")

    # 1. 构建图
    tool_review_graph: StateGraph = build_tool_review_graph()

    # 2. 生成线程ID
    thread_id = str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": thread_id}}

    # 3. 首次运行：触发 interrupt
    print("🚀 首次运行：LLM 生成工具建议后，将暂停等待您的审查...\n")

    interrupt_obj = None
    for chunk in tool_review_graph.stream(
        input={
            "tool_calls": [],
            "human_approval": None,
            "human_modified_tool_calls": None,
            "tool_exec_result": None
        },
        config=thread_config
    ):
        print("chunk >>>", chunk)

        # ✅ stream 产出通常是 (node_name, value)
        if "__interrupt__" in chunk:
            # 在新版本里，value 不在 chunk 里，而是在 state 里
            interrupt_obj = chunk.get("__interrupt__")[0]
            print("=" * 40)
            print("⏸️ 流程已暂停：请进行工具审查")
            print("=" * 40)
            print("中断信息:", interrupt_obj)
            print("=" * 40 + "\n")


    if interrupt_obj:
        user_input = input("请输入您的操作（approve/reject/modify）：").strip()

        # 6. 恢复流程
        print(f"\n🔄 恢复流程：您选择的操作是「{user_input}」")
        final_state = tool_review_graph.invoke(
            input=Command(resume=user_input),
            config=thread_config
        )

        # 7. 输出最终结果
        print("\n" + "=" * 60)
        print("📋 流程结束：最终状态汇总")
        print("=" * 60)
        print(f"用户审查结果：{final_state['human_approval']}")
        print(f"修改后的工具（若有）：{final_state['human_modified_tool_calls'] or '无'}")
        print(f"工具执行结果：{final_state['tool_exec_result']}")
        print("=" * 60)
    else:
        raise RuntimeError("❌ 未捕获到中断，请检查配置")
