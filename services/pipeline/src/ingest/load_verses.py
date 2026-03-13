"""
Load Bhagavad Gita verses into ChromaDB for vector search.

Each verse is stored as a document combining:
- English translation (primary search target)
- Transliteration
- Word meanings
- Metadata: chapter, verse number, Sanskrit text, translator
"""

import json
from pathlib import Path

import chromadb

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "processed"
CHROMA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "chroma"


def load_data() -> tuple[list[dict], list[dict], list[dict]]:
    with open(DATA_DIR / "verses.json", encoding="utf-8") as f:
        verses = json.load(f)
    with open(DATA_DIR / "translations.json", encoding="utf-8") as f:
        translations = json.load(f)
    with open(DATA_DIR / "chapters.json", encoding="utf-8") as f:
        chapters = json.load(f)
    return verses, translations, chapters


def build_documents(
    verses: list[dict], translations: list[dict], chapters: list[dict]
) -> tuple[list[str], list[str], list[dict]]:
    """Build ChromaDB documents by combining verse text with English translations."""
    chapter_names = {ch["chapter_number"]: ch["name_meaning"] for ch in chapters}

    # Translations use a global sequential verse_number (1-701),
    # NOT chapter-specific numbering. Group by this sequential ID.
    eng_translations: dict[int, list[dict]] = {}
    for t in translations:
        if t["language"] == "english":
            eng_translations.setdefault(t["verse_number"], []).append(t)

    documents = []
    ids = []
    metadatas = []

    for seq_index, verse in enumerate(verses):
        # seq_index+1 maps to the global sequential verse_number in translations
        vnum = verse["verse_number"]
        verse_translations = eng_translations.get(seq_index + 1, [])

        # Pick the first available English translation
        translation_text = ""
        translator = ""
        if verse_translations:
            best = verse_translations[0]
            translation_text = best["text"]
            translator = best["author"]

        # Compose a rich document for embedding
        chapter_name = chapter_names.get(verse["chapter_number"], "")
        doc_parts = []

        if chapter_name:
            doc_parts.append(f"Chapter {verse['chapter_number']}: {chapter_name}")

        if translation_text:
            doc_parts.append(f"Translation: {translation_text}")

        if verse["transliteration"]:
            doc_parts.append(f"Transliteration: {verse['transliteration']}")

        if verse["word_meanings"]:
            doc_parts.append(f"Word meanings: {verse['word_meanings']}")

        documents.append("\n\n".join(doc_parts))
        ids.append(verse["id"])
        metadatas.append({
            "chapter_number": verse["chapter_number"],
            "verse_number": vnum,
            "sanskrit": verse["sanskrit"],
            "transliteration": verse["transliteration"],
            "translation": translation_text,
            "translator": translator,
            "chapter_name": chapter_name,
            "verse_id": verse["id"],
        })

    return documents, ids, metadatas


def ingest():
    print("Loading data...")
    verses, translations, chapters = load_data()

    print("Building documents...")
    documents, ids, metadatas = build_documents(verses, translations, chapters)
    print(f"Prepared {len(documents)} documents")

    print(f"Initializing ChromaDB at {CHROMA_DIR}...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete existing collection if re-ingesting
    try:
        client.delete_collection("gita_verses")
    except Exception:
        pass

    collection = client.create_collection(
        name="gita_verses",
        metadata={"description": "Bhagavad Gita verses with English translations"},
    )

    # ChromaDB has a batch limit, insert in chunks
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        end = min(i + batch_size, len(documents))
        collection.add(
            documents=documents[i:end],
            ids=ids[i:end],
            metadatas=metadatas[i:end],
        )
        print(f"  Inserted verses {i+1}-{end}")

    print(f"\nDone! {collection.count()} verses in ChromaDB")

    # Quick sanity check
    results = collection.query(query_texts=["What is the nature of the soul?"], n_results=3)
    print("\nSanity check — 'What is the nature of the soul?':")
    for doc_id, meta in zip(results["ids"][0], results["metadatas"][0]):
        print(f"  {doc_id}: {meta['translation'][:100]}...")


if __name__ == "__main__":
    ingest()
