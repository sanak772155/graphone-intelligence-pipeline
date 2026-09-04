import requests
import json
import re
import time
from datetime import datetime, timezone

OUTPUT_STARTUPS = "startups.json"
OUTPUT_PRODUCTS = "products.json"

# Curated GitHub "awesome list" repos that catalog real AI startups/products/tools
# Each has a README.md with markdown links: [Name](url) - description
AWESOME_LIST_SOURCES = [
    "https://raw.githubusercontent.com/mahseema/awesome-ai-tools/main/README.md",
    "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md",
    "https://raw.githubusercontent.com/filipecalegario/awesome-generative-ai/main/README.md",
    "https://raw.githubusercontent.com/jamesmurdza/awesome-ai-devtools/main/README.md",
    "https://raw.githubusercontent.com/underlines/awesome-marketing-datascience/master/awesome-ai-tools.md",
]

def parse_markdown_links(markdown_text, source_url):
    """
    Extracts entries in the format [Name](url) - description
    from a markdown awesome-list file.
    """
    entries = []
    # Matches: [Name](https://...) - optional description text
    pattern = re.compile(r'\[([^\]\[]{2,80})\]\((https?://[^\s\)]+)\)\s*[-–—:]?\s*([^\n]{0,200})')

    for match in pattern.finditer(markdown_text):
        name = match.group(1).strip()
        url = match.group(2).strip()
        description = match.group(3).strip()

        # Filter out obvious non-product/company links (badges, images, anchors, etc.)
        if any(skip in url.lower() for skip in ["shields.io", "badge", "github.com/sponsors", ".png", ".svg", ".gif", "#"]):
            continue
        if any(skip in name.lower() for skip in ["back to top", "contents", "license", "contribut"]):
            continue
        if len(name) < 2:
            continue

        entries.append({"name": name, "url": url, "description": description})

    return entries

def fetch_all_entries():
    all_entries = []
    session = requests.Session()
    session.headers.update({"User-Agent": "GraphOne-Research-Bot/1.0"})

    for source_url in AWESOME_LIST_SOURCES:
        print(f"Fetching: {source_url}")
        try:
            resp = session.get(source_url, timeout=20)
            if resp.status_code == 429:
                print("  Rate limited, waiting 15s...")
                time.sleep(15)
                resp = session.get(source_url, timeout=20)

            if resp.status_code != 200:
                print(f"  Skipped (status {resp.status_code})")
                continue

            entries = parse_markdown_links(resp.text, source_url)
            print(f"  Extracted {len(entries)} entries")

            for e in entries:
                e["source_list"] = source_url
            all_entries.extend(entries)

        except Exception as ex:
            print(f"  Error fetching {source_url}: {ex}")
            continue

        time.sleep(1)

    return all_entries

def dedupe_entries(entries):
    seen = set()
    unique = []
    for e in entries:
        key = e["name"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique

def build_records(entries):
    startups = []
    products = []
    now = datetime.now(timezone.utc).isoformat()

    for e in entries:
        startup_record = {
            "schemaVersion": "1.0",
            "recordType": "STARTUP",
            "source": {
                "name": "GitHub Awesome-List Aggregation",
                "url": e["source_list"]
            },
            "content": {
                "entityName": e["name"],
                "data": {
                    "employeeCount": None,  # not available from this source
                    "website": e["url"],
                    "description": e["description"]
                }
            },
            "collectedAt": now
        }
        startups.append(startup_record)

        product_record = {
            "schemaVersion": "1.0",
            "recordType": "PRODUCT",
            "source": {
                "name": "GitHub Awesome-List Aggregation",
                "url": e["source_list"]
            },
            "content": {
                "startupName": e["name"],
                "productName": e["name"],
                "description": e["description"],
                "pricingModel": "UNKNOWN",
                "website": e["url"]
            },
            "collectedAt": now
        }
        products.append(product_record)

    return startups, products

if __name__ == "__main__":
    print("Fetching AI startup/product entries from GitHub awesome-lists...\n")
    raw_entries = fetch_all_entries()
    print(f"\nTotal raw entries: {len(raw_entries)}")

    unique_entries = dedupe_entries(raw_entries)
    print(f"Total unique entries after dedup: {len(unique_entries)}")

    startups, products = build_records(unique_entries)

    with open(OUTPUT_STARTUPS, "w", encoding="utf-8") as f:
        json.dump(startups, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_PRODUCTS, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    print(f"\nDONE.")
    print(f"Total startups: {len(startups)}")
    print(f"Total products: {len(products)}")
    print(f"Saved to {OUTPUT_STARTUPS} and {OUTPUT_PRODUCTS}")
