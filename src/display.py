import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

BANNER_ART = (
    "[bold cyan]   ██████╗ ██████╗ [/]\n"
    "[bold cyan]  ██╔════╝ ██╔══██╗[/]\n"
    "[bold cyan]  ██║      ██████╔╝[/]\n"
    "[bold cyan]  ██║  ███╗██╔═══╝ [/]\n"
    "[bold cyan]  ╚██████╔╝██║     [/]\n"
    "[bold cyan]   ╚═════╝ ╚═╝     [/]\n"
    "[bold white]      AGENT       [/]"
)


def show_banner(model, version="1.0"):
    content = Text.from_markup(
        f"{BANNER_ART}\n\n"
        f"  [dim]v{version}[/]  ·  [green]{model}[/]\n"
        f"  [dim]Type [bold]/help[/] for commands[/]"
    )
    console.print(Panel(content, border_style="cyan", padding=(0, 2)))
    console.print()


def show_help():
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column("Section", style="bold cyan")
    table.add_column("Usage", style="white")

    table.add_row("Slack", "")
    table.add_row("", "  send a slack message to [bold]#channel[/] saying ...")
    table.add_row("", "  write a 50 word slack message to [bold]#channel[/] about ...")
    table.add_row("", "  read slack messages from [bold]#channel[/]")
    table.add_row("", "  list my slack channels")
    table.add_row("", "")
    table.add_row("Email", "")
    table.add_row("", "  send an email to [bold]user@email.com[/] saying ...")
    table.add_row("", "  write a formal email to [bold]user@email.com[/] about ...")
    table.add_row("", "  read my emails from [bold]user@email.com[/]")
    table.add_row("", "")
    table.add_row("Commands", "")
    table.add_row("", "  [green]/help[/]     Show this menu")
    table.add_row("", "  [green]/quit[/]     Exit")
    table.add_row("", "  [green]/info[/]     Session info")
    table.add_row("", "  [green]/clear[/]    Clear screen")

    console.print(
        Panel(table, title="[bold]Help[/]", border_style="cyan", padding=(1, 2))
    )
    console.print()


def show_session_info(model, start_time):
    elapsed = int(time.time() - start_time)
    mins, secs = divmod(elapsed, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        uptime = f"{hrs}h {mins}m {secs}s"
    elif mins > 0:
        uptime = f"{mins}m {secs}s"
    else:
        uptime = f"{secs}s"

    content = Text.from_markup(
        f"  Model   [green]{model}[/]\n  Uptime  [dim]{uptime}[/]"
    )
    console.print(
        Panel(
            content, title="[bold]Session Info[/]", border_style="cyan", padding=(1, 2)
        )
    )
    console.print()


def create_channel_table(channels):
    table = Table(title="Slack Channels", show_lines=False, border_style="blue")
    table.add_column("#Channel", style="bold white")
    table.add_column("Members", justify="right", style="cyan")

    for ch in channels:
        name = ch.get("name", "unknown")
        members = ch.get("num_members", 0)
        table.add_row(f"#{name}", str(members))

    return table


def create_slack_messages_table(channel_name, messages):
    table = Table(
        title=f"Messages from #{channel_name}",
        show_lines=False,
        border_style="blue",
    )
    table.add_column("Time", style="cyan", width=10)
    table.add_column("Message", style="white")

    for msg in messages:
        ts = msg.get("_time_str", "")
        text = msg.get("text", "")
        table.add_row(ts, text)

    return table


def create_sent_panel(title, body_line):
    content = Text(body_line)
    return Panel(
        content, title=f"[bold green]{title}[/]", border_style="green", padding=(0, 2)
    )
