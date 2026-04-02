import os
import sys
from dotenv import load_dotenv
from requests.exceptions import ConnectionError as ReqConnectionError
from langchain_openai import ChatOpenAI

from src.graphs import build_graph
from src.agents import start_agent

load_dotenv()

DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

HELP_TEXT = f"""
  {BOLD}Slack{RESET}
    send a slack message to #channel saying ...
    write a 50 word slack message to #channel about ...
    read slack messages from #channel
    list my slack channels

  {BOLD}Email{RESET}
    send an email to user@email.com saying ...
    write a formal email to user@email.com about ...
    read my emails from user@email.com

  {BOLD}Other{RESET}
    help    Show this menu
    quit    Exit
"""


def start():
    print(f"\n  {DIM}Connecting to LLM...{RESET}", end=" ", flush=True)
    try:
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        model = os.getenv("LLM_MODEL", "qwen2.5:3b")
        llm = ChatOpenAI(base_url=base_url, api_key="sk-no-key-needed", model=model)
        llm.invoke("hi")
        print(f"{DIM}done{RESET}")
    except (ReqConnectionError, ConnectionError):
        print(f"\n\n  Error: Cannot connect to LLM server at {base_url}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n  Error: {e}\n")
        sys.exit(1)

    general_agent = start_agent(llm, [])
    graph = build_graph(general_agent, llm).compile()

    print(f"\n  {BOLD}GP-Agent{RESET} {DIM}v1.0{RESET}")
    print(f"  {DIM}Type 'help' for commands, 'quit' to exit{RESET}\n")

    while True:
        try:
            user_input = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print()
            break

        if user_input.lower() in ("help", "h", "?"):
            print(HELP_TEXT)
            continue

        try:
            result = graph.invoke({"input": user_input})
            output = result["output"]
            for line in output.split("\n"):
                print(f"  {line}")
            print()
        except (ReqConnectionError, ConnectionError):
            print("  Error: Lost connection to LLM server.\n")
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid_auth" in error_msg or "token" in error_msg:
                print("  Error: Slack token invalid. Check .env file.\n")
            elif "connection" in error_msg or "refused" in error_msg:
                print("  Error: Connection failed. Check internet/Ollama.\n")
            elif "credential" in error_msg or "gmail" in error_msg:
                print("  Error: Gmail credentials issue. Check credentials.json.\n")
            else:
                print(f"  Error: {e}\n")


if __name__ == "__main__":
    start()
