"""Root CLI application for gofolio."""

import cyclopts

from gofolio.cli.convert import cli as convert_cli

app = cyclopts.App(
    name="gofolio",
    help="gofolio — HTML to PDF converter powered by folio.",
    version_flags=["--version", "-V"],
)

app.command(convert_cli)
