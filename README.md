# GitaAI

An open-source AI chat interface grounded in the Bhagavad Gita and Vedic scriptures. Ask questions about dharma, karma, yoga, and the deeper meanings of life — and get answers rooted in actual verses with proper citations.

## Vision

Most AI chatbots treat ancient texts as flat data. GitaAI is different:

- **Knowledge Graph + RAG hybrid** — understands the *relationships* between concepts, scriptures, and philosophical schools, not just keyword matches
- **Faithful to the source** — every answer cites specific verses with original Sanskrit, transliteration, and translation
- **Multi-perspective** — presents interpretations from different schools (Advaita, Dvaita, Vishishtadvaita) rather than picking one
- **Learning paths** — guides users through interconnected concepts across texts

## Texts Covered

**Phase 1 (MVP):**
- Bhagavad Gita (18 chapters, 700 verses)

**Phase 2+:**
- Principal Upanishads (Isha, Kena, Katha, Mundaka, Mandukya, etc.)
- Patanjali's Yoga Sutras
- Brahma Sutras
- Select hymns from the Vedas

**Future:**
- Ramayana and Mahabharata (key philosophical sections)
- Puranas (select stories and teachings)
- Commentaries by major Acharyas

## Architecture

GitaAI uses a **hybrid Knowledge Graph + RAG** architecture:

```
User Question
      |
      +---> Vector Search (RAG)         --> Relevant verses & passages
      |
      +---> Knowledge Graph (Neo4j)     --> Related concepts, cross-references,
      |                                      schools of thought, lineage
      |
      +---> LLM (Claude)               --> Synthesizes a grounded, cited answer
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full technical design.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (TypeScript, Tailwind CSS) |
| Backend | Next.js API routes + FastAPI (Python) |
| LLM | Claude API (Anthropic) |
| Knowledge Graph | Neo4j |
| Vector Store | Weaviate / ChromaDB |
| Embeddings | Voyage AI |
| Database | PostgreSQL |

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- pnpm
- Docker (for Neo4j, PostgreSQL in development)

### Setup

```bash
# Clone the repository
git clone https://github.com/agni21/gitaai.git
cd gitaai

# Copy environment variables
cp .env.example .env
# Fill in your API keys in .env

# Install frontend dependencies
cd apps/web && pnpm install

# Install Python dependencies
cd ../../services/pipeline && pip install -e ".[dev]"

# Start development services (Neo4j, PostgreSQL)
docker compose up -d

# Run the frontend
cd ../../apps/web && pnpm dev

# Run the Python API (in another terminal)
cd services/pipeline && uvicorn src.api.main:app --reload
```

### Environment Variables

See [.env.example](.env.example) for all required variables:

- `ANTHROPIC_API_KEY` — Claude API key
- `NEO4J_URI` — Neo4j connection string
- `DATABASE_URL` — PostgreSQL connection string
- `VOYAGE_API_KEY` — Voyage AI embedding API key

## Project Structure

```
gitaai/
├── apps/web/              # Next.js frontend
├── services/pipeline/     # Python RAG + Knowledge Graph pipeline
├── data/                  # Text data (raw, processed, seeds)
├── docs/                  # Architecture and design docs
└── scripts/               # Utility scripts
```

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before getting started.

This is a project that bridges technology and spirituality. We ask contributors to approach the source material with respect and accuracy.

## Roadmap

- [ ] **Phase 1** — MVP: Gita RAG chat with basic citation
- [ ] **Phase 2** — Knowledge Graph integration, multi-text support
- [ ] **Phase 3** — Multi-perspective answers, graph visualization, learning paths
- [ ] **Phase 4** — Community annotations, Hindi/Sanskrit UI, mobile app

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed phased plan.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

This project draws from publicly available translations and commentaries of Hindu scriptures. We are grateful to the scholars, translators, and traditions that have made these texts accessible.
