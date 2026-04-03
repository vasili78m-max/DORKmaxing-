# DorkMaxing

Google dorking automation in your terminal. Fires queries at Serper (Google results), DuckDuckGo, and Bing in parallel, deduplicates, and streams results into a clean TUI.

```
 ██████╗  ██████╗ ██████╗ ██╗  ██╗███╗   ███╗ █████╗ ██╗  ██╗
██╔══██╗██╔═══██╗██╔══██╗██║ ██╔╝████╗ ████║██╔══██╗╚██╗██╔╝
██║  ██║██║   ██║██████╔╝█████╔╝ ██╔████╔██║███████║ ╚███╔╝ 
██║  ██║██║   ██║██╔══██╗██╔═██╗ ██║╚██╔╝██║██╔══██║ ██╔██╗ 
██████╔╝╚██████╔╝██║  ██║██║  ██╗██║ ╚═╝ ██║██║  ██║██╔╝ ██╗
╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
```

---

## Setup

### 1. Clone

```bash
git clone https://github.com/yourname/dorkmax
cd dorkmax
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or install as a global command:

```bash
pip install -e .
```

### 3. Add your Serper API key

```bash
cp .env.example .env
```

Edit `.env` and paste your key:

```
SERPER_API_KEY=your_key_here
```

Get a free key at [serper.dev](https://serper.dev) — 2,500 free requests/month.

---

## Usage

### Launch the TUI

```bash
python main.py
# or if installed globally:
dorkmax
```

### Pre-fill a query on launch

```bash
python main.py "site:example.com filetype:pdf"
```

### Use a built-in template

```bash
python main.py --template login-panels --target example.com
```

### Headless mode (no TUI, print to stdout)

```bash
python main.py "inurl:admin" --no-tui
python main.py --template exposed-env --target example.com --no-tui --export results.json
```

### Other commands

```bash
dorkmax templates   # list all built-in dork templates
dorkmax history     # show recent scan history
dorkmax quota       # show Serper API quota
```

---

## TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Run search / open selected URL in browser |
| `Ctrl+E` | Export results to JSON + CSV |
| `Ctrl+L` | Clear results |
| `Ctrl+T` | Show available templates |
| `Ctrl+Q` | Quit |
| `Escape` | Clear preview pane |
| `↑ / ↓` | Navigate results |

---

## Built-in Dork Templates

| Template | What it finds |
|----------|--------------|
| `exposed-env` | `.env` files with secrets |
| `login-panels` | Admin/login pages |
| `open-directories` | Directory listings |
| `config-files` | XML/YAML/JSON config files |
| `sensitive-docs` | PDFs, XLS with confidential labels |
| `git-exposed` | Exposed `.git` directories |
| `sql-errors` | Pages leaking SQL error messages |
| `backup-files` | `.bak`, `.sql`, `.old` backup files |
| `cameras` | Exposed webcam interfaces |
| `api-keys` | Pages containing API key references |

Use with `--target` to scope to a domain:

```bash
dorkmax --template backup-files --target example.com --no-tui
```

Or enter in TUI with the syntax:

```
template:backup-files target:example.com
```

---

## Engine Notes

| Engine | Type | Notes |
|--------|------|-------|
| Serper | API | Google results. Costs 1 request/query. Free: 2500/month |
| DuckDuckGo | Scrape | Free, no quota. Random delay applied automatically |
| Bing | Scrape | Free, no quota. Slower delay to avoid blocks |

Quota is tracked locally in `~/.dorkmax/quota.json` and resets monthly.

---

## Project Structure

```
dorkmax/
├── main.py              # CLI entrypoint (Typer)
├── app.py               # Textual TUI app
├── engines/             # one adapter per engine
│   ├── base.py
│   ├── serper.py
│   ├── duckduckgo.py
│   └── bing.py
├── core/
│   ├── dispatcher.py    # async parallel runner
│   ├── aggregator.py    # merge + dedup
│   ├── dork_builder.py  # template → query
│   └── quota.py         # Serper request counter
├── templates/
│   └── dorks.yaml       # built-in dork categories
├── output/
│   ├── formatter.py     # JSON/CSV export
│   └── history.py       # scan history
└── utils/
    ├── useragent.py     # UA rotation
    └── normalizer.py    # URL dedup
```

---

## Adding Custom Templates

Edit `templates/dorks.yaml` and add your own category:

```yaml
my-category:
  - 'inurl:something site:{target}'
  - 'filetype:xyz "keyword" site:{target}'
```

Then use it with:

```bash
dorkmax --template my-category --target example.com
```

---

## Disclaimer

DorkMaxing is for educational and authorized security research only. Only use against systems you have permission to test. The authors are not responsible for misuse.
