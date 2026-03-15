"""Seed the Neo4j knowledge graph with Gita data.

Creates nodes for: Scripture, Chapter, Verse, Concept, Person
Creates relationships: PART_OF, MENTIONS, EXPLAINS, RELATES_TO,
                       PREREQUISITE, TEACHES, ASKS_ABOUT, SPOKEN_BY
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from neo4j import GraphDatabase

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


def seed(uri: str, user: str, password: str):
    """Seed the Neo4j graph with Gita knowledge graph data."""
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

    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # Clear existing data
        logger.info("Clearing existing graph data...")
        session.run("MATCH (n) DETACH DELETE n")

        # Create constraints for performance
        logger.info("Creating constraints...")
        for label, prop in [
            ("Scripture", "name"),
            ("Chapter", "number"),
            ("Verse", "verse_id"),
            ("Concept", "id"),
            ("Person", "id"),
        ]:
            session.run(
                f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
            )

        # Scripture node
        logger.info("Creating Scripture node...")
        session.run(
            """CREATE (:Scripture {
                name: 'Bhagavad Gita', sanskrit_name: $sn,
                tradition: 'Hindu', language: 'Sanskrit',
                chapters: 18, verses: 701
            })""",
            sn="भगवद्गीता",
        )

        # Chapter nodes
        logger.info("Creating %d Chapter nodes...", len(chapters))
        for ch in chapters:
            session.run(
                """CREATE (c:Chapter {
                    number: $num, name: $name, sanskrit_name: $sn,
                    name_meaning: $meaning, verses_count: $vc,
                    summary: $summary
                })""",
                num=ch["chapter_number"],
                name=ch["name_translation"],
                sn=ch["name_sanskrit"],
                meaning=ch["name_meaning"],
                vc=ch["verses_count"],
                summary=ch.get("summary", ""),
            )
            session.run(
                """MATCH (ch:Chapter {number: $num}), (s:Scripture {name: 'Bhagavad Gita'})
                   CREATE (ch)-[:PART_OF]->(s)""",
                num=ch["chapter_number"],
            )

        # Verse nodes
        logger.info("Creating %d Verse nodes...", len(verses))
        batch_size = 100
        for i in range(0, len(verses), batch_size):
            batch = verses[i : i + batch_size]
            for v in batch:
                session.run(
                    """CREATE (v:Verse {
                        verse_id: $vid, chapter_number: $ch, verse_number: $vn,
                        sanskrit: $sk, transliteration: $tr
                    })""",
                    vid=v["id"],
                    ch=v["chapter_number"],
                    vn=v["verse_number"],
                    sk=v["sanskrit"],
                    tr=v["transliteration"],
                )
                session.run(
                    """MATCH (v:Verse {verse_id: $vid}), (ch:Chapter {number: $ch})
                       CREATE (v)-[:PART_OF]->(ch)""",
                    vid=v["id"],
                    ch=v["chapter_number"],
                )
            logger.info("  Inserted verses %d-%d", i + 1, min(i + batch_size, len(verses)))

        # Concept nodes
        logger.info("Creating %d Concept nodes...", len(concepts))
        for c in concepts:
            session.run(
                """CREATE (:Concept {
                    id: $id, name: $name, sanskrit_term: $st,
                    category: $cat, description: $desc, description_hindi: $dh
                })""",
                id=c["id"],
                name=c["name"],
                st=c["sanskrit_term"],
                cat=c["category"],
                desc=c["description"],
                dh=c["description_hindi"],
            )

        # Person nodes
        logger.info("Creating %d Person nodes...", len(persons))
        for p in persons:
            session.run(
                """CREATE (:Person {
                    id: $id, name: $name, sanskrit_name: $sn,
                    role: $role, description: $desc, description_hindi: $dh
                })""",
                id=p["id"],
                name=p["name"],
                sn=p["sanskrit_name"],
                role=p["role"],
                desc=p["description"],
                dh=p["description_hindi"],
            )

        # Concept-Verse relationships (EXPLAINS and MENTIONS)
        logger.info("Creating Concept-Verse relationships...")
        concept_count = 0
        for concept_id, mappings in concept_verse_map.items():
            if concept_id.startswith("_"):
                continue
            for verse_id in mappings.get("explains", []):
                session.run(
                    """MATCH (v:Verse {verse_id: $vid}), (c:Concept {id: $cid})
                       CREATE (v)-[:EXPLAINS]->(c)""",
                    vid=verse_id,
                    cid=concept_id,
                )
                concept_count += 1
            for verse_id in mappings.get("mentions", []):
                session.run(
                    """MATCH (v:Verse {verse_id: $vid}), (c:Concept {id: $cid})
                       CREATE (v)-[:MENTIONS]->(c)""",
                    vid=verse_id,
                    cid=concept_id,
                )
                concept_count += 1
        logger.info("  Created %d concept-verse edges", concept_count)

        # Concept-Concept relationships
        logger.info("Creating Concept-Concept relationships...")
        for rel in concept_relationships:
            session.run(
                f"""MATCH (a:Concept {{id: $from_id}}), (b:Concept {{id: $to_id}})
                    CREATE (a)-[:{rel["type"]}]->(b)""",
                from_id=rel["from"],
                to_id=rel["to"],
            )
        logger.info("  Created %d concept-concept edges", len(concept_relationships))

        # Person-Concept relationships
        logger.info("Creating Person-Concept relationships...")
        for pcm in person_concept_map:
            session.run(
                f"""MATCH (p:Person {{id: $pid}}), (c:Concept {{id: $cid}})
                    CREATE (p)-[:{pcm["type"]}]->(c)""",
                pid=pcm["person"],
                cid=pcm["concept"],
            )
        logger.info("  Created %d person-concept edges", len(person_concept_map))

        # Speaker relationships (SPOKEN_BY)
        logger.info("Creating speaker relationships...")
        speaker_count = 0
        for verse_id, speaker_id in speaker_map.items():
            session.run(
                """MATCH (v:Verse {verse_id: $vid}), (p:Person {id: $pid})
                   CREATE (v)-[:SPOKEN_BY]->(p)""",
                vid=verse_id,
                pid=speaker_id,
            )
            speaker_count += 1
        logger.info("  Created %d speaker edges", speaker_count)

        # Summary
        result = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
        )
        logger.info("Graph summary:")
        for record in result:
            logger.info("  %s: %d", record["label"], record["count"])

        result = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
        )
        logger.info("Relationship summary:")
        for record in result:
            logger.info("  %s: %d", record["type"], record["count"])

    driver.close()
    logger.info("Done! Knowledge graph seeded successfully.")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.config import settings

    seed(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
