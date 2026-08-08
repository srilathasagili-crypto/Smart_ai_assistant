from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from graph.state import AssistantState
from graph.nodes import chat_node, tool_node
from memory.chat_history import get_checkpointer


def build_graph():
    builder = StateGraph(AssistantState)

    builder.add_node("chat", chat_node)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "chat")
    builder.add_conditional_edges(
        "chat",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "chat")

    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer)