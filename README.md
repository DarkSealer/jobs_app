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

1. Create a `config.yaml` file with your profile information
2. Set up API keys for job boards (if required)
3. Run the search agent

## Usage

```bash
python main.py --location "San Francisco" --remote
python main.py --location "New York" --radius 50
python main.py --remote-only
```

## Project Structure

- `main.py` - Entry point
- `config.yaml` - User profile and preferences
- `src/` - Source code
  - `scraper/` - Job board scrapers
  - `matcher/` - Job matching logic
  - `models/` - Data models
  - `utils/` - Utility functions
