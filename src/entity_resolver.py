import json
import csv
from rapidfuzz import fuzz, process

# Seed list of known canonical AI startup names (mock database of 50)
CANONICAL_STARTUPS = [
    "OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Microsoft",
    "NVIDIA", "Mistral AI", "Cohere", "Stability AI", "Hugging Face",
    "xAI", "Perplexity AI", "Scale AI", "Databricks", "Together AI",
    "Runway", "Character.AI", "Inflection AI", "Adept AI", "AI21 Labs",
    "Midjourney", "ElevenLabs", "Replit", "LangChain", "Pinecone",
    "Weights & Biases", "Cerebras Systems", "Groq", "SambaNova Systems",
    "Anyscale", "Snorkel AI", "Tabnine", "Glean", "Harvey AI",
    "Sierra", "Cursor", "Vercel", "Fireworks AI", "Baseten",
    "Modal Labs", "LlamaIndex", "Voyage AI", "Contextual AI",
    "Imbue", "Reka AI", "01.AI", "Zhipu AI", "Moonshot AI",
    "DeepSeek", "Qwen (Alibaba)"
]

def canonicalize(raw_name, threshold=80):
    """
    Match a raw/messy entity name against the canonical seed list.
    Returns (canonical_name, match_score) or (None, 0) if no good match.
    """
    if not raw_name or not raw_name.strip():
        return None, 0

    match = process.extractOne(
        raw_name,
        CANONICAL_STARTUPS,
        scorer=fuzz.WRatio
    )
    if match and match[1] >= threshold:
        return match[0], match[1]
    return None, 0

def build_mapping_log(raw_names_list):
    """Given a list of raw/messy names, produce a resolution log."""
    log = []
    for raw in raw_names_list:
        canonical, score = canonicalize(raw)
        log.append({
            "raw_name": raw,
            "canonical_name": canonical if canonical else raw,
            "match_score": score,
            "resolved": canonical is not None
        })
    return log

if __name__ == "__main__":
    # Test / demo cases showing messy variants resolving correctly
    test_raw_names = [
        "OpenAI", "OpenAI, Inc.", "Open AI", "open-ai",
        "Anthropic", "Anthropic PBC", "anthropic.com",
        "Google DeepMind", "DeepMind", "Google Deep Mind",
        "Hugging Face", "HuggingFace", "hugging-face",
        "Meta AI", "Meta Platforms AI", "MetaAI",
        "Stability AI", "Stability.ai", "Stability A.I.",
        "Mistral", "Mistral AI SAS",
        "xAI Corp", "X.AI",
        "Perplexity", "Perplexity.ai",
        "Some Totally Unknown Startup Inc"  # should NOT match (unresolved)
    ]

    mapping_log = build_mapping_log(test_raw_names)

    # Save as JSON
    with open("entity_mapping_log.json", "w", encoding="utf-8") as f:
        json.dump(mapping_log, f, indent=2, ensure_ascii=False)

    # Save as CSV too (easy to paste into Google Sheets)
    with open("entity_mapping_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["raw_name", "canonical_name", "match_score", "resolved"])
        writer.writeheader()
        writer.writerows(mapping_log)

    print("Entity resolution results:\n")
    for entry in mapping_log:
        status = "✓ MATCHED" if entry["resolved"] else "✗ NO MATCH"
        print(f"{status} | '{entry['raw_name']}' -> '{entry['canonical_name']}' (score: {entry['match_score']})")

    print(f"\nSaved to entity_mapping_log.json and entity_mapping_log.csv")
  
