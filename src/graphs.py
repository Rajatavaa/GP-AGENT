from langgraph.graph import StateGraph, END, START
from typing import TypedDict

from .agents import email_agent, general_agent_node, slack_agent, router
from .email import email_tools
from .slack import slack_tools


class Agentstate(TypedDict):
    input: str
    output: str


def build_graph(email_agent_node, slack_agent_node, general_agent, llm):
    graph = StateGraph(Agentstate)
    graph.add_node("router_node", lambda state: state)

    graph.add_node("email_node", lambda state: email_agent(state, llm, email_tools))

    graph.add_node("slack_node", lambda state: slack_agent(state, llm, slack_tools))

    graph.add_node(
        "general_node", lambda state: general_agent_node(state, general_agent)
    )

    graph.add_edge(START, "router_node")

    graph.add_conditional_edges(
        "router_node",
        lambda state: router(state, llm),
        {
            "slack": "slack_node",
            "email": "email_node",
            "general": "general_node",
        },
    )

    graph.add_edge("email_node", END)
    graph.add_edge("slack_node", END)
    graph.add_edge("general_node", END)

    return graph
