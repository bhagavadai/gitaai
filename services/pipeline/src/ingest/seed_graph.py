"""Seed the Kùzu knowledge graph with Gita data.

Creates node tables: Scripture, Chapter, Verse, Concept, Person
Creates rel tables: PART_OF, MENTIONS, EXPLAINS, RELATES_TO,
                    PREREQUISITE, TEACHES, ASKS_ABOUT, SPOKEN_BY
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import kuzu

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
SEED_DIR = DATA_DIR / "seed"

SPEAKER_PATTERNS = {
    "krishna": [
        "श्रीभगवानुवाच",
        "श्री भगवानुवाच",
    ],
    "arjuna": [
        "अर्जुन उवाच",
        "अर्जुनउवाच",
    ],
    "sanjaya": [
        "सञ्जय उवाच",
        "संजय उवाच",
        "संजयउवाच",
    ],
    "dhritarashtra": [
        "धृतराष्ट्र उवाच",
    ],
}


def detect_speakers(verses: list[dict]) -> dict[str, str]:
    """Detect who speaks each verse from Sanskrit text patterns."""
    speaker_map = {}
    current_speaker = "sanjaya"

    for v in verses:
        sanskrit = v["sanskrit"]
        detected = None
        for speaker, patterns in SPEAKER_PATTERNS.items():
            for p in patterns:
                if p in sanskrit:
                    detected = speaker
                    break
            if detected:
                break
        if detected:
            current_speaker = detected
        speaker_map[v["id"]] = current_speaker

    return speaker_map


def load_seed_data():
    """Load all seed data files."""
    with open(PROCESSED_DIR / "chapters.json", encoding="utf-8") as f:
        chapters = json.load(f)
    with open(PROCESSED_DIR / "verses.json", encoding="utf-8") as f:
        verses = json.load(f)
    with open(SEED_DIR / "concepts.json", encoding="utf-8") as f:
        concepts = json.load(f)
    with open(SEED_DIR / "concept_verse_map.json", encoding="utf-8") as f:
        concept_verse_map = json.load(f)
    with open(SEED_DIR / "concept_relationships.json", encoding="utf-8") as f:
        concept_relationships = json.load(f)
    with open(SEED_DIR / "persons.json", encoding="utf-8") as f:
        persons = json.load(f)
    with open(SEED_DIR / "person_concept_map.json", encoding="utf-8") as f:
        person_concept_map = json.load(f)
    return (
        chapters,
        verses,
        concepts,
        concept_verse_map,
        concept_relationships,
        persons,
        person_concept_map,
    )


def _create_schema(conn: kuzu.Connection):
    """Create all node and relationship tables."""
    logger.info("Creating schema...")

    # Node tables
    conn.execute("""
        CREATE NODE TABLE Scripture (
            name STRING,
            sanskrit_name STRING,
            tradition STRING,
            language STRING,
            chapters INT64,
            verses INT64,
            PRIMARY KEY (name)
        )
    """)
    conn.execute("""
        CREATE NODE TABLE Chapter (
            number INT64,
            name STRING,
            sanskrit_name STRING,
            name_meaning STRING,
            verses_count INT64,
            summary STRING,
            PRIMARY KEY (number)
        )
    """)
    conn.execute("""
        CREATE NODE TABLE Verse (
            verse_id STRING,
            chapter_number INT64,
            verse_number INT64,
            sanskrit STRING,
            transliteration STRING,
            PRIMARY KEY (verse_id)
        )
    """)
    conn.execute("""
        CREATE NODE TABLE Concept (
            id STRING,
            name STRING,
            sanskrit_term STRING,
            category STRING,
            `description` STRING,
            description_hindi STRING,
            PRIMARY KEY (id)
        )
    """)
    conn.execute("""
        CREATE NODE TABLE Person (
            id STRING,
            name STRING,
            sanskrit_name STRING,
            role STRING,
            `description` STRING,
            description_hindi STRING,
            PRIMARY KEY (id)
        )
    """)

    # Relationship tables
    conn.execute("CREATE REL TABLE ChapterPartOf (FROM Chapter TO Scripture)")
    conn.execute("CREATE REL TABLE VersePartOf (FROM Verse TO Chapter)")
    conn.execute("CREATE REL TABLE EXPLAINS (FROM Verse TO Concept)")
    conn.execute("CREATE REL TABLE MENTIONS (FROM Verse TO Concept)")
    conn.execute("CREATE REL TABLE RELATES_TO (FROM Concept TO Concept)")
    conn.execute("CREATE REL TABLE PREREQUISITE (FROM Concept TO Concept)")
    conn.execute("CREATE REL TABLE TEACHES (FROM Person TO Concept)")
    conn.execute("CREATE REL TABLE ASKS_ABOUT (FROM Person TO Concept)")
    conn.execute("CREATE REL TABLE SPOKEN_BY (FROM Verse TO Person)")


def seed(db_path: str):
    """Seed the Kùzu graph with Gita knowledge graph data."""
    (
        chapters,
        verses,
        concepts,
        concept_verse_map,
        concept_relationships,
        persons,
        person_concept_map,
    ) = load_seed_data()
    speaker_map = detect_speakers(verses)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # Drop existing tables (clean slate — rels first, then nodes)
    logger.info("Clearing existing graph data...")
    tables_df = conn.execute("CALL show_tables() RETURN *").get_as_df()
    if not tables_df.empty:
        for t_type in ("REL", "NODE"):
            for table in tables_df[tables_df["type"] == t_type]["name"].tolist():
                conn.execute(f"DROP TABLE {table}")

    _create_schema(conn)

    # Scripture node
    logger.info("Creating Scripture node...")
    conn.execute(
        "CREATE (:Scripture {name: $name, sanskrit_name: $sn, "
        "tradition: $tradition, language: $lang, chapters: $ch, verses: $v})",
        parameters={
            "name": "Bhagavad Gita",
            "sn": "भगवद्गीता",
            "tradition": "Hindu",
            "lang": "Sanskrit",
            "ch": 18,
            "v": 701,
        },
    )

    # Chapter nodes
    logger.info("Creating %d Chapter nodes...", len(chapters))
    for ch in chapters:
        conn.execute(
            "CREATE (:Chapter {number: $num, name: $name, sanskrit_name: $sn, "
            "name_meaning: $meaning, verses_count: $vc, summary: $summary})",
            parameters={
                "num": ch["chapter_number"],
                "name": ch["name_translation"],
                "sn": ch["name_sanskrit"],
                "meaning": ch["name_meaning"],
                "vc": ch["verses_count"],
                "summary": ch.get("summary", ""),
            },
        )
        conn.execute(
            "MATCH (ch:Chapter {number: $num}), (s:Scripture {name: 'Bhagavad Gita'}) "
            "CREATE (ch)-[:ChapterPartOf]->(s)",
            parameters={"num": ch["chapter_number"]},
        )

    # Verse nodes
    logger.info("Creating %d Verse nodes...", len(verses))
    for i, v in enumerate(verses):
        conn.execute(
            "CREATE (:Verse {verse_id: $vid, chapter_number: $ch, "
            "verse_number: $vn, sanskrit: $sk, transliteration: $tr})",
            parameters={
                "vid": v["id"],
                "ch": v["chapter_number"],
                "vn": v["verse_number"],
                "sk": v["sanskrit"],
                "tr": v["transliteration"],
            },
        )
        conn.execute(
            "MATCH (v:Verse {verse_id: $vid}), (ch:Chapter {number: $ch}) "
            "CREATE (v)-[:VersePartOf]->(ch)",
            parameters={"vid": v["id"], "ch": v["chapter_number"]},
        )
        if (i + 1) % 100 == 0:
            logger.info("  Inserted verses %d/%d", i + 1, len(verses))
    logger.info("  Inserted all %d verses", len(verses))

    # Concept nodes
    logger.info("Creating %d Concept nodes...", len(concepts))
    for c in concepts:
        conn.execute(
            "CREATE (:Concept {id: $id, name: $name, sanskrit_term: $st, "
            "category: $cat, `description`: $desc_val, description_hindi: $dh})",
            parameters={
                "id": c["id"],
                "name": c["name"],
                "st": c["sanskrit_term"],
                "cat": c["category"],
                "desc_val": c["description"],
                "dh": c["description_hindi"],
            },
        )

    # Person nodes
    logger.info("Creating %d Person nodes...", len(persons))
    for p in persons:
        conn.execute(
            "CREATE (:Person {id: $id, name: $name, sanskrit_name: $sn, "
            "role: $role, `description`: $desc_val, description_hindi: $dh})",
            parameters={
                "id": p["id"],
                "name": p["name"],
                "sn": p["sanskrit_name"],
                "role": p["role"],
                "desc_val": p["description"],
                "dh": p["description_hindi"],
            },
        )

    # Concept-Verse relationships (EXPLAINS and MENTIONS)
    logger.info("Creating Concept-Verse relationships...")
    edge_count = 0
    for concept_id, mappings in concept_verse_map.items():
        if concept_id.startswith("_"):
            continue
        for verse_id in mappings.get("explains", []):
            conn.execute(
                "MATCH (v:Verse {verse_id: $vid}), (c:Concept {id: $cid}) "
                "CREATE (v)-[:EXPLAINS]->(c)",
                parameters={"vid": verse_id, "cid": concept_id},
            )
            edge_count += 1
        for verse_id in mappings.get("mentions", []):
            conn.execute(
                "MATCH (v:Verse {verse_id: $vid}), (c:Concept {id: $cid}) "
                "CREATE (v)-[:MENTIONS]->(c)",
                parameters={"vid": verse_id, "cid": concept_id},
            )
            edge_count += 1
    logger.info("  Created %d concept-verse edges", edge_count)

    # Concept-Concept relationships
    logger.info("Creating Concept-Concept relationships...")
    for rel in concept_relationships:
        rel_type = rel["type"]
        if rel_type not in ("RELATES_TO", "PREREQUISITE"):
            logger.warning("  Skipping unknown relationship type: %s", rel_type)
            continue
        conn.execute(
            f"MATCH (a:Concept {{id: $from_id}}), (b:Concept {{id: $to_id}}) "
            f"CREATE (a)-[:{rel_type}]->(b)",
            parameters={"from_id": rel["from"], "to_id": rel["to"]},
        )
    logger.info("  Created %d concept-concept edges", len(concept_relationships))

    # Person-Concept relationships
    logger.info("Creating Person-Concept relationships...")
    for pcm in person_concept_map:
        rel_type = pcm["type"]
        if rel_type not in ("TEACHES", "ASKS_ABOUT"):
            logger.warning("  Skipping unknown relationship type: %s", rel_type)
            continue
        conn.execute(
            f"MATCH (p:Person {{id: $pid}}), (c:Concept {{id: $cid}}) "
            f"CREATE (p)-[:{rel_type}]->(c)",
            parameters={"pid": pcm["person"], "cid": pcm["concept"]},
        )
    logger.info("  Created %d person-concept edges", len(person_concept_map))

    # Speaker relationships (SPOKEN_BY)
    logger.info("Creating speaker relationships...")
    speaker_count = 0
    for verse_id, speaker_id in speaker_map.items():
        conn.execute(
            "MATCH (v:Verse {verse_id: $vid}), (p:Person {id: $pid}) CREATE (v)-[:SPOKEN_BY]->(p)",
            parameters={"vid": verse_id, "pid": speaker_id},
        )
        speaker_count += 1
    logger.info("  Created %d speaker edges", speaker_count)

    # Summary
    result = conn.execute("CALL show_tables() RETURN name, type, comment").get_as_df()
    node_tables = result[result["type"].str.upper() == "NODE"]["name"].tolist()
    logger.info("Graph summary:")
    for table_name in node_tables:
        count_result = conn.execute(f"MATCH (n:{table_name}) RETURN count(n) AS cnt").get_as_df()
        logger.info("  %s: %d", table_name, count_result["cnt"][0])

    logger.info("Done! Knowledge graph seeded successfully.")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.config import settings

    seed(settings.kuzu_db_dir)
