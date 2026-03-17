"""Graph traversal for concept expansion and relationship discovery."""

from __future__ import annotations

import re

import kuzu

from ..config import settings

_db = None
_conn = None


def get_connection() -> kuzu.Connection:
    global _db, _conn
    if _db is None:
        _db = kuzu.Database(settings.kuzu_db_dir)
        _conn = kuzu.Connection(_db)
    return _conn


def _query_to_dicts(
    conn: kuzu.Connection,
    cypher: str,
    parameters: dict | None = None,
) -> list[dict]:
    """Execute a Cypher query and return results as a list of dicts."""
    result = conn.execute(cypher, parameters=parameters or {})
    columns = result.get_column_names()
    rows = []
    while result.has_next():
        values = result.get_next()
        rows.append(dict(zip(columns, values)))
    return rows


def find_concepts_for_query(query: str) -> list[dict]:
    """Find concepts whose names or Sanskrit terms appear in the query.

    Uses case-insensitive matching against concept names, Sanskrit terms,
    and common variations.
    """
    conn = get_connection()
    rows = _query_to_dicts(
        conn,
        "MATCH (c:Concept) "
        "WHERE lower(c.name) CONTAINS lower($query) "
        "   OR lower(c.sanskrit_term) CONTAINS lower($query) "
        "   OR lower(c.id) CONTAINS lower($query) "
        "RETURN c.id AS id, c.name AS name, c.sanskrit_term AS sanskrit_term, "
        "       c.category AS category, c.`description` AS `description`, "
        "       c.description_hindi AS description_hindi",
        {"query": query},
    )
    return rows


def expand_concepts(concept_ids: list[str], depth: int = 1) -> dict:
    """Expand from given concepts to find related concepts and key verses.

    Returns:
        {
            "related_concepts": [
                {"id", "name", "sanskrit_term", "category",
                 "description", "relationship"}
            ],
            "key_verses": [
                {"verse_id", "chapter_number",
                 "verse_number", "relationship"}
            ],
            "graph_context": str  # formatted context for LLM
        }
    """
    if not concept_ids:
        return {"related_concepts": [], "key_verses": [], "graph_context": ""}

    conn = get_connection()

    # Find related concepts (1-hop via RELATES_TO)
    related_concepts = []
    for rel_type in ("RELATES_TO", "PREREQUISITE"):
        rows = _query_to_dicts(
            conn,
            f"MATCH (c:Concept)-[r:{rel_type}]-(related:Concept) "
            "WHERE c.id IN $ids AND NOT related.id IN $ids "
            "RETURN DISTINCT related.id AS id, related.name AS name, "
            "       related.sanskrit_term AS sanskrit_term, "
            "       related.category AS category, "
            "       related.`description` AS `description`, "
            "       related.description_hindi AS description_hindi, "
            "       c.name AS from_concept",
            {"ids": concept_ids},
        )
        for row in rows:
            row["relationship"] = rel_type
        related_concepts.extend(rows)

    # Deduplicate by id (keep first occurrence)
    seen_ids: set[str] = set()
    unique_related: list[dict] = []
    for rc in related_concepts:
        if rc["id"] not in seen_ids:
            seen_ids.add(rc["id"])
            unique_related.append(rc)
    related_concepts = unique_related

    # Find key verses that EXPLAIN the concepts (most relevant)
    key_verses = _query_to_dicts(
        conn,
        "MATCH (v:Verse)-[:EXPLAINS]->(c:Concept) "
        "WHERE c.id IN $ids "
        "RETURN v.verse_id AS verse_id, "
        "       v.chapter_number AS chapter_number, "
        "       v.verse_number AS verse_number, "
        "       c.name AS concept_name, "
        "       'explains' AS relationship "
        "ORDER BY v.chapter_number, v.verse_number",
        {"ids": concept_ids},
    )

    # Build a text context for the LLM
    graph_context = _format_graph_context(concept_ids, related_concepts, conn)

    return {
        "related_concepts": related_concepts,
        "key_verses": key_verses,
        "graph_context": graph_context,
    }


def get_concept_context(query: str) -> dict:
    """High-level function: given a user query, find relevant concepts
    and expand them to get graph context.

    Returns the same structure as expand_concepts, plus matched_concepts.
    """
    matched = _match_concepts_from_query(query)

    if not matched:
        return {
            "matched_concepts": [],
            "related_concepts": [],
            "key_verses": [],
            "graph_context": "",
        }

    concept_ids = [c["id"] for c in matched]
    expanded = expand_concepts(concept_ids)

    return {
        "matched_concepts": matched,
        **expanded,
    }


# English keyword aliases for concept matching
_CONCEPT_ALIASES: dict[str, list[str]] = {
    "atman": [
        "soul", "spirit", "consciousness", "आत्मा",
        "death", "dying", "afterlife", "immortal", "eternal",
        "body", "physical",
    ],
    "brahman": [
        "ultimate reality", "absolute", "supreme truth", "cosmic consciousness",
        "truth", "reality",
    ],
    "karma": ["action", "deed", "consequence", "cause and effect"],
    "dharma": [
        "duty", "righteousness", "moral", "ethics", "right action",
        "purpose", "sin", "wrong", "evil",
        "war", "battle", "fight", "conflict",
    ],
    "moksha": [
        "liberation", "freedom", "salvation", "enlightenment", "मुक्ति",
        "bliss",
    ],
    "bhakti": [
        "devotion", "devotee", "love of god", "worship",
        "love", "prayer",
    ],
    "bhakti_yoga": ["devotional", "path of devotion"],
    "jnana": [
        "knowledge", "wisdom", "understanding", "discernment",
        "confused", "confusion", "doubt",
        "teacher", "guru",
    ],
    "jnana_yoga": ["path of knowledge", "intellectual"],
    "dhyana": ["meditation", "meditate", "contemplation", "mindfulness"],
    "dhyana_yoga": ["path of meditation"],
    "yoga": ["union", "discipline"],
    "karma_yoga": [
        "selfless action", "path of action", "desireless action",
        "work", "career", "job",
    ],
    "nishkama_karma": [
        "desireless", "without attachment", "selfless service",
        "success", "failure", "result", "outcome",
    ],
    "maya": ["illusion", "delusion", "ignorance", "appearance"],
    "samsara": ["rebirth", "cycle of birth", "reincarnation", "transmigration"],
    "prakriti": ["material nature", "material world", "matter", "primal nature"],
    "purusha": ["supreme spirit", "cosmic self", "witness"],
    "gunas": [
        "qualities", "three qualities", "modes of nature",
        "food", "eating", "diet",
    ],
    "sattva": ["goodness", "purity", "harmony"],
    "rajas": ["passion", "activity", "restlessness"],
    "tamas": ["darkness", "inertia", "laziness"],
    "vairagya": [
        "detachment", "dispassion", "non-attachment", "letting go",
        "grief", "sorrow", "sadness", "suffering", "loss",
    ],
    "sthitaprajna": ["steady wisdom", "mental stability", "composure"],
    "surrender": ["surrender", "trust god", "समर्पण"],
    "shraddha": ["faith", "belief", "conviction"],
    "ahamkara": ["ego", "pride", "false self", "i-ness"],
    "buddhi": ["intellect", "intelligence", "reason"],
    "ishvara": ["god", "lord", "divine", "creator", "supreme being"],
    "vishvarupa": ["cosmic form", "universal form", "divine vision"],
    "tyaga": ["renunciation", "giving up", "sacrifice of results"],
    "sannyasa": ["monastic", "ascetic"],
    "daivi_sampat": [
        "divine qualities", "virtues", "noble qualities",
        "forgiveness", "kindness",
    ],
    "asuri_sampat": ["demonic qualities", "vices", "negative traits", "wicked"],
    "avatara": ["incarnation", "avatar", "divine descent"],
    "yajna": ["sacrifice", "offering", "ritual"],
    # New concepts
    "shanti": [
        "peace", "inner peace", "calm", "tranquil", "tranquility",
        "serenity", "peaceful", "शान्ति", "शांति",
    ],
    "kama": ["desire", "craving", "lust", "temptation", "काम"],
    "krodha": ["anger", "rage", "wrath", "angry", "furious", "hatred", "क्रोध"],
    "manas": [
        "mind", "mental", "thoughts", "thinking", "restless",
        "anxiety", "anxious", "worry", "worried", "stress", "stressed",
        "fear", "fearful", "nervous", "मन",
    ],
    "karuna": ["compassionate", "mercy", "empathy", "care", "करुणा"],
    "ahimsa": [
        "non-violence", "nonviolence", "harm", "violence", "hurt",
        "अहिंसा",
    ],
    "abhyasa": [
        "practice", "discipline", "habit", "consistent", "persistence",
        "अभ्यास",
    ],
    "samata": [
        "equanimity", "balance", "even-minded",
        "happiness", "joy", "happy", "समता",
    ],
    "prana": [
        "breath", "breathing", "pranayama", "life force", "vital",
        "प्राण",
    ],
}


def _match_concepts_from_query(query: str) -> list[dict]:
    """Match concepts from a user query using multiple strategies."""
    conn = get_connection()
    query_lower = query.lower()

    # Check alias matches (word-boundary aware for single-word ASCII aliases,
    # substring match for multi-word and non-ASCII/Devanagari aliases)
    alias_matched_ids = set()
    query_words = set(re.findall(r"\w+", query_lower))
    for concept_id, aliases in _CONCEPT_ALIASES.items():
        for alias in aliases:
            if " " in alias or not alias.isascii():
                if alias in query_lower:
                    alias_matched_ids.add(concept_id)
                    break
            else:
                if alias in query_words:
                    alias_matched_ids.add(concept_id)
                    break

    all_concepts = _query_to_dicts(
        conn,
        "MATCH (c:Concept) "
        "RETURN c.id AS id, c.name AS name, "
        "       c.sanskrit_term AS sanskrit_term, "
        "       c.category AS category, "
        "       c.`description` AS `description`, "
        "       c.description_hindi AS description_hindi",
    )

    matches = []
    for concept in all_concepts:
        name_lower = concept["name"].lower()
        id_lower = concept["id"].lower()
        sanskrit = concept["sanskrit_term"].lower()

        if (
            name_lower in query_lower
            or id_lower in query_lower
            or sanskrit in query_lower
            or concept["id"] in alias_matched_ids
        ):
            matches.append(concept)

    return matches


def _format_graph_context(
    concept_ids: list[str], related_concepts: list[dict], conn: kuzu.Connection
) -> str:
    """Format graph data into a text context for the LLM."""
    parts = []

    matched = _query_to_dicts(
        conn,
        "MATCH (c:Concept) "
        "WHERE c.id IN $ids "
        "RETURN c.name AS name, c.sanskrit_term AS sanskrit_term, "
        "       c.`description` AS `description`",
        {"ids": concept_ids},
    )

    parts.append("Relevant Gita concepts:")
    for row in matched:
        parts.append(f"- {row['name']} ({row['sanskrit_term']}): {row['description']}")

    if related_concepts:
        parts.append("\nRelated concepts:")
        seen: set[str] = set()
        for rc in related_concepts:
            if rc["id"] not in seen:
                seen.add(rc["id"])
                parts.append(f"- {rc['name']} ({rc['sanskrit_term']}): {rc['description']}")

    # Get who teaches these concepts
    teachings = _query_to_dicts(
        conn,
        "MATCH (p:Person)-[:TEACHES]->(c:Concept) "
        "WHERE c.id IN $ids "
        "RETURN DISTINCT p.name AS person, c.name AS concept",
        {"ids": concept_ids},
    )
    if teachings:
        parts.append("\nTeachings:")
        for t in teachings:
            parts.append(f"- {t['person']} teaches about {t['concept']}")

    return "\n".join(parts)
