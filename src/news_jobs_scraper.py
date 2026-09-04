import re
import feedparser
import requests
import json
import re
import time
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
from bs4 import BeautifulSoup

NOW = datetime.now(timezone.utc)
CUTOFF = NOW - timedelta(hours=24)

OUTPUT_NEWS = "news.json"
OUTPUT_JOBS = "jobs.json"

# 5 AI news sources (RSS feeds - reliable, no anti-bot issues)
NEWS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "MarkTechPost", "url": "https://www.marktechpost.com/feed/"},
    {"name": "AI News", "url": "https://www.artificialintelligence-news.com/feed/"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
]

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 GraphOne-Research-Bot/1.0"})


def parse_date_safe(date_str):
    """Normalize any date string (ISO, RFC822, relative) into a UTC datetime."""
    if not date_str:
        return None
    try:
        dt = dateparser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def extract_full_text(url):
    """Fetch article page and extract main text content (best-effort, generic)."""
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)
        return text[:5000]  # cap length, avoid huge payloads (413 prevention)
    except Exception:
        return ""


def scrape_news():
    all_news = []
    for feed_info in NEWS_FEEDS:
        print(f"Fetching news: {feed_info['name']}")
        try:
            feed = feedparser.parse(feed_info["url"])
            if feed.bozo and not feed.entries:
                print(f"  Failed to parse feed")
                continue

            for entry in feed.entries:
                pub_date_str = entry.get("published") or entry.get("updated")
                pub_date = parse_date_safe(pub_date_str)

                # Freshness check: only keep articles from last 24 hours
                if pub_date is None or pub_date < CUTOFF:
                    continue

                link = entry.get("link", "")
                title = entry.get("title", "").strip()
                full_text = extract_full_text(link) if link else ""

                record = {
                    "schemaVersion": "1.0",
                    "recordType": "NEWS",
                    "source": {
                        "name": feed_info["name"],
                        "url": link
                    },
                    "content": {
                        "title": title,
                        "summary": entry.get("summary", "")[:500],
                        "full_text": full_text,
                        "published_date": pub_date.isoformat()
                    },
                    "collectedAt": NOW.isoformat()
                }
                all_news.append(record)
                time.sleep(0.5)

            print(f"  Fresh (24h) articles found: {sum(1 for n in all_news if n['source']['name'] == feed_info['name'])}")

        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1)

    return all_news


def infer_role_family(title):
    title_lower = title.lower()
    if any(k in title_lower for k in ["engineer", "developer", "swe", "backend", "frontend", "fullstack"]):
        return "Engineering"
    if any(k in title_lower for k in ["research", "scientist", "phd"]):
        return "Research"
    if any(k in title_lower for k in ["product manager", "pm "]):
        return "Product"
    if any(k in title_lower for k in ["data scientist", "data analyst", "ml engineer", "machine learning"]):
        return "Data/ML"
    if any(k in title_lower for k in ["sales", "account executive", "bd "]):
        return "Sales"
    if any(k in title_lower for k in ["marketing", "growth"]):
        return "Marketing"
    return "Other"


def scrape_remoteok_jobs():
    """RemoteOK public JSON API - filtered for AI-related roles, last 24h."""
    jobs = []
    try:
        print("Fetching jobs: RemoteOK")
        resp = session.get("https://remoteok.com/api", timeout=15)
        if resp.status_code != 200:
            print(f"  Error {resp.status_code}")
            return jobs

        data = resp.json()
        for item in data:
            if not isinstance(item, dict) or "position" not in item:
                continue  # first item is metadata, skip

            tags = " ".join(item.get("tags", [])).lower()
            position = item.get("position", "").lower()
            if not re.search(r'\b(ai|artificial intelligence|machine learning|ml engineer|data scien|deep learning|llm|nlp|neural network)\b', tags + " " + position):
                continue

            date_str = item.get("date")
            pub_date = parse_date_safe(date_str)
            if pub_date is None or pub_date < CUTOFF:
                continue

            record = {
                "schemaVersion": "1.0",
                "recordType": "JOB",
                "source": {
                    "name": "RemoteOK",
                    "url": item.get("url", "")
                },
                "content": {
                    "company": item.get("company", "").strip(),
                    "title": item.get("position", "").strip(),
                    "date": pub_date.isoformat(),
                    "is_remote": True,
                    "role_family": infer_role_family(item.get("position", "")),
                    "tags": item.get("tags", [])
                },
                "collectedAt": NOW.isoformat()
            }
            jobs.append(record)

        print(f"  Fresh (24h) AI jobs found: {len(jobs)}")

    except Exception as e:
        print(f"  Error: {e}")

    return jobs
def scrape_hn_hiring_jobs():
    """Hacker News 'Who is Hiring' thread - top-level comments as job posts, filtered for AI + 24h freshness."""
    jobs = []
    try:
        print("Fetching jobs: Hacker News Who's Hiring")
        search_resp = session.get(
            "https://hn.algolia.com/api/v1/search_by_date?query=Who%20is%20Hiring&tags=story,author_whoishiring",
            timeout=15
        )
        if search_resp.status_code != 200:
            print(f"  Error {search_resp.status_code}")
            return jobs

        hits = search_resp.json().get("hits", [])
        if not hits:
            print("  No hiring thread found")
            return jobs

        thread_id = hits[0]["objectID"]
        thread_resp = session.get(f"https://hn.algolia.com/api/v1/items/{thread_id}", timeout=20)
        if thread_resp.status_code != 200:
            print(f"  Error fetching thread {thread_resp.status_code}")
            return jobs

        children = thread_resp.json().get("children", [])

        for comment in children:
            text = comment.get("text") or ""
            if not text:
                continue

            created_at = comment.get("created_at")
            pub_date = parse_date_safe(created_at)
            if pub_date is None or pub_date < CUTOFF:
                continue

            if not re.search(r'\b(ai|artificial intelligence|machine learning|ml engineer|data scientist|deep learning|llm|nlp)\b', text.lower()):
                continue

            clean_text = BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
            title_line = clean_text[:120]
            company_guess = clean_text.split("|")[0].strip()[:80] if "|" in clean_text else "Unknown"

            record = {
                "schemaVersion": "1.0",
                "recordType": "JOB",
                "source": {
                    "name": "Hacker News Who's Hiring",
                    "url": f"https://news.ycombinator.com/item?id={comment.get('id')}"
                },
                "content": {
                    "company": company_guess,
                    "title": title_line,
                    "date": pub_date.isoformat(),
                    "is_remote": "remote" in clean_text.lower(),
                    "role_family": infer_role_family(clean_text),
                    "tags": []
                },
                "collectedAt": NOW.isoformat()
            }
            jobs.append(record)

        print(f"  Fresh (24h) AI jobs found: {len(jobs)}")

    except Exception as e:
        print(f"  Error: {e}")

    return jobs

def scrape_wwr_jobs():
    """We Work Remotely RSS feed for programming jobs, filtered for AI keywords."""
    jobs = []
    feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    print("Fetching jobs: We Work Remotely")
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            if not any(k in title.lower() for k in ["ai", "machine learning", "ml", "data scientist"]):
                continue

            pub_date_str = entry.get("published")
            pub_date = parse_date_safe(pub_date_str)
            if pub_date is None or pub_date < CUTOFF:
                continue

            # WWR titles are usually "Company: Job Title"
            company = title.split(":")[0].strip() if ":" in title else "Unknown"

            record = {
                "schemaVersion": "1.0",
                "recordType": "JOB",
                "source": {
                    "name": "We Work Remotely",
                    "url": entry.get("link", "")
                },
                "content": {
                    "company": company,
                    "title": title,
                    "date": pub_date.isoformat(),
                    "is_remote": True,
                    "role_family": infer_role_family(title),
                    "tags": []
                },
                "collectedAt": NOW.isoformat()
            }
            jobs.append(record)

        print(f"  Fresh (24h) AI jobs found: {len(jobs)}")

    except Exception as e:
        print(f"  Error: {e}")

    return jobs


if __name__ == "__main__":
    print(f"Cutoff for 24h freshness: {CUTOFF.isoformat()}\n")

    print("=== SCRAPING NEWS ===")
    news = scrape_news()

    print("\n=== SCRAPING JOBS ===")
    jobs =scrape_remoteok_jobs() + scrape_wwr_jobs() + scrape_hn_hiring_jobs()

    with open(OUTPUT_NEWS, "w", encoding="utf-8") as f:
        json.dump(news, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_JOBS, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    print(f"\nDONE.")
    print(f"Total fresh (24h) news articles: {len(news)}")
    print(f"Total fresh (24h) jobs: {len(jobs)}")
    print(f"Saved to {OUTPUT_NEWS} and {OUTPUT_JOBS}")
