# GitaAI — System Architecture

## Overview

GitaAI uses a **hybrid Knowledge Graph + RAG** architecture to answer questions about Vedic scriptures. This document captures the technical design, key decisions, and phased build plan.

## Why Hybrid (Graph + RAG)?

| Approach | Strengths | Weaknesses |
|----------|-----------|------------|
| **RAG only** | Good at finding relevant text chunks | Misses relationships between concepts; flat retrieval |
| **Knowledge Graph only** | Great at relationships and reasoning paths | Can't do open-ended semantic search over full text |
| **Hybrid** | Semantic search + relational reasoning | More complex to build |

Vedic literature is inherently **relational** — concepts build on each other across texts, multiple schools interpret the same verse differently, and understanding context requires traversing connections. A pure vector search misses this structure. The hybrid approach lets us retrieve relevant text (RAG) AND traverse concept relationships (Graph).

## System Architecture

```
                                    +-----------------+
                                    |   Next.js Web   |
                                    |   (Chat UI)     |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    |  Next.js API    |
                                    |  Routes         |
                                    +--------+--------+
                                             |
                              +--------------+--------------+
                              |                             |
                    +---------v---------+         +---------v---------+
                    |  FastAPI          |         |  PostgreSQL       |
                    |  (ML Pipeline)    |         |  (Users, Sessions)|
                    +---------+---------+         +-------------------+
                              |
               +--------------+--------------+
               |              |              |
     +---------v---+  +------v------+  +----v--------+
     |  ChromaDB   |  |   Kùzu      |  |  Claude API |
     |  (Vectors)  |  |   (Graph)   |  |  (LLM)      |
     +-------------+  +-------------+  +-------------+
```

## Query Flow

```
1. User asks: "How does Krishna explain the nature of the self?"

2. INTENT CLASSIFICATION
   → Determine query type: factual, conceptual, comparative, exploratory

3. PARALLEL RETRIEVAL
   ├── Vector Search (Weaviate)
   │   → Top-k verse chunks semantically similar to the query
   │   → Returns: BG 2.20, BG 2.17, BG 2.23, KU 1.2.18...
   │
   └── Graph Traversal (Kùzu)
       → Start from entities in query: [Krishna, Self/Atman]
       → Traverse: Krishna -[TEACHES]-> Atman
       → Expand: Atman -[RELATES_TO]-> Brahman, Moksha
       → Cross-ref: Atman -[ELABORATED_IN]-> Katha Upanishad
       → Schools: Shankaracharya -[INTERPRETS]-> BG 2.20 (Advaita view)
       → Returns: concept map + related verses + interpretations

4. CONTEXT ASSEMBLY
   → Merge vector results + graph context
   → Deduplicate, rank by relevance
   → Format with verse numbers, Sanskrit, translations

5. LLM GENERATION (Claude)
   → System prompt: "You are a scholar of Vedic philosophy..."
   → Context: assembled verses + concept relationships
   → User query
   → Generate answer with inline citations [BG 2.20]

6. RESPONSE
   → Streamed to user with:
     - Answer text with verse citations
     - Expandable verse cards (Sanskrit + translation)
     - Related concepts sidebar
     - "Explore further" links
```

## Data Model

### Knowledge Graph Schema (Kùzu)

#### Nodes

| Label | Properties | Description |
|-------|-----------|-------------|
| `Scripture` | name, tradition, language, period | A sacred text (e.g., Bhagavad Gita) |
| `Chapter` | number, name, sanskrit_name, theme | A chapter/section within a scripture |
| `Verse` | number, sanskrit, transliteration, translation, translator, commentary | An individual verse |
| `Concept` | name, sanskrit_term, description, category | A philosophical concept (e.g., Dharma, Karma) |
| `Person` | name, role, description | Historical or mythological figure |
| `School` | name, founder, core_teaching | School of philosophy (e.g., Advaita) |
| `Commentary` | title, author, tradition, period | A commentary on a text |

#### Relationships

| Type | From → To | Description |
|------|-----------|-------------|
| `PART_OF` | Chapter → Scripture | Chapter belongs to scripture |
| `PART_OF` | Verse → Chapter | Verse belongs to chapter |
| `TEACHES` | Person → Concept | Person teaches this concept |
| `MENTIONS` | Verse → Concept | Verse discusses this concept |
| `EXPLAINS` | Verse → Concept | Verse is a key explanation of this concept |
| `RELATES_TO` | Concept → Concept | Concepts are related |
| `PREREQUISITE` | Concept → Concept | Understanding A helps understand B |
| `INTERPRETS` | Commentary → Verse | Commentary interprets a verse |
| `BELONGS_TO` | Commentary → School | Commentary is from this school |
| `SPOKEN_BY` | Verse → Person | Who speaks this verse |
| `ELABORATED_IN` | Concept → Scripture | Concept is further explained in another text |

### Vector Store Schema (Weaviate)

```
Class: VerseChunk
  - verse_id: string (e.g., "BG_2_47")
  - scripture: string
  - chapter: int
  - verse_number: string
  - sanskrit: text
  - transliteration: text
  - translation: text
  - translator: string
  - commentary: text (optional)
  - concepts: string[] (linked concept names)
  - embedding: vector
```

## Key Design Decisions

### Why Claude API (not self-hosted LLM)?
- Superior instruction following and citation accuracy
- Long context window for multi-verse answers
- Cost-effective for an MVP — no GPU infrastructure needed
- Can switch to self-hosted later if needed

### Why Kùzu (not Neo4j or a simpler graph)?
- Embedded database — no server, no Docker, no auth needed
- Cypher-compatible query language (easy to learn, well-documented)
- Zero infrastructure cost — just a local directory
- Fast in-process queries with no network overhead
- Schema-first design enforces data integrity

### Why Weaviate (not Pinecone/ChromaDB)?
- Hybrid search (vector + keyword) built in
- Self-hostable (important for open source)
- Good filtering on metadata (scripture, chapter, translator)
- ChromaDB is a viable lightweight alternative for Phase 1

### Why monorepo (not separate repos)?
- Shared types between frontend and pipeline
- Atomic changes across stack
- Simpler CI/CD
- Single source of truth for docs

## Phased Build Plan

### Phase 1 — MVP (RAG Chat)
**Goal:** Working chat that answers Gita questions with verse citations.

- [ ] Set up Next.js frontend with chat UI
- [ ] Set up FastAPI backend
- [ ] Ingest Bhagavad Gita (all 700 verses, 1-2 translations)
- [ ] Generate embeddings and store in ChromaDB (lighter than Weaviate for MVP)
- [ ] Basic RAG pipeline: embed query → retrieve top-k → Claude generates answer
- [ ] Stream responses to frontend
- [ ] Display verse citations with expandable cards
- [ ] Deploy MVP

**Out of scope:** Knowledge graph, multi-text, auth, analytics.

### Phase 2 — Knowledge Graph Integration
**Goal:** Richer answers that understand concept relationships.

- [ ] Design and seed Kùzu graph with Gita concepts/relationships
- [ ] Build graph traversal module
- [ ] Hybrid retrieval: vector search + graph context
- [ ] Add Upanishads and Yoga Sutras to corpus
- [ ] Cross-text references in answers
- [ ] "Related concepts" sidebar in UI
- [ ] Migrate from ChromaDB to Weaviate (if scale demands)

### Phase 3 — Multi-Perspective & Visualization
**Goal:** Show diverse interpretations and let users explore the knowledge graph.

- [ ] Add commentaries from multiple Acharyas
- [ ] Multi-perspective answer format ("Shankaracharya says... Ramanuja says...")
- [ ] Interactive graph visualization (D3.js / vis.js)
- [ ] Learning paths: guided journeys through concepts
- [ ] User accounts and saved conversations
- [ ] Analytics dashboard

### Phase 4 — Community & Scale
**Goal:** Community-driven growth and multilingual support.

- [ ] Community annotations and corrections
- [ ] Hindi/Sanskrit UI localization
- [ ] Mobile-responsive / PWA
- [ ] API for third-party integrations
- [ ] Self-hosted LLM option for offline/privacy use
- [ ] Expand to Puranas, Ramayana, Mahabharata

## Performance Targets

| Metric | Target |
|--------|--------|
| Time to first token | < 1.5s |
| Full response time | < 8s (700-word answer) |
| Vector search latency | < 200ms |
| Graph query latency | < 300ms |
| Concurrent users | 100+ (Phase 1), 1000+ (Phase 3) |

## Cost Considerations

- Claude API: ~$0.01-0.05 per query (depending on context length)
- Kùzu: Free and embedded — no hosting cost
- Weaviate: Self-hosted (free) or Weaviate Cloud (free tier available)
- Hosting: Vercel free tier (frontend), Railway/Fly.io (backend)
- Embeddings: ~$0.001 per 1000 tokens (one-time cost for corpus)
