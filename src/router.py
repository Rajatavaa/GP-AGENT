def router(state, llm):
    from .display import console

    user_input = state["input"]

    prompt = f"""You are a routing assistant. Based on the user input, determine which agent and action to use.

Available routes:
- llm_compose: when user asks to write/compose/create a message with LLM's own words
- slack_list_channels: when user wants to see/list Slack channels
- slack_send_message: when user wants to send a message to Slack
- slack_read_messages: when user wants to read/check messages in a Slack channel
- email_send_email: when user wants to send an email (but not compose with LLM)
- email_read_email: when user wants to read/search emails
- general_chat: for general conversation or questions

User input: {user_input}

Respond with ONLY the route name (one of the options above). Examples:
- "write a fun email to bob@example.com saying we will meet this weekend" -> llm_compose
- "compose a message to #general on slack" -> llm_compose
- "send an email saying hello, also add a fun line on your own" -> llm_compose
- "write an email to bob saying X, make it more fun" -> llm_compose
- "send a message to #general on slack saying hello" -> slack_send_message
- "list slack channels" -> slack_list_channels
- "send email to bob@example.com saying hello" -> email_send_email
- "what is 2+2" -> general_chat

IMPORTANT: If the user asks to "add a line", "on your own", "make it fun", "compose", "write", "create", "generate" - use llm_compose even if they also say "send email".

Route:"""

    try:
        result = llm.invoke(prompt)
        content = result.content if hasattr(result, "content") else str(result)
        content = content.replace("<think>", "").replace("</think>", "").strip().lower()

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
    user_input = state["input"].lower()

    if "email" in user_input or "mail" in user_input:
        return "email"
    elif "slack" in user_input:
        return "slack"

    prompt = f"Is this about email or slack? Input: {user_input}. Respond with just 'email' or 'slack'."
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.lower().strip()

    if "email" in content or "mail" in content:
        return "email"
    return "slack"
