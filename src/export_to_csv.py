import json
import csv
import os

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dict/list structures into flat CSV-friendly columns."""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep=sep))
        elif isinstance(v, list):
            items[new_key] = "; ".join(str(x) for x in v)
        else:
            items[new_key] = v
    return items

def json_to_csv(json_file, csv_file):
    if not os.path.exists(json_file):
        print(f"  Skipped: {json_file} not found")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print(f"  Skipped: {json_file} is empty")
        return

    flat_rows = [flatten_dict(row) for row in data]

    # Collect all possible fieldnames across all rows
    fieldnames = []
    for row in flat_rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)

    print(f"  {json_file} -> {csv_file} ({len(flat_rows)} rows)")

if __name__ == "__main__":
    print("Converting JSON files to CSV for Google Sheets...\n")

    conversions = [
        ("startups.json", "startups.csv"),
        ("products.json", "products.csv"),
        ("research_papers.json", "research_papers.csv"),
        ("jobs.json", "jobs.csv"),
        ("news.json", "news.csv"),
        ("entity_mapping_log.json", "entity_mapping_log_export.csv"),
    ]

    for json_file, csv_file in conversions:
        json_to_csv(json_file, csv_file)

    print("\nDONE. All CSV files ready for Google Sheets import.")
