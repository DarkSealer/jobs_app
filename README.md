# Job Search Agent

An intelligent job search application that automatically finds jobs matching your skills, experience, and projects across multiple job boards.

## Features

- **Multi-platform search**: Searches across LinkedIn, Indeed, Glassdoor, and other job boards
- **Tech stack filtering**: Analyzes job descriptions to find roles matching your specific technologies
- **Location filtering**: Search by specific location or remote opportunities
- **Profile-based matching**: Uses your description, experience, and projects to find relevant jobs
- **Automated scraping**: Continuously monitors new job postings

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example config and edit it locally (never commit real names, emails, or credentials):

   ```bash
   copy config.example.yaml config.yaml
   ```

   On macOS/Linux: `cp config.example.yaml config.yaml`

2. Or run: `python main.py init` (creates `config.yaml` from `config.example.yaml`).

3. Some scrapers only work with public feeds; boards that require login will stay empty until you add supported integrations. Keep any future API keys or session material in environment variables or a private file that stays **out** of git (see `.gitignore`).

## Usage

```bash
python main.py search --location "San Francisco" --remote
python main.py search --location "New York" --limit 50
python main.py search --remote-only
```

## Project Structure

- `main.py` - Entry point
- `config.example.yaml` - Safe template committed to the repo
- `config.yaml` - Your local profile (gitignored; not in the repo)
- `src/` - Source code
  - `scraper/` - Job board scrapers
  - `matcher/` - Job matching logic
  - `models/` - Data models
  - `utils/` - Utility functions
