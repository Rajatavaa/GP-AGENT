import ast
import re
from datetime import datetime
from langchain_core.messages import HumanMessage


DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def start_agent(llm, tools):
    """Creates an agent with the given LLM and tools.
    If no tools, returns a plain chat agent.
    """
    if not tools:
        return llm

    return llm.bind_tools(tools)


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
    keywords = [
        "write",
        "compose",
        "draft",
        "create",
        "generate",
        "professional",
        "formal",
        "word",
        "on your own",
        "add a line",
        "make it",
    ]
    user_lower = user_input.lower()
    return any(k in user_lower for k in keywords)


def _llm_compose_message(state, llm):
    """Use the LLM to compose a message based on the user's intent."""
    user_input = state.get("input", "")
    prompt = (
        "You are a message writer. Based on the user's request, write ONLY the message content."
        "Do not include any explanation, prefix, reasoning, or formatting. Just the message itself.\n\n"
        "Please do not include the subject in the email body"
        f"User request: {user_input}"
    )
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    content = content.replace("<think>", "").replace("</think>", "").strip()
    return {**state, "composed_message": content}


def _extract_name_from_email(email):
    """Extract name part from email address (e.g., rajatava from rajatava@aivctalent.com)."""
    if not email:
        return None
    name_part = email.split("@")[0]
    name_part = name_part.replace(".", " ").replace("_", " ")
    return name_part.strip()


def _extract_sender_name(body):
    """Extract sender name from email signature."""
    patterns = [
        r"(?:Best|Regards|Sincerely|Thanks),\s*\n?(.+?)(?:\n|$)",
        r"(?:Best|Regards|Sincerely|Thanks),\s*\n?\[\s*Your\s+Name\s*\]",
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        if match:
            name = match.group(1).strip()
            if name and name != "Your Name":
                return name

    return None


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


class Slack_work:
    def handle_slack_list_channels(state, tools):
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

    def handle_slack_send(state, tools, llm):
        channel_match = re.search(r"#([\w-]+)", state.get("input", ""))
        channel = channel_match.group(1) if channel_match else "general"

        composed = state.get("composed_message")
        if composed:
            message = composed
        else:
            saying_match = re.search(
                r"saying\s+(.+)", state.get("input", ""), re.IGNORECASE
            )
            message = (
                saying_match.group(1).strip()
                if saying_match
                else state.get("input", "")
            )

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
        return {**state, "output": f'Message sent to #{channel}:\n  "{confirmed}"'}

    def handle_slack_read(state, tools):
        channel_match = re.search(r"#([\w-]+)", state.get("input", ""))
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
    def handle_email_send(state, tools, llm):
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", state.get("input", ""))
        to_email = email_match.group(0) if email_match else ""

        composed = state.get("composed_message")
        if composed:
            body = composed
        else:
            saying_match = re.search(
                r"saying\s+(.+)", state.get("input", ""), re.IGNORECASE
            )
            body = (
                saying_match.group(1).strip()
                if saying_match
                else state.get("input", "")
            )

        subject_match = re.search(
            r"(?:about|regarding)\s+(.+?)(?:\s+saying|\s*$)",
            state.get("input", ""),
            re.IGNORECASE,
        )
        subject = (
            subject_match.group(1).strip()
            if subject_match
            else " ".join(body.split()[:6])
            if body
            else "Email"
        )

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

        extracted_name = _extract_sender_name(confirmed)
        if extracted_name:
            confirmed = re.sub(
                rf"(?:Best|Regards|Sincerely|Thanks),\s*\n?.*{re.escape(extracted_name)}",
                "",
                confirmed,
                flags=re.IGNORECASE | re.DOTALL,
            ).strip()

        send_tool.invoke({"to": to_email, "subject": subject, "message": confirmed})
        return {**state, "output": f'Email sent to {to_email}: "{subject}"'}

    def handle_email_read(state, tools):
        read_tool = None
        search_tool = None
        for tool in tools:
            if tool.name == "get_gmail_message":
                read_tool = tool
            elif tool.name == "gmail_search":
                search_tool = tool

        if not read_tool and not search_tool:
            return {**state, "output": "No email read/search tool available"}

        query = state.get("input", "")
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", query)
        if email_match:
            query = f"from:{email_match.group(0)} OR to:{email_match.group(0)}"

        tool_result = (search_tool or read_tool).invoke({"query": query})
        return {**state, "output": f"Email search result: {tool_result}"}
