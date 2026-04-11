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
    user_input = state.get("input", "")
    prompt = (
        "You are a message writer. Write ONLY the message body.\n\n"
        "RULES:\n"
        "- Do NOT include a subject line (no 'Subject:' prefix)\n"
        "- Do NOT include a sign-off like 'Best, [Your Name]' or 'Regards, [Your Name]'\n"
        "- Do NOT repeat the user's instructions in the message\n"
        "- If the user says 'in X words', that means write the message using approximately X words. "
        "Do NOT mention the word count in the message itself.\n"
        "- Output ONLY the message body text, nothing else.\n\n"
        f"User request: {user_input}"
    )
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = _strip_think_tags(content)
    # Remove subject line if LLM still includes one
    content = re.sub(r"^Subject:.*\n*", "", content, flags=re.IGNORECASE).strip()
    # Remove [Your Name] placeholders and sign-offs with them
    content = re.sub(
        r"(?:Best|Regards|Sincerely|Thanks|Cheers),?\s*\n*\s*\[.*?\]",
        "", content, flags=re.IGNORECASE
    ).strip()
    # Replace smart quotes with regular quotes (don't delete content between them)
    content = content.replace("\u201c", '"').replace("\u201d", '"').strip()
    return {**state, "composed_message": content}


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
        content = content.strip('"\'')
        if content:
            return content
    except Exception:
        pass
    return "Email"


def _extract_sender_name(body):
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
