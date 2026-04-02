import ast
import re
from datetime import datetime
from langchain_core.messages import HumanMessage


def start_agent(llm, tools):
    """Creates an agent with the given LLM and tools.
    If no tools, returns a plain chat agent.
    """
    if not tools:
        return llm

    return llm.bind_tools(tools)


DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _confirm_message(message, llm=None):
    """Show message to user and let them confirm, edit, or cancel."""
    print(f"\n  {BOLD}Preview:{RESET}")
    for line in message.split("\n"):
        print(f"    {line}")
    print(f"\n  {DIM}[Y] Send  [E] Edit  [C] Cancel{RESET}")

    while True:
        choice = input("  > ").strip().lower()

        if choice in ("y", "yes", ""):
            return message
        elif choice in ("c", "cancel"):
            return None
        elif choice in ("e", "edit"):
            print(f"  {DIM}What to change:{RESET}")
            edits = input("  > ").strip()
            if not edits:
                continue
            if llm:
                prompt = (
                    "You are a message editor. Here is the original message:\n\n"
                    f"{message}\n\n"
                    f"The user wants these changes: {edits}\n\n"
                    "Write ONLY the updated message. No explanation."
                )
                result = llm.invoke(prompt)
                content = result.content if hasattr(result, "content") else str(result)
                message = content.replace("<think>", "").replace("</think>", "").strip()
            else:
                message = edits
            print(f"\n  {BOLD}Updated:{RESET}")
            for line in message.split("\n"):
                print(f"    {line}")
            print(f"\n  {DIM}[Y] Send  [E] Edit again  [C] Cancel{RESET}")
        else:
            print(f"  {DIM}Enter Y, E, or C{RESET}")


def _needs_llm_compose(user_input):
    """Check if the user wants the LLM to compose/write the message."""
    keywords = ["write", "compose", "draft", "create", "generate", "professional", "formal", "word"]
    user_lower = user_input.lower()
    return any(k in user_lower for k in keywords)


def _llm_compose_message(llm, user_input):
    """Use the LLM to compose a message based on the user's intent."""
    prompt = (
        "You are a message writer. Based on the user's request, write ONLY the message content. "
        "Do not include any explanation, prefix, or formatting. Just the message itself.\n\n"
        f"User request: {user_input}"
    )
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.replace("<think>", "").replace("</think>", "").strip()
    return content


def slack_agent(state, llm, tools):
    """Agent specialized for Slack operations."""
    user_input = state.get("input", " ")
    user_input_lower = user_input.lower()

    if "list" in user_input_lower or "channels" in user_input_lower:
        return _handle_slack_list_channels(state, tools)
    elif "read" in user_input_lower or "get" in user_input_lower or "check" in user_input_lower:
        return _handle_slack_read(state, tools, user_input)
    else:
        return _handle_slack_send(state, tools, user_input, llm)


def _handle_slack_list_channels(state, tools):
    """Handle listing Slack channels."""
    channel_tool = None
    for tool in tools:
        if tool.name == "get_channelid_name_dict":
            channel_tool = tool
            break

    if not channel_tool:
        return {**state, "output": "Slack channel list tool not found"}

    channels = channel_tool.invoke({})
    if isinstance(channels, str):
        channels = ast.literal_eval(channels)

    lines = ["Slack Channels:"]
    lines.append("  " + "-" * 30)
    for ch in channels:
        name = ch.get("name", "unknown")
        members = ch.get("num_members", 0)
        lines.append(f"  # {name}  ({members} members)")
    lines.append("  " + "-" * 30)

    return {**state, "output": "\n".join(lines)}


def _handle_slack_send(state, tools, user_input, llm):
    """Handle sending a Slack message."""
    channel_match = re.search(r"#([\w-]+)", user_input)
    channel = channel_match.group(1) if channel_match else "general"

    if _needs_llm_compose(user_input):
        message = _llm_compose_message(llm, user_input)
    else:
        saying_match = re.search(r"saying\s+(.+)", user_input, re.IGNORECASE)
        message = saying_match.group(1).strip() if saying_match else user_input

    send_tool = None
    for tool in tools:
        if tool.name == "send_message":
            send_tool = tool
            break

    if not send_tool:
        return {**state, "output": "Slack send tool not found"}

    confirmed = _confirm_message(message, llm)
    if not confirmed:
        return {**state, "output": "Message cancelled."}

    send_tool.invoke({"message": confirmed, "channel": channel})
    return {**state, "output": f"Message sent to #{channel}:\n  \"{confirmed}\""}


def _handle_slack_read(state, tools, user_input):
    """Handle reading Slack messages."""
    channel_match = re.search(r"#([\w-]+)", user_input)
    channel_name = channel_match.group(1) if channel_match else "general"

    channel_tool = None
    read_tool = None
    for tool in tools:
        if tool.name == "get_channelid_name_dict":
            channel_tool = tool
        elif tool.name == "get_messages":
            read_tool = tool

    if not read_tool or not channel_tool:
        return {**state, "output": "Slack read tools not found"}

    channels = channel_tool.invoke({})
    channel_id = None
    if isinstance(channels, str):
        channels = ast.literal_eval(channels)
    for ch in channels:
        if ch.get("name") == channel_name:
            channel_id = ch["id"]
            break

    if not channel_id:
        return {**state, "output": f"Channel #{channel_name} not found"}

    tool_result = read_tool.invoke({"channel_id": channel_id})

    messages = tool_result
    if isinstance(messages, str):
        messages = ast.literal_eval(messages)

    if not messages:
        return {**state, "output": f"No messages in #{channel_name}"}

    lines = [f"Messages from #{channel_name}:"]
    lines.append("  " + "-" * 40)
    for msg in reversed(messages):
        ts = float(msg.get("ts", 0))
        time_str = datetime.fromtimestamp(ts).strftime("%I:%M %p")
        text = msg.get("text", "")
        if text.startswith("<@") and "has joined" in text:
            continue
        lines.append(f"  [{time_str}]  {text}")
    lines.append("  " + "-" * 40)

    return {**state, "output": "\n".join(lines)}


class Email_work:
    def email_agent(state, llm, tools):
        """Agent specialized for email operations.
        Supports both sending and reading emails based on user intent.
        """
        user_input = state.get("input", " ")
        user_input_lower = user_input.lower()
        prompt = f"You are decider based on the user input wether the intent is to send_message or read_message{user_input_lower}"
        result = llm.invoke(prompt)
        result = result.content if hasattr(result, "content") else str(result)
        result = result.replace("<think>", "").replace("</think>", "").strip()

        if result == "read_message":
            return Email_work._handle_read_email(state, tools, user_input)
        else:
            return Email_work._handle_send_email(state, tools, user_input, llm)

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

    def _handle_send_email(state, tools, user_input, llm=None):
        """Handle sending emails."""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", user_input)
        to_email = email_match.group(0) if email_match else ""

        if llm and _needs_llm_compose(user_input):
            body = _llm_compose_message(llm, user_input)
        else:
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

        send_tool = None
        for tool in tools:
            if tool.name == "send_gmail_message":
                send_tool = tool
                break

        if not send_tool:
            return {**state, "output": "Send email tool not found"}

        if not to_email:
            return {**state, "output": "Could not find recipient email address"}

        print(f"\n  To: {to_email}")
        print(f"  Subject: {subject}")
        confirmed = _confirm_message(body, llm)
        if not confirmed:
            return {**state, "output": "Email cancelled."}

        send_tool.invoke(
            {
                "to": to_email,
                "subject": subject,
                "message": confirmed,
            }
        )

        return {**state, "output": f"Email sent to {to_email}: \"{subject}\""}


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
