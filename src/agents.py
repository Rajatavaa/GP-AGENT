import ast
import re
from datetime import datetime
from langchain_core.messages import HumanMessage
from rich.markdown import Markdown

from .utils import _confirm_message, _extract_sender_name, _strip_think_tags, _generate_subject
from .display import (
    console,
    create_channel_table,
    create_slack_messages_table,
    create_sent_panel,
)


def start_agent(llm, tools):
    if not tools:
        return llm

    return llm.bind_tools(tools)


def general_agent_node(state, agent):
    user_input = state.get("input", "")

    result = agent.invoke(
        [
            HumanMessage(
                content=f"You are a helpful assistant. Handle this:\n{user_input}"
            )
        ]
    )

    output = result.content if hasattr(result, "content") else str(result)
    output = _strip_think_tags(output)
    return {**state, "output": Markdown(output)}


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

        return {**state, "output": create_channel_table(channels)}

    def handle_slack_send(state, tools, llm):
        channel_match = re.search(r"#([\w-]+)", state.get("input", ""))
        channel = channel_match.group(1) if channel_match else "general"

        composed = state.get("composed_message")
        if composed:
            message = composed
        else:
            saying_match = re.search(
                r"saying\s+(.+?)(?:\s+in\s+\d+\s+words?)?\s*$",
                state.get("input", ""), re.IGNORECASE,
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
        return {
            **state,
            "output": create_sent_panel(
                f"Message sent to #{channel}",
                confirmed,
            ),
        }

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

        display_messages = []
        for msg in reversed(messages):
            text = msg.get("text", "")
            if text.startswith("<@") and "has joined" in text:
                continue
            ts = float(msg.get("ts", 0))
            time_str = datetime.fromtimestamp(ts).strftime("%I:%M %p")
            display_messages.append({"_time_str": time_str, "text": text})

        return {
            **state,
            "output": create_slack_messages_table(channel_name, display_messages),
        }


class Email_work:
    def handle_email_send(state, tools, llm):
        user_input = state.get("input", "")
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", user_input)
        to_email = email_match.group(0) if email_match else ""
        composed = state.get("composed_message")
        if composed:
            body = composed
        else:
            # Extract message after "saying", but strip trailing instructions like "in 50 words"
            saying_match = re.search(
                r"saying\s+(.+?)(?:\s+in\s+\d+\s+words?)?\s*$",
                user_input, re.IGNORECASE,
            )
            body = (
                saying_match.group(1).strip()
                if saying_match
                else user_input
            )

        subject_match = re.search(
            r"(?:about|regarding)\s+(.+?)(?:\s+saying|\s*$)",
            user_input,
            re.IGNORECASE,
        )
        if subject_match:
            subject = subject_match.group(1).strip()
        else:
            subject = _generate_subject(body, llm)

        send_tool = None
        for tool in tools:
            if tool.name == "send_gmail_message":
                send_tool = tool
                break

        if not send_tool:
            return {**state, "output": "Send email tool not found"}
        if not to_email:
            return {**state, "output": "Could not find recipient email address"}

        console.print(f"\n  [bold]To:[/bold] {to_email}")
        console.print(f"  [bold]Subject:[/bold] {subject}")
        confirmed = _confirm_message(body, llm)
        if not confirmed:
            return {**state, "output": "Email cancelled."}

        if confirmed != body and not subject_match:
            subject = _generate_subject(confirmed, llm)

        extracted_name = _extract_sender_name(confirmed)
        if extracted_name:
            confirmed = re.sub(
                rf"(?:Best|Regards|Sincerely|Thanks),\s*\n?.*{re.escape(extracted_name)}",
                "",
                confirmed,
                flags=re.IGNORECASE | re.DOTALL,
            ).strip()

        send_tool.invoke({"to": to_email, "subject": subject, "message": confirmed})
        return {
            **state,
            "output": create_sent_panel(
                "Email Sent",
                f"To: {to_email}\nSubject: {subject}\n\n{confirmed}",
            ),
        }

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
