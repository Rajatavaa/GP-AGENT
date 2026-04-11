import re


def _has_compose_signals(text):
    """Detect if input has signals that the user wants the LLM to compose/write the message."""
    lower = text.lower()
    # Word count requests like "in 50 words", "in 100 words"
    if re.search(r"in\s+\d+\s+word", lower):
        return True
    # Style/tone requests
    compose_keywords = [
        "write", "compose", "draft", "generate", "create",
        "make it fun", "make it professional", "make it formal",
        "make it friendly", "make it short", "make it brief",
        "on your own", "add a line", "add something",
        "professional tone", "formal tone", "casual tone",
    ]
    return any(k in lower for k in compose_keywords)


def _mentions_email_or_slack(text):
    """Check if input mentions email or slack as a target."""
    lower = text.lower()
    if "email" in lower or "mail" in lower or "slack" in lower:
        return True
    if re.search(r"#[\w-]+", text):  # slack channel like #general
        return True
    if re.search(r"[\w\.-]+@[\w\.-]+", text):  # email address
        return True
    return False


def router(state, llm):
    from .display import console
    from .utils import _strip_think_tags

    user_input = state["input"]

    # Fast pre-check: if input has compose signals + mentions email/slack, skip LLM
    if _has_compose_signals(user_input) and _mentions_email_or_slack(user_input):
        return "llm_compose"

    # Fast pre-check: "write" without email/slack context = general chat
    if user_input.lower().startswith("write") and not _mentions_email_or_slack(user_input):
        return "general_chat"

    prompt = f"""You are a routing assistant. Based on the user input, determine which agent and action to use.

Available routes:
- llm_compose: when user wants the LLM to compose/write a message to SEND via email or slack (must mention email or slack)
- slack_list_channels: when user wants to see/list Slack channels
- slack_send_message: when user wants to send a message to Slack (with their own exact words)
- slack_read_messages: when user wants to read/check messages in a Slack channel
- email_send_email: when user wants to send an email (with their own exact words)
- email_read_email: when user wants to read/search emails
- general_chat: for ANY general conversation, questions, or writing requests that are NOT about sending emails or slack messages

User input: {user_input}

Respond with ONLY the route name. Examples:
- "write a fun email to bob@example.com about the meeting" -> llm_compose
- "compose a professional slack message to #general about the update" -> llm_compose
- "send an email saying hello, make it fun" -> llm_compose
- "write a 50 word email to bob@example.com" -> llm_compose
- "send email to bob@example.com saying hello in 50 words" -> llm_compose
- "send email to bob@example.com about X in 100 words" -> llm_compose
- "send a message to #general on slack saying hello" -> slack_send_message
- "list slack channels" -> slack_list_channels
- "send email to bob@example.com saying hello" -> email_send_email
- "read emails from bob@example.com" -> email_read_email
- "what is 2+2" -> general_chat
- "write a poem" -> general_chat
- "write me something in 50 words" -> general_chat
- "explain python decorators" -> general_chat
- "hello" -> general_chat

IMPORTANT:
- llm_compose is ONLY for composing messages to send via email or slack. The input MUST mention email, slack, or a channel/email address.
- If the user says "write" but does NOT mention email/slack/channel/email-address, use general_chat.
- If the user mentions a word count like "in 50 words", "in 100 words", or says "make it professional", "make it fun", "formal", etc — use llm_compose (the user wants the LLM to compose the message, not send their raw text).
- When in doubt, use general_chat.

Route:"""

    try:
        result = llm.invoke(prompt)
        content = result.content if hasattr(result, "content") else str(result)
        content = _strip_think_tags(content).lower()

        valid_routes = [
            "llm_compose",
            "slack_list_channels",
            "slack_send_message",
            "slack_read_messages",
            "email_send_email",
            "email_read_email",
            "general_chat",
        ]

        for route in valid_routes:
            if route in content:
                return route

        return "general_chat"
    except Exception as e:
        console.print(f"  [dim]Router error: {e}, defaulting to general_chat[/dim]")
        return "general_chat"


def should_compose(state, llm):
    """After LLM compose, determine where to route next (email or slack)."""
    from .utils import _strip_think_tags

    user_input = state["input"].lower()

    if "email" in user_input or "mail" in user_input:
        return "email"
    elif "slack" in user_input or "#" in user_input:
        return "slack"

    prompt = f"Is this about sending an email or a slack message? Input: {user_input}. Respond with just 'email', 'slack', or 'neither'."
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = _strip_think_tags(content).lower()

    if "email" in content or "mail" in content:
        return "email"
    elif "slack" in content:
        return "slack"
    return "general"
