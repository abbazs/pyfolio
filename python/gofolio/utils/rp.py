"""RichPrint helper for styled CLI output."""

from rich.console import Console


class RichPrint:
    """Provides styled terminal output methods using Rich markup."""

    def __init__(self, console: Console | None = None):
        self._console = console

    @property
    def console(self) -> Console:
        """Lazy-load the shared console singleton."""
        if self._console is None:
            from gofolio.utils.console import console

            self._console = console
        return self._console

    def success(self, message: str) -> None:
        """Print a green success message with a checkmark."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def error(self, message: str) -> None:
        """Print a red error message with a cross."""
        self.console.print(f"[bold red]✗[/bold red] {message}")

    def warning(self, message: str) -> None:
        """Print a yellow warning message with a warning sign."""
        self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")

    def info(self, message: str) -> None:
        """Print a blue informational message."""
        self.console.print(f"[bold blue]i[/bold blue] {message}")


rp = RichPrint()
