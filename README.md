# GraphOne Intelligence Pipeline

A data ingestion pipeline for the AI/venture ecosystem — scraping startups, products, research papers, jobs, and news, with LLM-based structuring and entity resolution.

## What This Does

- **Research Papers**: Scrapes arXiv (via official API) for AI/ML papers, extracts GitHub repo links from abstracts, and pulls live star counts via the GitHub API.
- **Startups & Products**: Aggregates real, sourced entries from curated GitHub "awesome-list" repositories (community-maintained catalogs of AI tools/companies).
- **News**: Pulls from 5 AI news RSS feeds (TechCrunch AI, VentureBeat AI, MarkTechPost, AI News, The Verge AI), filters to the last 24 hours using normalized publish dates, and extracts full article text.
- **Jobs**: Pulls from RemoteOK API, We Work Remotely RSS, and Hacker News "Who's Hiring" thread, filtered to AI-related roles posted in the last 24 hours.
- **Entity Resolution**: Fuzzy-matches messy company name variants (e.g. "OpenAI, Inc." / "Open AI") against a canonical seed list using RapidFuzz.

## Setup

Install dependencies:
pip install -r requirements.txt

Create a `.env` file with:
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here

## Usage

cd src
python paper_scraper.py        (creates research_papers.json)
python startup_scraper.py      (creates startups.json, products.json)
python news_jobs_scraper.py    (creates news.json, jobs.json)
python entity_resolver.py      (creates entity_mapping_log.json)
python export_to_csv.py        (converts all JSON to CSV for Sheets import)

## Architecture

See `architecture.pdf` for the full design document covering:
- Scaling to 500,000+ records
- Handling 413 (payload too large) and 429 (rate limit) errors
- Freshness tracking across distributed crawler runs
- Storage strategy (relational + document + graph)

## Data Output

Live data is published in a Google Sheet with 6 tabs — Startups, Products, Research Papers, Jobs, News, Entity Mapping. Link included in the submission form.

## Results (this run)

| Entity | Count |
|---|---|
| Startups | 1,595 |
| Products | 1,595 |
| Research Papers | 840 (with GitHub star tracking) |
| News (24h fresh) | 27 |
| Jobs (24h fresh) | 13 |
| Entity mappings tested | 26 |

## Notes on Design Decisions

- **No hallucinated data**: every record traces back to a real, fetched source URL (arXiv API, GitHub API, RSS feeds, JSON APIs). Nothing is LLM-generated without a source.
- **Freshness**: news/jobs are filtered using `dateutil` to normalize ISO, RFC822, and relative dates against a 24-hour UTC cutoff.
- **Anti-bot strategy**: sources were deliberately chosen to avoid Cloudflare/Datadome-protected endpoints (official APIs, RSS feeds, raw GitHub content) rather than attempting to bypass protections, which is safer and more maintainable at scale. See `architecture.pdf` for how Playwright + proxy rotation would extend this to protected sources like Crunchbase.
