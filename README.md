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
      +---> Knowledge Graph (Kùzu)      --> Related concepts, cross-references,
      |                                      schools of thought, lineage
      |
      +---> LLM (Claude)               --> Synthesizes a grounded, cited answer
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full technical design.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (TypeScript, Tailwind CSS) |
| Backend | FastAPI (Python) |
| LLM | Claude API (Anthropic) |
| Knowledge Graph | Kùzu (embedded) |
| Vector Store | ChromaDB |
| Embeddings | MiniLM (local, via ChromaDB) |

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- npm
- Docker (optional, for containerized deployment)

### Setup

```bash
# Clone the repository
git clone https://github.com/bhagavadai/gitaai.git
cd gitaai

# Copy environment variables
cp .env.example .env
# Fill in your API keys in .env

# Install frontend dependencies
cd apps/web && npm install && cd ../..

# Install Python dependencies
cd services/pipeline && pip install -e ".[dev]" && cd ../..

# Ingest data into ChromaDB
python3 -m services.pipeline.src.ingest.load_verses

# Seed knowledge graph (Kùzu — embedded, no server needed)
python3 -c "from services.pipeline.src.ingest.seed_graph import seed; from services.pipeline.src.config import settings; seed(settings.kuzu_db_dir)"

# Run the backend (from project root)
python3 -m uvicorn services.pipeline.src.api.main:app --reload

# Run the frontend (in another terminal)
cd apps/web && npm run dev
```

### Environment Variables

See [.env.example](.env.example) for all required variables:

- `LLM_PROVIDER` — `bedrock` (AWS) or `anthropic` (direct API)
- `ANTHROPIC_API_KEY` or `AWS_*` — LLM credentials
- `VOYAGE_API_KEY` — Voyage AI embedding API key
- `KUZU_DB_DIR` — Kùzu database directory (default: `data/kuzu`)
- `CORS_ORIGINS` — Comma-separated allowed origins for the API
- `NEXT_PUBLIC_PIPELINE_URL` — Backend URL for the frontend

## Deployment

### Frontend (Vercel)

1. Connect your GitHub repo to [Vercel](https://vercel.com)
2. It will auto-detect the `vercel.json` config (builds from `apps/web/`)
3. Set environment variable: `NEXT_PUBLIC_PIPELINE_URL` = your backend URL

### Backend (Railway)

1. Create a new [Railway](https://railway.app) project from the repo
2. Point to the Dockerfile at `services/pipeline/Dockerfile`
3. Set environment variables: API keys, `CORS_ORIGINS` (your Vercel URL)
4. Mount a persistent volume at `/app/data` for ChromaDB and Kùzu

### Docker Compose (local / self-hosted)

```bash
# Start backend
docker compose up -d

# Frontend runs separately
cd apps/web && npm run dev
```

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

- [x] **Phase 1** — MVP: Gita RAG chat with verse citations and Hindi support
- [x] **Phase 2** — Knowledge Graph integration (concepts, relationships, hybrid retrieval)
- [ ] **Phase 3** — Multi-perspective answers, graph visualization, learning paths
- [ ] **Phase 4** — Community annotations, Hindi/Sanskrit UI, mobile app

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed phased plan.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

This project draws from publicly available translations and commentaries of Hindu scriptures. We are grateful to the scholars, translators, and traditions that have made these texts accessible.
