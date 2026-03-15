"""
Load Bhagavad Gita verses into ChromaDB for vector search.

Each verse is stored as a document combining:
- English translation (primary search target)
- Transliteration
- Word meanings
- Metadata: chapter, verse number, Sanskrit text, translator
"""

import json
import logging
from pathlib import Path

import chromadb

from ..config import settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(settings.data_dir) / "processed"
CHROMA_DIR = Path(settings.chroma_persist_dir)


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
    # NOT chapter-specific numbering. Group by language and sequential ID.
    translations_by_lang: dict[str, dict[int, list[dict]]] = {}
    for t in translations:
        lang = t["language"]
        translations_by_lang.setdefault(lang, {}).setdefault(t["verse_number"], []).append(t)

    eng_translations = translations_by_lang.get("english", {})
    hindi_translations = translations_by_lang.get("hindi", {})

    documents = []
    ids = []
    metadatas = []

    for seq_index, verse in enumerate(verses):
        # seq_index+1 maps to the global sequential verse_number in translations
        seq_num = seq_index + 1
        vnum = verse["verse_number"]

        # Pick English translation
        eng_list = eng_translations.get(seq_num, [])
        translation_text = eng_list[0]["text"] if eng_list else ""
        translator = eng_list[0]["author"] if eng_list else ""

        # Pick Hindi translation
        hindi_list = hindi_translations.get(seq_num, [])
        translation_hindi = hindi_list[0]["text"] if hindi_list else ""
        translator_hindi = hindi_list[0]["author"] if hindi_list else ""

        # Compose a rich document for embedding (English + Hindi for better retrieval)
        chapter_name = chapter_names.get(verse["chapter_number"], "")
        doc_parts = []

        if chapter_name:
            doc_parts.append(f"Chapter {verse['chapter_number']}: {chapter_name}")

        if translation_text:
            doc_parts.append(f"Translation: {translation_text}")

        if translation_hindi:
            doc_parts.append(f"Hindi: {translation_hindi}")

        if verse["transliteration"]:
            doc_parts.append(f"Transliteration: {verse['transliteration']}")

        if verse["word_meanings"]:
            doc_parts.append(f"Word meanings: {verse['word_meanings']}")

        documents.append("\n\n".join(doc_parts))
        ids.append(verse["id"])
        metadatas.append(
            {
                "chapter_number": verse["chapter_number"],
                "verse_number": vnum,
                "sanskrit": verse["sanskrit"],
                "transliteration": verse["transliteration"],
                "translation": translation_text,
                "translator": translator,
                "translation_hindi": translation_hindi,
                "translator_hindi": translator_hindi,
                "chapter_name": chapter_name,
                "verse_id": verse["id"],
            }
        )

    return documents, ids, metadatas


def ingest():
    logger.info("Loading data...")
    verses, translations, chapters = load_data()

    logger.info("Building documents...")
    documents, ids, metadatas = build_documents(verses, translations, chapters)
    logger.info("Prepared %d documents", len(documents))

    logger.info("Initializing ChromaDB at %s...", CHROMA_DIR)
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
        logger.info("  Inserted verses %d-%d", i + 1, end)

    logger.info("Done! %d verses in ChromaDB", collection.count())

    # Quick sanity check
    results = collection.query(query_texts=["What is the nature of the soul?"], n_results=3)
    logger.info("Sanity check — 'What is the nature of the soul?':")
    for doc_id, meta in zip(results["ids"][0], results["metadatas"][0]):
        logger.info("  %s: %s...", doc_id, meta["translation"][:100])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ingest()
