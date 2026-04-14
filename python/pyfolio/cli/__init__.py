"""Root CLI application for pyfolio."""

import cyclopts

from pyfolio.cli.convert import cli as convert_cli

app = cyclopts.App(
    name="pyfolio",
    help="pyfolio — HTML to PDF converter powered by folio.",
    version_flags=["--version", "-V"],
)

app.command(convert_cli)
