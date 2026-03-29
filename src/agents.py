from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.utils.function_calling import convert_to_openai_function


def start_agent(llm, tools):
    if not tools:
        return create_agent(llm, tools)

    functions = [convert_to_openai_function(t) for t in tools]

    # Force tool usage for models that don't auto-call tools
    tool_choice = {"type": "function", "function": {"name": tools[0].name}}

    llm_with_tools = llm.bind(functions=functions, tool_choice=tool_choice)
    agent = create_agent(llm_with_tools, tools)
    return agent


def agent_node(state, agent):
    user_input = state.get("input", " ")
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    output = (
        result.get("messages", [])[-1].content
        if result.get("messages")
        else str(result)
    )
    return {**state, "output": output}


def slack_agent(state, llm, tools):
    "Agent specialized for slack"

    user_input = state.get("input", " ")

    functions = [convert_to_openai_function(t) for t in tools]
    tool_choice = {"type": "function", "function": {"name": tools[0].name}}

    llm_with_tools = llm.bind(functions=functions, tool_choice=tool_choice)
    response = llm_with_tools.invoke(user_input)

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            for tool in tools:
                if tool.name == tool_name:
                    tool_result = tool.invoke(tool_args)
                    return {**state, "output": f"Slack message sent! {tool_result}"}

    output = response.content if hasattr(response, "content") else str(response)
    return {**state, "output": output}


def email_agent(state, llm, tools):
    "Agent specialized for email"
    from langchain_core.utils.function_calling import convert_to_openai_function

    user_input = state.get("input", " ")

    functions = [convert_to_openai_function(t) for t in tools]
    tool_choice = {"type": "function", "function": {"name": tools[0].name}}

    llm_with_tools = llm.bind(functions=functions, tool_choice=tool_choice)
    response = llm_with_tools.invoke(user_input)

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            for tool in tools:
                if tool.name == tool_name:
                    tool_result = tool.invoke(tool_args)
                    return {
                        **state,
                        "output": f"Email sent successfully! {tool_result}",
                    }

    output = response.content if hasattr(response, "content") else str(response)
    return {**state, "output": output}


# This is the fallback if the previous agent nodes fails
def general_agent_node(state, agent):
    """
    Fallback agent
    """
    user_input = state.get("input", "")

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=f"You are a helpful assistant. Handle this:\n{user_input}"
                )
            ]
        }
    )

    output = (
        result.get("messages", [])[-1].content
        if result.get("messages")
        else str(result)
    )
    return {
        **state,
        "output": output,
    }


def router(state, llm):
    user_input = state["input"].lower()

    if "slack" in user_input:
        return "slack"
    if "email" in user_input or "mail" in user_input:
        return "email"

    prompt = f"""Classify intent: email, slack, or general. Input: {user_input}"""
    result = llm.invoke(prompt).content
    result = result.replace("<think>", "").replace("</think>", "").strip()
    result = result.lower().split()[0] if result.split() else "general"
    return result


def format_output(state):
    """
    Final output formatter
    """
    return {"final_output": state.get("output", "")}
