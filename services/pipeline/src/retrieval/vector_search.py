"""Vector search over Gita verses using ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb

CHROMA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "chroma"

_client: Optional[chromadb.PersistentClient] = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_collection("gita_verses")
    return _collection


def search_verses(query: str, n_results: int = 5) -> list[dict]:
    """Search for verses relevant to the query.

    Returns a list of dicts with keys:
        verse_id, chapter_number, verse_number, sanskrit,
        transliteration, translation, translator, chapter_name
    """
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=n_results)

    verses = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        verses.append({
            "verse_id": meta["verse_id"],
            "chapter_number": meta["chapter_number"],
            "verse_number": meta["verse_number"],
            "sanskrit": meta["sanskrit"],
            "transliteration": meta["transliteration"],
            "translation": meta["translation"],
            "translator": meta["translator"],
            "chapter_name": meta["chapter_name"],
            "relevance_rank": i + 1,
        })

    return verses
