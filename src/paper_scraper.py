import arxiv
import requests
import json
import time
import re
from datetime import datetime, timezone

OUTPUT_FILE = "research_papers.json"
TARGET_COUNT = 1000
SEARCH_QUERIES = [
    "artificial intelligence",
    "machine learning",
    "large language models",
    "computer vision",
    "reinforcement learning",
    "natural language processing",
    "deep learning",
    "generative AI",
    "neural networks",
    "transformers"
]

def extract_github_url(text):
    """Find a GitHub repo URL mentioned in abstract/comment text."""
    if not text:
        return None
    match = re.search(r'https?://github\.com/[A-Za-z0-9_\-]+/[A-Za-z0-9_\-\.]+', text)
    if match:
        url = match.group(0).rstrip('.,)')
        return url
    return None

def get_github_stars(github_url, session):
    """Query GitHub API for star count. Returns None if not found/rate-limited."""
    try:
        # Extract owner/repo from URL
        parts = github_url.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        resp = session.get(api_url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("stargazers_count")
        elif resp.status_code == 403:
            # Rate limited - back off
            print("  GitHub rate limit hit, sleeping 30s...")
            time.sleep(30)
            return None
        else:
            return None
    except Exception as e:
        print(f"  GitHub lookup failed: {e}")
        return None

def scrape_arxiv_papers(target_count=TARGET_COUNT):
    results = []
    seen_ids = set()
    session = requests.Session()
    session.headers.update({"User-Agent": "GraphOne-Research-Bot/1.0"})

    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)

    for query in SEARCH_QUERIES:
        if len(results) >= target_count:
            break

        print(f"\nSearching arXiv for: '{query}'")
        search = arxiv.Search(
            query=query,
            max_results=200,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        try:
            for paper in client.results(search):
                if paper.entry_id in seen_ids:
                    continue
                seen_ids.add(paper.entry_id)

                # Look for GitHub link in abstract or comment
                combined_text = f"{paper.summary} {paper.comment or ''}"
                github_url = extract_github_url(combined_text)
                github_stars = None

                if github_url:
                    github_stars = get_github_stars(github_url, session)
                    time.sleep(1)  # be polite to GitHub API

                record = {
                    "schemaVersion": "1.0",
                    "recordType": "RESEARCH_PAPER",
                    "source": {
                        "name": "arXiv",
                        "url": paper.entry_id
                    },
                    "content": {
                        "title": paper.title.strip().replace("\n", " "),
                        "authors": [a.name for a in paper.authors],
                        "paper_url": paper.entry_id,
                        "pdf_url": paper.pdf_url,
                        "github_url": github_url,
                        "github_stars": github_stars,
                        "published_date": paper.published.isoformat() if paper.published else None,
                        "primary_category": paper.primary_category
                    },
                    "collectedAt": datetime.now(timezone.utc).isoformat()
                }
                results.append(record)

                if len(results) % 50 == 0:
                    print(f"  Collected {len(results)} papers so far...")

                if len(results) >= target_count:
                    break

        except Exception as e:
            print(f"  Error during query '{query}': {e}")
            time.sleep(5)
            continue

        time.sleep(2)  # pause between queries

    return results

if __name__ == "__main__":
    print(f"Starting arXiv paper scrape, target = {TARGET_COUNT} papers...")
    papers = scrape_arxiv_papers(TARGET_COUNT)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    with_github = sum(1 for p in papers if p["content"]["github_url"])
    with_stars = sum(1 for p in papers if p["content"]["github_stars"] is not None)

    print(f"\nDONE.")
    print(f"Total papers collected: {len(papers)}")
    print(f"Papers with GitHub link found: {with_github}")
    print(f"Papers with GitHub star count: {with_stars}")
    print(f"Saved to {OUTPUT_FILE}")
