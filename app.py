import asyncio
import os
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Input,
    ListView,
    ListItem,
    Label,
    Static,
    Select,
    Button,
    RichLog,
)
from textual.reactive import reactive
from textual import work
from rich.text import Text
from rich.table import Table
from rich.console import Console

from engines.serper import SerperEngine
from engines.duckduckgo import DuckDuckGoEngine
from engines.bing import BingEngine
from engines.base import SearchResult, EngineResponse
from core.dispatcher import dispatch
from core.aggregator import aggregate
from core.dork_builder import list_templates, build_query
from core.quota import quota_display
from output.history import save_scan
from output.formatter import export_json, export_csv


BANNER = """
[bold cyan] ██████╗  ██████╗ ██████╗ ██╗  ██╗███╗   ███╗ █████╗ ██╗  ██╗
[bold cyan]██╔══██╗██╔═══██╗██╔══██╗██║ ██╔╝████╗ ████║██╔══██╗╚██╗██╔╝
[bold cyan]██║  ██║██║   ██║██████╔╝█████╔╝ ██╔████╔██║███████║ ╚███╔╝ 
[bold cyan]██║  ██║██║   ██║██╔══██╗██╔═██╗ ██║╚██╔╝██║██╔══██║ ██╔██╗ 
[bold cyan]██████╔╝╚██████╔╝██║  ██║██║  ██╗██║ ╚═╝ ██║██║  ██║██╔╝ ██╗
[bold cyan]╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
[dim]  google dorking automation  ·  serper + duckduckgo + bing
"""


class ResultItem(ListItem):
    def __init__(self, result: SearchResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        source_color = {"Serper": "green", "DuckDuckGo": "yellow", "Bing": "blue"}.get(self.result.source, "white")
        yield Label(
            Text.assemble(
                (f"[{self.result.source}] ", source_color),
                (self.result.title[:70], "bold white"),
            )
        )
        yield Label(Text(self.result.url[:90], style="cyan"))


class DorkMaxApp(App):
    CSS = """
    Screen {
        background: #0d0d0d;
    }

    #banner {
        color: cyan;
        padding: 0 2;
        height: auto;
    }

    #search-bar {
        height: 3;
        border: solid #333;
        background: #111;
        padding: 0 1;
    }

    #controls {
        height: 3;
        padding: 0 1;
        background: #0d0d0d;
    }

    #controls Select {
        width: 28;
        background: #111;
        border: solid #333;
    }

    #controls Button {
        background: #1a1a2e;
        border: solid #4444aa;
        color: #aaaaff;
        width: 14;
    }

    #controls Button:hover {
        background: #2a2a4e;
    }

    #controls Button.-active {
        background: #3a3a6e;
    }

    #main-split {
        height: 1fr;
    }

    #results-panel {
        width: 55%;
        border: solid #222;
        background: #0d0d0d;
    }

    #results-panel ListView {
        background: #0d0d0d;
        padding: 0;
    }

    #results-panel ListItem {
        padding: 1 1;
        border-bottom: solid #1a1a1a;
    }

    #results-panel ListItem:hover {
        background: #1a1a1a;
    }

    #results-panel ListItem.--highlight {
        background: #1a1a2e;
    }

    #preview-panel {
        width: 45%;
        border: solid #222;
        background: #0a0a0a;
        padding: 1 2;
    }

    #preview-title {
        color: bold white;
        margin-bottom: 1;
    }

    #preview-url {
        color: cyan;
        margin-bottom: 1;
    }

    #preview-source {
        margin-bottom: 1;
    }

    #preview-snippet {
        color: #aaaaaa;
        margin-bottom: 1;
    }

    #preview-actions {
        height: auto;
        margin-top: 1;
    }

    #log-panel {
        height: 7;
        border: solid #1a1a1a;
        background: #080808;
        padding: 0 1;
    }

    #status-bar {
        height: 1;
        background: #111;
        padding: 0 2;
        color: #666;
    }

    #panel-label {
        color: #444;
        text-style: bold;
        padding: 0 1;
        height: 1;
        background: #111;
    }

    .engine-tag-serper { color: green; }
    .engine-tag-ddg    { color: yellow; }
    .engine-tag-bing   { color: blue; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+e", "export_results", "Export"),
        Binding("ctrl+l", "clear_results", "Clear"),
        Binding("ctrl+t", "show_templates", "Templates"),
        Binding("escape", "clear_preview", "Clear preview"),
        Binding("enter", "open_url", "Open URL"),
    ]

    results: reactive[List[SearchResult]] = reactive([])
    selected_result: reactive[Optional[SearchResult]] = reactive(None)
    is_searching: reactive[bool] = reactive(False)

    def __init__(self, serper_key: str):
        super().__init__()
        self.serper_key = serper_key
        self.engines = [
            SerperEngine(api_key=serper_key),
            DuckDuckGoEngine(),
            BingEngine(),
        ]
        self._all_results: List[SearchResult] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical():
            yield Static(BANNER, id="banner")

            yield Input(
                placeholder="  enter dork query  (e.g. site:example.com filetype:pdf)",
                id="search-bar",
            )

            with Horizontal(id="controls"):
                yield Select(
                    options=[("All Engines", "all"), ("Serper only", "serper"), ("DDG + Bing", "free")],
                    value="all",
                    id="engine-select",
                )
                yield Button("Search", id="btn-search", variant="primary")
                yield Button("Templates", id="btn-templates")
                yield Button("Export", id="btn-export")

            with Horizontal(id="main-split"):
                with Vertical(id="results-panel"):
                    yield Static("  results", id="panel-label")
                    yield ListView(id="results-list")

                with Vertical(id="preview-panel"):
                    yield Static("  preview", id="panel-label")
                    yield Static("", id="preview-title")
                    yield Static("", id="preview-url")
                    yield Static("", id="preview-source")
                    yield Static("", id="preview-snippet")
                    with Horizontal(id="preview-actions"):
                        yield Button("Copy URL", id="btn-copy")

            yield RichLog(id="log-panel", highlight=True, markup=True, max_lines=50)
            yield Static(self._status_text(), id="status-bar")

        yield Footer()

    def _status_text(self) -> str:
        remaining = quota_display()
        count = len(self._all_results)
        searching = " [searching...]" if self.is_searching else ""
        return f" Serper: {remaining}  |  results: {count}{searching}  |  ctrl+q quit  ctrl+e export  ctrl+t templates"

    def _refresh_status(self):
        try:
            self.query_one("#status-bar", Static).update(self._status_text())
        except Exception:
            pass

    def on_mount(self) -> None:
        self.query_one("#search-bar", Input).focus()
        self._log("DorkMaxing ready. Enter a dork query or press ctrl+t for templates.")

    def _log(self, msg: str):
        try:
            log = self.query_one("#log-panel", RichLog)
            log.write(msg)
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-bar":
            self._run_search(event.value.strip())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-search":
            query = self.query_one("#search-bar", Input).value.strip()
            self._run_search(query)
        elif event.button.id == "btn-templates":
            self.action_show_templates()
        elif event.button.id == "btn-export":
            self.action_export_results()
        elif event.button.id == "btn-copy":
            if self.selected_result:
                import pyperclip
                try:
                    pyperclip.copy(self.selected_result.url)
                    self._log(f"Copied: {self.selected_result.url}")
                except Exception:
                    self._log(f"URL: {self.selected_result.url}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ResultItem):
            self.selected_result = event.item.result
            self._update_preview(event.item.result)

    def _update_preview(self, r: SearchResult):
        source_color = {"Serper": "green", "DuckDuckGo": "yellow", "Bing": "blue"}.get(r.source, "white")
        self.query_one("#preview-title", Static).update(
            Text(r.title or "(no title)", style="bold white")
        )
        self.query_one("#preview-url", Static).update(
            Text(r.url, style="cyan")
        )
        self.query_one("#preview-source", Static).update(
            Text(f"Source: {r.source}", style=source_color)
        )
        self.query_one("#preview-snippet", Static).update(
            Text(r.snippet or "(no snippet)", style="#aaaaaa")
        )

    def _run_search(self, query: str):
        if not query:
            return
        engine_select = self.query_one("#engine-select", Select).value
        engines = self._get_engines(engine_select)
        self.is_searching = True
        self._log(f"[cyan]Searching:[/cyan] {query}  [dim]engines: {', '.join(e.name for e in engines)}[/dim]")
        self._do_search(query, engines)

    def _get_engines(self, mode: str):
        if mode == "serper":
            return [e for e in self.engines if e.name == "Serper"]
        elif mode == "free":
            return [e for e in self.engines if e.name != "Serper"]
        return self.engines

    @work(exclusive=False, thread=False)
    async def _do_search(self, query: str, engines):
        try:
            responses = await dispatch(engines, query)
            results = aggregate(responses)
            self._all_results = results

            lv = self.query_one("#results-list", ListView)
            await lv.clear()
            for r in results:
                await lv.append(ResultItem(r))

            for resp in responses:
                if resp.error:
                    self._log(f"[red]{resp.engine} error:[/red] {resp.error}")
                else:
                    self._log(f"[dim]{resp.engine}:[/dim] {len(resp.results)} results  ({resp.elapsed}s)")

            self._log(f"[green]Done.[/green] {len(results)} unique results after dedup.")

            if results:
                save_scan(query, results, [e.name for e in engines])

        except Exception as e:
            self._log(f"[red]Search failed:[/red] {e}")
        finally:
            self.is_searching = False
            self._refresh_status()

    def action_export_results(self):
        if not self._all_results:
            self._log("[yellow]Nothing to export.[/yellow]")
            return
        path_json = os.path.expanduser("~/dorkmax_results.json")
        path_csv = os.path.expanduser("~/dorkmax_results.csv")
        export_json(self._all_results, path_json)
        export_csv(self._all_results, path_csv)
        self._log(f"[green]Exported:[/green] {path_json}  |  {path_csv}")

    def action_clear_results(self):
        lv = self.query_one("#results-list", ListView)
        lv.clear()
        self._all_results = []
        self.selected_result = None
        self._refresh_status()
        self._log("Results cleared.")

    def action_show_templates(self):
        templates = list_templates()
        self._log("[cyan]Available templates:[/cyan] " + "  ".join(templates))
        self._log("[dim]Usage: template:<name> target:<domain>  e.g.  template:login-panels target:example.com[/dim]")

    def action_clear_preview(self):
        self.selected_result = None
        for wid in ["#preview-title", "#preview-url", "#preview-source", "#preview-snippet"]:
            try:
                self.query_one(wid, Static).update("")
            except Exception:
                pass

    def action_open_url(self):
        if self.selected_result:
            import webbrowser
            webbrowser.open(self.selected_result.url)
            self._log(f"[cyan]Opening:[/cyan] {self.selected_result.url}")
