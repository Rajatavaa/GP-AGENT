import json
import re
from langchain_core.messages import HumanMessage


def start_agent(llm, tools):
    """Creates an agent with the given LLM and tools.
    If no tools, returns a plain chat agent.
    """
    if not tools:
        return llm

    return llm.bind_tools(tools)


def agent_node(state, agent):
    """Generic agent node that invokes the agent and extracts output."""
    user_input = state.get("input", " ")
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    output = (
        result.get("messages", [])[-1].content
        if result.get("messages")
        else str(result)
    )
    return {**state, "output": output}


def _execute_tool_calls(response, tools, state, success_prefix):
    """Execute any tool calls found in the response."""
    tool_calls = getattr(response, "tool_calls", None) or []

    if not tool_calls and hasattr(response, "additional_kwargs"):
        extra = response.additional_kwargs
        if "tool_calls" in extra:
            tool_calls = extra["tool_calls"]

    if not tool_calls:
        return None

    for tool_call in tool_calls:
        if isinstance(tool_call, dict):
            if "function" in tool_call:
                func = tool_call["function"]
                tool_name = func.get("name", "")
                try:
                    tool_args = json.loads(func.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    tool_args = func.get("arguments", {})
            else:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
        else:
            tool_name = getattr(tool_call, "name", "")
            tool_args = getattr(tool_call, "args", {})

        print(f"[DEBUG] Tool: {tool_name}")
        print(f"[DEBUG] Args: {json.dumps(tool_args, indent=2)}")

        for tool in tools:
            if tool.name == tool_name:
                tool_result = tool.invoke(tool_args)
                return {**state, "output": f"{success_prefix} {tool_result}"}

    return None


def slack_agent(state, llm, tools):
    """Agent specialized for Slack operations."""
    user_input = state.get("input", " ")

    tool_choice = {"type": "function", "function": {"name": tools[0].name}}
    agent = llm.bind_tools(tools, tool_choice=tool_choice)
    response = agent.invoke([HumanMessage(content=user_input)])

    result = _execute_tool_calls(response, tools, state, "Slack action completed!")
    if result:
        return result

    output = response.content if hasattr(response, "content") else str(response)
    return {**state, "output": output}


class Email_work:
    def email_agent(state, llm, tools):
        """Agent specialized for email operations.
        Supports both sending and reading emails based on user intent.
        """
        user_input = state.get("input", " ")
        user_input_lower = user_input.lower()
        prompt = f"You are decider based on the user input wether the intent is to send_message or read_message{user_input_lower}"
        result = llm.invoke(prompt)
        result = result.replace("<think>", "").replace("</think>", "").strip()

        if result == "read_message":
            return _handle_read_email(state, tools, user_input)
        else:
            return _handle_send_email(state, tools, user_input)

    def _handle_read_email(state, tools, user_input):
        """Handle reading/searching emails."""
        read_tool = None
        search_tool = None
        for tool in tools:
            if tool.name == "get_gmail_message":
                read_tool = tool
            elif tool.name == "gmail_search":
                search_tool = tool

        if not read_tool and not search_tool:
            return {**state, "output": "No email read/search tool available"}

        query = user_input
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", user_input)
        if email_match:
            query = f"from:{email_match.group(0)} OR to:{email_match.group(0)}"

        if search_tool:
            tool_result = search_tool.invoke({"query": query})
        else:
            tool_result = read_tool.invoke({"query": query})

        return {**state, "output": f"Email search result: {tool_result}"}

    def _handle_send_email(state, tools, user_input):
        """Handle sending emails."""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", user_input)
        to_email = email_match.group(0) if email_match else ""

        saying_match = re.search(r"saying\s+(.+)", user_input, re.IGNORECASE)
        body = saying_match.group(1).strip() if saying_match else user_input

        subject_match = re.search(
            r"(?:about|regarding|on)\s+(.+?)(?:\s+saying|\s*$)",
            user_input,
            re.IGNORECASE,
        )
        if subject_match:
            subject = subject_match.group(1).strip()
        else:
            words = body.split()[:6]
            subject = " ".join(words) if words else "Email"

        print("[DEBUG] Extracted email fields:")
        print(f"[DEBUG]   to: {to_email}")
        print(f"[DEBUG]   subject: {subject}")
        print(f"[DEBUG]   body: {body}")

        send_tool = None
        for tool in tools:
            if tool.name == "send_gmail_message":
                send_tool = tool
                break

        if not send_tool:
            return {**state, "output": "Send email tool not found"}

        if not to_email:
            return {**state, "output": "Could not find recipient email address"}

        tool_result = send_tool.invoke(
            {
                "to": to_email,
                "subject": subject,
                "message": body,
            }
        )

        return {**state, "output": f"Email sent successfully! {tool_result}"}


def general_agent_node(state, agent):
    """Fallback agent for general queries."""
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
    return {**state, "output": output}


def router(state, llm):
    """Routes the user input to the appropriate agent."""
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
    """Final output formatter."""
    return {"final_output": state.get("output", "")}
