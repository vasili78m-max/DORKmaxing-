import os
import sys
import asyncio
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from pathlib import Path load_dotenv(Path(__file__).parent / ".env") ```  This forces it to look for `.env` in the same folder as `main.py` regardless of where you run the script from.  Make that change, save, then run: ``` python main.py run

app_cli = typer.Typer(
    name="dorkmax",
    help="DorkMaxing — Google dorking automation via Serper, DuckDuckGo & Bing",
    add_completion=False,
)


def _get_serper_key() -> str:
    key = os.environ.get("SERPER_API_KEY", "")
    if not key:
        typer.echo("[!] SERPER_API_KEY not set. Copy .env.example to .env and add your key.", err=True)
        typer.echo("    Get a free key at https://serper.dev", err=True)
        raise typer.Exit(1)
    return key


@app_cli.command()
def run(
    query: Optional[str] = typer.Argument(None, help="Dork query to search immediately on launch"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Use a built-in dork template"),
    target: Optional[str] = typer.Option(None, "--target", "-d", help="Target domain for template substitution"),
    export: Optional[str] = typer.Option(None, "--export", "-o", help="Export results to file (json/csv)"),
    no_tui: bool = typer.Option(False, "--no-tui", help="Run headless, print results to stdout"),
):
    """
    Launch DorkMaxing TUI or run a headless search.

    Examples:

      dorkmax                                         # open TUI

      dorkmax "site:example.com filetype:pdf"        # open TUI with pre-filled query

      dorkmax --template login-panels --target example.com

      dorkmax "inurl:admin" --no-tui --export out.json
    """
    serper_key = _get_serper_key()

    if no_tui:
        _run_headless(query, template, target, export, serper_key)
        return

    from app import DorkMaxApp
    tui = DorkMaxApp(serper_key=serper_key)

    if query:
        # pre-fill search bar on launch
        async def _prefill():
            await asyncio.sleep(0.3)
            try:
                from textual.widgets import Input
                inp = tui.query_one("#search-bar", Input)
                inp.value = query
            except Exception:
                pass
        tui.call_later(_prefill)

    tui.run()


@app_cli.command("templates")
def show_templates():
    """List all available dork templates."""
    from core.dork_builder import load_templates
    templates = load_templates()
    typer.echo("\nAvailable DorkMaxing templates:\n")
    for name, dorks in templates.items():
        typer.echo(f"  {name:<20} ({len(dorks)} dorks)")
    typer.echo("\nUsage: dorkmax --template <name> --target <domain>\n")


@app_cli.command("history")
def show_history():
    """Show recent scan history."""
    from output.history import load_history
    scans = load_history()
    if not scans:
        typer.echo("No scan history found.")
        return
    typer.echo("\nRecent scans:\n")
    for s in scans:
        typer.echo(f"  [{s['timestamp']}]  {s['query'][:60]:<60}  {s['result_count']} results")
    typer.echo()


@app_cli.command("quota")
def show_quota():
    """Show current Serper API quota."""
    from core.quota import get_quota
    remaining, limit = get_quota()
    typer.echo(f"\n  Serper quota: {remaining}/{limit} requests remaining\n")


def _run_headless(query, template, target, export_path, serper_key):
    from engines.serper import SerperEngine
    from engines.duckduckgo import DuckDuckGoEngine
    from engines.bing import BingEngine
    from core.dispatcher import dispatch
    from core.aggregator import aggregate
    from core.dork_builder import build_query
    from output.formatter import export_json, export_csv

    engines = [SerperEngine(serper_key), DuckDuckGoEngine(), BingEngine()]
    queries = []

    if template:
        queries = build_query(template, target)
    elif query:
        queries = [query]
    else:
        typer.echo("Provide a query or --template.", err=True)
        raise typer.Exit(1)

    async def _run():
        all_results = []
        for q in queries:
            typer.echo(f"Searching: {q}")
            responses = await dispatch(engines, q)
            results = aggregate(responses)
            all_results.extend(results)
            for resp in responses:
                status = f"  {resp.engine}: {len(resp.results)} results" if not resp.error else f"  {resp.engine}: ERROR - {resp.error}"
                typer.echo(status)

        typer.echo(f"\nTotal unique results: {len(all_results)}")
        for r in all_results:
            typer.echo(f"  [{r.source}] {r.url}")

        if export_path:
            if export_path.endswith(".csv"):
                export_csv(all_results, export_path)
            else:
                export_json(all_results, export_path)
            typer.echo(f"\nExported to: {export_path}")

    asyncio.run(_run())


if __name__ == "__main__":
    app_cli()
