# Job Radar (Job Search Agent)

This repository contains:

1. **Job Radar** — a **Streamlit** UI for configuring your profile, choosing sources, running searches, reviewing ranked matches, and tracking applications over time (SQLite).
2. **Job Search Agent** — the original **Click** CLI that loads `config.yaml`, scrapes enabled boards, matches jobs, and writes JSON/CSV under `results/`.

Both share the same backend: scrapers in `src/scraper/`, matching in `src/matcher/`, and models in `src/models/`.

## Install

```bash
pip install -r requirements.txt
```

## Run the GUI (Job Radar)

From the project root, use **Python’s module runner** so you do not rely on the `streamlit` executable being on `PATH` (common on Windows):

```powershell
python -m streamlit run app.py
```

Or double‑click / run **`run_gui.bat`** in this folder (same command).

If `streamlit` is on your `PATH` (e.g. some virtualenvs), `streamlit run app.py` also works.

Then open the URL shown in the terminal. Navigation lives in the sidebar (native multipage navigation is turned off in `.streamlit/config.toml` so only the custom menu appears).

After a search, use **Open Results inbox** on the Search page (or the sidebar). The **Results** page has its own **Minimum score (filter)** slider: it defaults to **0** so every stored job is visible. The number “X at or above Y” on Search only counts jobs that met your **search** minimum score; weaker matches are still saved and appear when the Results filter is 0.

### Where data is stored

- **SQLite database:** `data/jobs.db` (created automatically; the file is gitignored).
- **Optional YAML:** `config.yaml` (local only; gitignored) still drives board-specific limits (e.g. `search_limit`), Lever/Greenhouse options, and can supply **projects** if you leave the profile projects JSON empty in the GUI.

### Sources: automated vs manual

In **Job Radar → Search**, only **automated** boards are queried. These are treated as **manual / browser** and are **never** auto-scraped from the GUI (they may remain enabled for visibility in **Sources**):

- LinkedIn  
- Glassdoor  
- Upwork  

The CLI (`python main.py search`) can still register those scrapers when they are enabled in YAML (placeholders or limited implementations today).

## Run the CLI (unchanged)

```bash
python main.py search --help
python main.py search --remote-only --limit 30
python main.py show_profile
python main.py init
```

Copy `config.example.yaml` to `config.yaml` (or run `python main.py init`), then edit `config.yaml` locally.

## Matching scores

Overall match score uses **fixed normalized weights** in code:

- Skills overlap (extracted tech vs profile): **45%**
- Title relevance: **20%**
- Experience fit: **20%**
- Project stack overlap: **15%**

If there is **no** overlap between extracted job technologies and your profile skills, the score is **capped at 55**. Quality bands (**Excellent / Strong / Maybe / Weak**) are shown in the GUI and in CSV exports alongside legacy letter **grades**.

The `matching:` block in `config.example.yaml` is documented as **legacy / unused** for overall weighting; `min_skill_match` may still be referenced in future filters.

## Tests

```bash
python -m pytest tests/test_matcher_scoring.py -v
```

## Project layout (high level)

| Path | Role |
|------|------|
| `app.py` | Streamlit home |
| `pages/` | Streamlit multipage UI |
| `src/scraper/` | Job board scrapers + `registry.py` registration |
| `src/matcher/` | `JobMatcher` scoring |
| `src/gui/` | SQLite (`database.py`), orchestration (`services.py`), UI helpers |
| `data/jobs.db` | GUI persistence (local) |
| `main.py` | CLI entry |

## Known limitations

- Scrapers depend on public HTML/APIs; sites may rate-limit or block automated access.
- Some boards are placeholders or return empty results until you add supported integrations.
- Job Radar does not perform cloud sync or multi-user accounts; everything is local SQLite.
