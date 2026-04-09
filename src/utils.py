import re

from prompt_toolkit import prompt as pt_prompt

from .display import console


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
                message = content.replace("\u201c", "").replace("\u201d", "").strip()
            else:
                message = edits
            console.print("\n  [bold]Updated:[/bold]")
            for line in message.split("\n"):
                console.print(f"    {line}")
            console.print("\n  [dim][Y] Send  [E] Edit again  [C] Cancel[/dim]")
        else:
            console.print("  [dim]Enter Y, E, or C[/dim]")


def _needs_llm_compose(user_input):
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
    user_input = state.get("input", "")
    prompt = (
        "You are a message writer. Based on the user's request, write ONLY the message content."
        "Do not include any explanation, prefix, reasoning, or formatting. Just the message itself.\n\n"
        "Please do not include the subject in the email body"
        f"User request: {user_input}"
    )
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = re.sub(r"\u201c.*?\u201d", "", content, flags=re.DOTALL)
    content = content.replace("\u201c", "").replace("\u201d", "").strip()
    return {**state, "composed_message": content}


def _extract_name_from_email(email):
    if not email:
        return None
    name_part = email.split("@")[0]
    name_part = name_part.replace(".", " ").replace("_", " ")
    return name_part.strip()


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
