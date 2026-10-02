"""Tout ce qui s'affiche dans le terminal : bannière, étapes, panneaux."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console(highlight=False)

ACCENT = "#7C9CFF"
WARM = "#FFB86B"
OK = "#5AD19A"
MUTED = "grey58"

LOGO = r"""
     ██╗ ██████╗ ██████╗ ██╗   ██╗
     ██║██╔═══██╗██╔══██╗╚██╗ ██╔╝
     ██║██║   ██║██████╔╝ ╚████╔╝
██   ██║██║   ██║██╔══██╗  ╚██╔╝
╚█████╔╝╚██████╔╝██████╔╝   ██║
 ╚════╝  ╚═════╝ ╚═════╝    ╚═╝
"""

GRADIENT = ["#7C9CFF", "#8E98FA", "#A094F4", "#B290EC", "#C48CE2", "#D688D6"]


def logo() -> Text:
    text = Text()
    for line, color in zip(LOGO.strip("\n").splitlines(), GRADIENT):
        text.append(line + "\n", style=f"bold {color}")
    return text


def banner(subtitle: str = "Ton agent de recherche d'emploi. Peu de candidatures, toutes irréprochables.") -> None:
    console.print()
    console.print(Align.center(logo()))
    console.print(Align.center(Text(subtitle, style=f"italic {MUTED}")))
    console.print()


def step_board(steps: list[tuple[str, str]], done: set[str], current: str | None = None) -> Panel:
    """Le tableau des étapes de l'onboarding avec une barre de progression."""
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", width=3)
    table.add_column()
    for i, (key, title) in enumerate(steps, 1):
        if key in done:
            mark, style = "✔", OK
        elif key == current:
            mark, style = "➜", f"bold {WARM}"
        else:
            mark, style = "○", MUTED
        table.add_row(Text(mark, style=style), Text(f"{i}. {title}", style=style if key != current else f"bold {WARM}"))

    n, total = len(done & {k for k, _ in steps}), len(steps)
    width = 30
    filled = round(width * n / total) if total else 0
    bar = Text("█" * filled, style=ACCENT) + Text("░" * (width - filled), style=MUTED)
    bar.append(f"  {n}/{total}", style=MUTED)
    return Panel(Group(table, Text(""), bar), title="[bold]Ta configuration[/]", border_style=ACCENT,
                 padding=(1, 3), expand=False)


def say(message: str, style: str = "") -> None:
    console.print(message, style=style)


def info(message: str) -> None:
    console.print(f"[{ACCENT}]›[/] {message}")


def success(message: str) -> None:
    console.print(f"[{OK}]✔[/] {message}")


def warn(message: str) -> None:
    console.print(f"[{WARM}]![/] {message}")


def error(message: str) -> None:
    console.print(f"[bold red]✖[/] {message}")


def section(title: str) -> None:
    console.print()
    console.print(Rule(Text(title, style=f"bold {ACCENT}"), style=MUTED))
    console.print()


def card(body, title: str = "", style: str = ACCENT) -> None:
    console.print(Panel(body, title=f"[bold]{title}[/]" if title else None, border_style=style,
                        padding=(1, 2), expand=False))
