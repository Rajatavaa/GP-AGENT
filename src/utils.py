import re

from prompt_toolkit import prompt as pt_prompt

from .display import console


def _strip_think_tags(text):
    """Remove <think>...</think> blocks (including content) from LLM output."""
    # Remove closed think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove unclosed think blocks (LLM output cut off or missing closing tag)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def _confirm_message(message, llm=None):
    console.print("\n  [bold]Preview:[/bold]")
    for line in message.split("\n"):
        console.print(f"    {line}")
    console.print("\n  [dim][Y] Send  [E] Edit  [C] Cancel[/dim]")

    while True:
        choice = pt_prompt("  > ").strip().lower()

        if choice in ("y", "yes", ""):
            return message
        elif choice in ("c", "cancel"):
            return None
        elif choice in ("e", "edit"):
            console.print("  [dim]What to change:[/dim]")
            edits = pt_prompt("  > ").strip()
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
                content = _strip_think_tags(content)
                message = content.replace("\u201c", '"').replace("\u201d", '"').strip()
            else:
                message = edits
            console.print("\n  [bold]Updated:[/bold]")
            for line in message.split("\n"):
                console.print(f"    {line}")
            console.print("\n  [dim][Y] Send  [E] Edit again  [C] Cancel[/dim]")
        else:
            console.print("  [dim]Enter Y, E, or C[/dim]")


def _llm_compose_message(state, llm):
    from .config import get_sender_name
    import re as _re

    user_input = state.get("input", "")
    receiver_name = state.get("receiver_name", "")
    sender_name = get_sender_name()

    is_email = bool(_re.search(r"email|mail|@", user_input.lower()))

    if is_email and not receiver_name:
        console.print("\n  [bold]Who is this email to?[/bold] (recipient's name)")
        try:
            receiver_name = pt_prompt("  Name > ").strip()
        except (KeyboardInterrupt, EOFError):
            receiver_name = ""

    name_instruction = ""
    if is_email:
        if receiver_name:
            name_instruction += f"\n- Address the recipient by name: {receiver_name}. Start with a salutation like 'Hi {receiver_name},' or 'Dear {receiver_name},'"
        if sender_name:
            name_instruction += f"\n- Sign off with your name: {sender_name}. End with something like 'Best, {sender_name}' or 'Regards, {sender_name}'"
    else:
        name_instruction += "\n- Do NOT include any salutation (no 'Hi Name,') or sign-off (no 'Thanks', 'Best', 'Regards', etc.). Write ONLY the core message."

    prompt = (
        "You are a message writer. Write ONLY the message body.\n\n"
        "RULES:\n"
        "- Do NOT include a subject line (no 'Subject:' prefix)\n"
        "- Do NOT repeat the user's instructions in the message\n"
        "- If the user says 'in X words', that means write the message using approximately X words. "
        "Do NOT mention the word count in the message itself.\n"
        "- Output ONLY the message body text, nothing else.\n"
        f"{name_instruction}\n\n"
        f"User request: {user_input}"
    )
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = _strip_think_tags(content)
    content = re.sub(r"^Subject:.*\n*", "", content, flags=re.IGNORECASE).strip()
    content = content.replace("\u201c", '"').replace("\u201d", '"').strip()
    return {**state, "composed_message": content, "receiver_name": receiver_name}


def _generate_subject(body, llm):
    """Use the LLM to generate a short email subject from the body."""
    prompt = (
        "Write a short email subject line (max 6 words) for this email body. "
        "Output ONLY the subject line, nothing else. No quotes, no 'Subject:' prefix.\n\n"
        f"Email body: {body}"
    )
    try:
        result = llm.invoke(prompt)
        content = result.content if hasattr(result, "content") else str(result)
        content = _strip_think_tags(content)
        content = re.sub(r"^Subject:\s*", "", content, flags=re.IGNORECASE).strip()
        content = content.strip("\"'")
        if content:
            return content
    except Exception:
        pass
    return "Email"


def email_structure(body):
    """Insert proper newlines around salutation, closing, and from lines."""
    body = re.sub(r"((?:Hi|Hello|Dear|Hey)\s+[^,.!?\n]+[,.])\s*", r"\1\n\n", body)
    body = re.sub(
        r"\s*\n?\s*((?:Best|Regards|Sincerely|Thanks|Warm regards|Cheers)\s*,)",
        r"\n\n\1",
        body,
    )
    body = re.sub(
        r"((?:Best|Regards|Sincerely|Thanks|Warm regards|Cheers),)\s+([A-Z][\w\s]*?)\s*$",
        r"\1\n\2",
        body,
        flags=re.MULTILINE,
    )
    body = re.sub(r"\s*\n?(From:)", r"\n\n\1", body)
    return body
