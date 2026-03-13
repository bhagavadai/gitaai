"""
Fetch Bhagavad Gita data from public domain sources and structure it
for the GitaAI pipeline.

Source: https://github.com/praneshp1org/Bhagavad-Gita-JSON-data
License: Public domain / educational use

Outputs:
  - data/processed/chapters.json   (18 chapters with metadata)
  - data/processed/verses.json     (700 verses with Sanskrit, transliteration, word meanings)
  - data/processed/translations.json (multiple translations per verse)
"""

import json
import sys
from pathlib import Path
from urllib.request import urlopen

BASE_URL = (
    "https://raw.githubusercontent.com/praneshp1org/Bhagavad-Gita-JSON-data/main"
)
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed"


def fetch_json(filename: str) -> list[dict]:
    url = f"{BASE_URL}/{filename}"
    print(f"Fetching {url}...")
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8-sig"))


def process_chapters(raw: list[dict]) -> list[dict]:
    return [
        {
            "chapter_number": ch["chapter_number"],
            "name_sanskrit": ch.get("name", ""),
            "name_transliterated": ch.get("name_transliterated", ""),
            "name_translation": ch.get("name_translation", ""),
            "name_meaning": ch.get("name_meaning", ""),
            "verses_count": ch["verses_count"],
            "summary": ch.get("chapter_summary", ""),
            "summary_hindi": ch.get("chapter_summary_hindi", ""),
        }
        for ch in sorted(raw, key=lambda c: c["chapter_number"])
    ]


def process_verses(raw: list[dict]) -> list[dict]:
    return [
        {
            "id": f"BG_{v['chapter_number']}_{v['verse_number']}",
            "chapter_number": v["chapter_number"],
            "verse_number": v["verse_number"],
            "sanskrit": v.get("text", "").strip(),
            "transliteration": v.get("transliteration", "").strip(),
            "word_meanings": v.get("word_meanings", "").strip(),
        }
        for v in sorted(raw, key=lambda v: (v["chapter_number"], v["verse_number"]))
    ]


def process_translations(raw: list[dict]) -> list[dict]:
    return [
        {
            "verse_id": f"BG_{t['verse_id']}",
            "verse_number": t["verse_number"],
            "author": t.get("authorName", "Unknown"),
            "author_id": t.get("author_id"),
            "language": t.get("lang", "english"),
            "text": t.get("description", "").strip(),
        }
        for t in raw
        if t.get("description", "").strip()
    ]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapters_raw = fetch_json("chapters.json")
    verses_raw = fetch_json("verse.json")
    translations_raw = fetch_json("translation.json")

    chapters = process_chapters(chapters_raw)
    verses = process_verses(verses_raw)
    translations = process_translations(translations_raw)

    for filename, data in [
        ("chapters.json", chapters),
        ("verses.json", verses),
        ("translations.json", translations),
    ]:
        path = OUTPUT_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(data)} records to {path}")

    print(f"\nDone! {len(chapters)} chapters, {len(verses)} verses, {len(translations)} translations")


if __name__ == "__main__":
    main()
