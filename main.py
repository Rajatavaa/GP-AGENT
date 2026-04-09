import os
import sys
import time

from dotenv import load_dotenv
from requests.exceptions import ConnectionError as ReqConnectionError
from langchain_openai import ChatOpenAI
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter

from src.graphs import build_graph
from src.agents import start_agent
from src.display import console, show_banner, show_help, show_session_info

load_dotenv()

COMMANDS = [
    "/help",
    "/quit",
    "/exit",
    "/info",
    "/clear",
    "send",
    "read",
    "list",
    "write",
]
COMPLETER = WordCompleter(COMMANDS, ignore_case=True, sentence=True)


def start():
    console.print("  [dim]Connecting to LLM...[/]", end=" ")
    try:
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
        model = os.getenv("LLM_MODEL", "qwen2.5:3b")
        llm = ChatOpenAI(base_url=base_url, api_key="sk-no-key-needed", model=model)
        llm.invoke("hi")
        console.print("[dim]done[/]")
    except (ReqConnectionError, ConnectionError):
        console.print(
            f"\n\n  [bold red]Error:[/bold red] Cannot connect to LLM server at {base_url}\n"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"\n\n  [bold red]Error:[/bold red] {e}\n")
        sys.exit(1)

    general_agent = start_agent(llm, [])
    graph = build_graph(general_agent, llm).compile()

    show_banner(model)

    history_file = os.path.expanduser("~/.gp_agent_history")
    session = PromptSession(
        history=FileHistory(history_file),
        completer=COMPLETER,
    )

    start_time = time.time()

    while True:
        try:
            first_line = session.prompt("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n  [dim]Bye![/]\n")
            break

        if not first_line:
            continue

        user_input = first_line
        while user_input.endswith("\\"):
            user_input = user_input[:-1]
            try:
                continuation = session.prompt("  ... ").strip()
            except (KeyboardInterrupt, EOFError):
                user_input = user_input.strip()
                break
            if not continuation:
                break
            user_input += " " + continuation

        user_input = user_input.strip()
        if not user_input:
            continue

        cmd = user_input.lower().lstrip("/")

        if cmd in ("quit", "exit", "q"):
            console.print("\n  [dim]Bye![/]\n")
            break

        if cmd in ("help", "h", "?"):
            show_help()
            continue

        if cmd == "info":
            show_session_info(model, start_time)
            continue

        if cmd == "clear":
            console.clear()
            continue

        try:
            console.print("  [dim]Thinking...[/]")
            result = graph.invoke({"input": user_input})
            output = result["output"]
            sys.stdout.write("\033[1A\033[2K")
            sys.stdout.flush()
            console.print(output)
            console.print()
        except (ReqConnectionError, ConnectionError):
            console.print(
                "  [bold red]Error:[/bold red] Lost connection to LLM server.\n"
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid_auth" in error_msg or "token" in error_msg:
                console.print(
                    "  [bold red]Error:[/bold red] Slack token invalid. Check .env file.\n"
                )
            elif "connection" in error_msg or "refused" in error_msg:
                console.print(
                    "  [bold red]Error:[/bold red] Connection failed. Check internet/Ollama.\n"
                )
            elif "credential" in error_msg or "gmail" in error_msg:
                console.print(
                    "  [bold red]Error:[/bold red] Gmail credentials issue. Check credentials.json.\n"
                )
            else:
                console.print(f"  [bold red]Error:[/bold red] {e}\n")


if __name__ == "__main__":
    start()
