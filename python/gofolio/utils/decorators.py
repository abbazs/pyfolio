"""CLI decorators and context managers for gofolio."""

import functools
import traceback
from collections.abc import Callable
from types import TracebackType
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from gofolio.utils.console import console as _default_console


class cli_progress:
    """Context manager that displays a Rich spinner/progress bar during a long operation."""

    def __init__(self, description: str, console: Console | None = None) -> None:
        self.description = description
        self._console = console or _default_console

    def __enter__(self) -> "cli_progress":
        """Start the progress display."""
        self._progress = Progress(
            SpinnerColumn(finished_text="✅"),
            TextColumn(f"[progress.description]{self.description}"),
            BarColumn(bar_width=40),
            TimeElapsedColumn(),
            transient=False,
            console=self._console,
        )
        self._task = self._progress.add_task(self.description, total=None)
        self._progress.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Stop the progress display, marking complete if no exception occurred."""
        if exc_type is None:
            self._progress.update(self._task, completed=1, total=1)
        self._progress.stop()
        return False


def handle_cli_errors[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that catches common exceptions and displays Rich error panels instead of tracebacks."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            from gofolio.utils.rp import rp

            rp.warning("Operation cancelled.")
        except ValueError as e:
            from gofolio.utils.console import console

            console.print(
                Panel(
                    f"[red]{e}[/red]",
                    title="[bold red]Validation Error[/bold red]",
                    border_style="red",
                )
            )
        except FileNotFoundError as e:
            from gofolio.utils.console import console

            console.print(
                Panel(
                    f"[red]{e}[/red]",
                    title="[bold red]File Not Found[/bold red]",
                    border_style="red",
                )
            )
        except Exception as e:
            from gofolio.utils.console import console

            error_panel = Panel(
                f"[red]{traceback.format_exc()}[/red]",
                title=f"[bold red]Error: {type(e).__name__}[/bold red]",
                border_style="red",
            )
            console.print(error_panel)

    return wrapper
