import re

DIM = "[2m"
BOLD = "[1m"
RESET = "[0m"


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
                message = content.replace("“", "").replace("”", "").strip()
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
    content = re.sub(r"“.*?”", "", content, flags=re.DOTALL)
    content = content.replace("“", "").replace("”", "").strip()
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
