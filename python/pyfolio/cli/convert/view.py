"""View layer for the convert command — renders conversion results to the terminal."""

from rich.panel import Panel
from stepper import Stepper, StepperTheme, StepStatus

from pyfolio.cli.convert.models import ConvertResult
from pyfolio.utils.console import console


def _human_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string (KB, MB, etc.)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def show_result(result: ConvertResult) -> None:
    """Display the conversion result using a Stepper and a summary panel."""
    theme = StepperTheme(
        show_elapsed_time=True,
        show_bar=True,
        bar_width=15,
        max_log_rows=2,
        log_prefix="›",
        completed_style="green bold",
        active_style="yellow bold",
        pending_style="bright_black",
        step_gap=0,
    )

    # Show conversion pipeline steps as a completed sequence.
    # Because the Rust conversion is synchronous, all steps are already done
    # by the time we reach this function; we replay them visually here.
    steps = [
        ("Read HTML", f"Loaded {result.input_path}"),
        ("Parse document", "DOM parsed by folio engine"),
        ("Render pages", f"Page size: {result.page_size.upper()}"),
        ("Write PDF", f"Saved to {result.output_path}"),
    ]

    with Stepper(console=console, theme=theme) as stepper:
        for label, log_msg in steps:
            step_idx = stepper.add_step(label, status=StepStatus.ACTIVE)
            stepper.log(step_idx, log_msg)
            stepper.set_step_progress(step_idx, 1.0)
            stepper.set_step_status(step_idx, StepStatus.COMPLETED)

    console.print()

    # Summary panel with key output details
    parts = [
        f"[bold]Input:[/bold]     {result.input_path}",
        f"[bold]Output:[/bold]    {result.output_path}",
        f"[bold]Page size:[/bold] {result.page_size.upper()}",
        f"[bold]File size:[/bold] {_human_size(result.output_size_bytes)}",
    ]

    console.print(
        Panel(
            "\n".join(parts),
            title="[bold green]Conversion Complete[/bold green]",
            border_style="green",
        )
    )
