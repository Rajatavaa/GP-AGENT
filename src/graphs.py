from langgraph.graph import StateGraph, END, START
from typing import Any, TypedDict

from .agents import general_agent_node, Slack_work, Email_work
from .router import router, should_compose
from .utils import _llm_compose_message
from .tools.email_tool import email_tools
from .tools.slack_tool import slack_tools


class Agentstate(TypedDict):
    input: str
    output: Any
    composed_message: str


def build_graph(general_agent, llm):
    graph = StateGraph(Agentstate)
    graph.add_node("router_node", lambda state: state)

    graph.add_node("llm_compose", lambda state: _llm_compose_message(state, llm))

    graph.add_node(
        "slack_list_channels",
        lambda state: Slack_work.handle_slack_list_channels(state, slack_tools),
    )
    graph.add_node(
        "slack_send_message",
        lambda state: Slack_work.handle_slack_send(state, slack_tools, llm),
    )
    graph.add_node(
        "slack_read_messages",
        lambda state: Slack_work.handle_slack_read(state, slack_tools),
    )

    graph.add_node(
        "email_send_email",
        lambda state: Email_work.handle_email_send(state, email_tools, llm),
    )
    graph.add_node(
        "email_read_email",
        lambda state: Email_work.handle_email_read(state, email_tools),
    )

    graph.add_node(
        "general_chat", lambda state: general_agent_node(state, general_agent)
    )

    graph.add_edge(START, "router_node")

    graph.add_conditional_edges(
        "router_node",
        lambda state: router(state, llm),
        {
            "llm_compose": "llm_compose",
            "slack_list_channels": "slack_list_channels",
            "slack_send_message": "slack_send_message",
            "slack_read_messages": "slack_read_messages",
            "email_send_email": "email_send_email",
            "email_read_email": "email_read_email",
            "general_chat": "general_chat",
        },
    )

    graph.add_conditional_edges(
        "llm_compose",
        lambda state: should_compose(state, llm),
        {
            "email": "email_send_email",
            "slack": "slack_send_message",
            "general": "general_chat",
        },
    )

    graph.add_edge("slack_list_channels", END)
    graph.add_edge("slack_send_message", END)
    graph.add_edge("slack_read_messages", END)
    graph.add_edge("email_send_email", END)
    graph.add_edge("email_read_email", END)
    graph.add_edge("general_chat", END)

    return graph
