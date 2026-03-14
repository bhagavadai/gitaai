"""Graph traversal for concept expansion and relationship discovery."""

from __future__ import annotations

import re
from typing import Optional

from neo4j import GraphDatabase

from ..config import settings

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


def find_concepts_for_query(query: str) -> list[dict]:
    """Find concepts whose names or Sanskrit terms appear in the query.

    Uses case-insensitive matching against concept names, Sanskrit terms,
    and common variations.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """MATCH (c:Concept)
               WHERE toLower(c.name) CONTAINS toLower($query)
                  OR toLower(c.sanskrit_term) CONTAINS toLower($query)
                  OR toLower(c.id) CONTAINS toLower($query)
               RETURN c.id AS id, c.name AS name, c.sanskrit_term AS sanskrit_term,
                      c.category AS category, c.description AS description,
                      c.description_hindi AS description_hindi""",
            query=query,
        )
        return [dict(record) for record in result]


def expand_concepts(concept_ids: list[str], depth: int = 1) -> dict:
    """Expand from given concepts to find related concepts and key verses.

    Returns:
        {
            "related_concepts": [{"id", "name", "sanskrit_term", "category", "description", "relationship"}],
            "key_verses": [{"verse_id", "chapter_number", "verse_number", "relationship"}],
            "graph_context": str  # formatted context for LLM
        }
    """
    if not concept_ids:
        return {"related_concepts": [], "key_verses": [], "graph_context": ""}

    driver = get_driver()
    with driver.session() as session:
        # Find related concepts (1-hop)
        related_result = session.run(
            """UNWIND $ids AS cid
               MATCH (c:Concept {id: cid})-[r:RELATES_TO|PREREQUISITE]-(related:Concept)
               WHERE NOT related.id IN $ids
               RETURN DISTINCT related.id AS id, related.name AS name,
                      related.sanskrit_term AS sanskrit_term,
                      related.category AS category,
                      related.description AS description,
                      related.description_hindi AS description_hindi,
                      type(r) AS relationship,
                      c.name AS from_concept""",
            ids=concept_ids,
        )
        related_concepts = [dict(r) for r in related_result]

        # Find key verses that EXPLAIN the concepts (most relevant)
        explains_result = session.run(
            """UNWIND $ids AS cid
               MATCH (v:Verse)-[:EXPLAINS]->(c:Concept {id: cid})
               RETURN DISTINCT v.verse_id AS verse_id,
                      v.chapter_number AS chapter_number,
                      v.verse_number AS verse_number,
                      c.name AS concept_name,
                      'explains' AS relationship
               ORDER BY v.chapter_number, v.verse_number""",
            ids=concept_ids,
        )
        key_verses = [dict(r) for r in explains_result]

        # Build a text context for the LLM
        graph_context = _format_graph_context(concept_ids, related_concepts, session)

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
    # Try to match concepts from the query
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
    "atman": ["soul", "self", "spirit", "consciousness", "आत्मा"],
    "brahman": ["ultimate reality", "absolute", "supreme truth", "cosmic consciousness"],
    "karma": ["action", "deed", "consequence", "cause and effect"],
    "dharma": ["duty", "righteousness", "moral", "ethics", "right action"],
    "moksha": ["liberation", "freedom", "salvation", "enlightenment", "मुक्ति"],
    "bhakti": ["devotion", "devotee", "love of god", "worship"],
    "bhakti_yoga": ["devotional", "path of devotion"],
    "jnana": ["knowledge", "wisdom", "understanding", "discernment"],
    "jnana_yoga": ["path of knowledge", "intellectual"],
    "dhyana": ["meditation", "meditate", "contemplation", "mindfulness"],
    "dhyana_yoga": ["path of meditation"],
    "yoga": ["union", "discipline"],
    "karma_yoga": ["selfless action", "path of action", "desireless action"],
    "nishkama_karma": ["desireless", "without attachment", "selfless service"],
    "maya": ["illusion", "delusion", "ignorance", "appearance"],
    "samsara": ["rebirth", "cycle of birth", "reincarnation", "transmigration"],
    "prakriti": ["material nature", "material world", "matter", "primal nature"],
    "purusha": ["supreme spirit", "cosmic self", "witness"],
    "gunas": ["qualities", "three qualities", "modes of nature"],
    "sattva": ["goodness", "purity", "harmony", "light"],
    "rajas": ["passion", "activity", "restlessness", "desire"],
    "tamas": ["darkness", "inertia", "laziness", "delusion"],
    "vairagya": ["detachment", "dispassion", "non-attachment", "letting go"],
    "sthitaprajna": ["steady wisdom", "equanimity", "mental stability", "composure"],
    "surrender": ["surrender", "give up", "let go", "trust god", "समर्पण"],
    "shraddha": ["faith", "trust", "belief", "conviction"],
    "ahamkara": ["ego", "pride", "false self", "i-ness"],
    "buddhi": ["intellect", "intelligence", "discernment", "reason"],
    "ishvara": ["god", "lord", "supreme", "divine"],
    "vishvarupa": ["cosmic form", "universal form", "divine vision"],
    "tyaga": ["renunciation", "giving up", "sacrifice of results"],
    "sannyasa": ["renunciation", "monastic", "ascetic"],
    "daivi_sampat": ["divine qualities", "virtues", "noble qualities"],
    "asuri_sampat": ["demonic qualities", "vices", "negative traits"],
    "avatara": ["incarnation", "avatar", "divine descent"],
    "yajna": ["sacrifice", "offering", "ritual", "selfless service"],
}


def _match_concepts_from_query(query: str) -> list[dict]:
    """Match concepts from a user query using multiple strategies."""
    driver = get_driver()
    query_lower = query.lower()

    # Check alias matches (word-boundary aware for single-word aliases)
    alias_matched_ids = set()
    query_words = set(re.findall(r"\w+", query_lower))
    for concept_id, aliases in _CONCEPT_ALIASES.items():
        for alias in aliases:
            if " " in alias:
                # Multi-word aliases: substring match is fine
                if alias in query_lower:
                    alias_matched_ids.add(concept_id)
                    break
            else:
                # Single-word aliases: must be a whole word
                if alias in query_words:
                    alias_matched_ids.add(concept_id)
                    break

    with driver.session() as session:
        result = session.run(
            """MATCH (c:Concept)
               RETURN c.id AS id, c.name AS name,
                      c.sanskrit_term AS sanskrit_term,
                      c.category AS category,
                      c.description AS description,
                      c.description_hindi AS description_hindi"""
        )

        matches = []
        for record in result:
            concept = dict(record)
            name_lower = concept["name"].lower()
            id_lower = concept["id"].lower()
            sanskrit = concept["sanskrit_term"].lower()

            # Exact or substring match in query
            if (
                name_lower in query_lower
                or id_lower in query_lower
                or sanskrit in query_lower
                or concept["id"] in alias_matched_ids
            ):
                matches.append(concept)

    return matches


def _format_graph_context(
    concept_ids: list[str], related_concepts: list[dict], session
) -> str:
    """Format graph data into a text context for the LLM."""
    parts = []

    # Get the matched concepts
    result = session.run(
        """UNWIND $ids AS cid
           MATCH (c:Concept {id: cid})
           RETURN c.name AS name, c.sanskrit_term AS sanskrit_term,
                  c.description AS description""",
        ids=concept_ids,
    )

    parts.append("Relevant Gita concepts:")
    for record in result:
        parts.append(
            f"- {record['name']} ({record['sanskrit_term']}): {record['description']}"
        )

    if related_concepts:
        parts.append("\nRelated concepts:")
        seen = set()
        for rc in related_concepts:
            if rc["id"] not in seen:
                seen.add(rc["id"])
                parts.append(
                    f"- {rc['name']} ({rc['sanskrit_term']}): {rc['description']}"
                )

    # Get who teaches these concepts
    result = session.run(
        """UNWIND $ids AS cid
           MATCH (p:Person)-[:TEACHES]->(c:Concept {id: cid})
           RETURN DISTINCT p.name AS person, c.name AS concept""",
        ids=concept_ids,
    )
    teachings = [dict(r) for r in result]
    if teachings:
        parts.append("\nTeachings:")
        for t in teachings:
            parts.append(f"- {t['person']} teaches about {t['concept']}")

    return "\n".join(parts)
