# GitaAI — Agent Instructions

This file governs how AI agents (Claude Code, Copilot, etc.) behave in this codebase. Read this before making any changes.

## Project Overview

GitaAI is an open-source AI chat interface grounded in the Bhagavad Gita and Vedic/Hindu scriptures. It uses a hybrid Knowledge Graph + RAG architecture to provide contextual, cited, multi-perspective answers about Vedic philosophy.

**This is a sacred-text project.** Treat the source material with respect and accuracy. Never fabricate verses, misattribute quotes, or hallucinate scripture references.

## Core Principles

### 1. Plan Before Implementing
- Before writing code, outline your approach in a comment or todo list
- For non-trivial features, create or update the relevant design doc in `docs/`
- Ask clarifying questions rather than making assumptions
- Consider how changes fit the long-term architecture (see `docs/ARCHITECTURE.md`)

### 2. Keep It Simple (KISS)
- Write the minimum code needed to solve the problem
- No premature abstractions — three similar lines > one clever abstraction used once
- No speculative features or "just in case" code
- If a function does more than one thing, split it

### 3. DRY — But Not at the Cost of Clarity
- Extract shared logic only when it's used in 3+ places
- A little repetition is better than a bad abstraction
- Shared utilities go in `src/lib/` or `src/utils/`

### 4. Modular, Clean Architecture
- Each module should have a single responsibility
- Keep files under 300 lines; split if longer
- Use clear, descriptive names — no abbreviations except well-known ones (DB, API, ID)
- Organize by feature/domain, not by file type

### 5. Test What Matters
- Write tests for business logic, data transformations, and edge cases
- Don't test framework boilerplate or trivial getters/setters
- Tests go in `__tests__/` or `*.test.ts` / `*.test.py` alongside the source
- Run existing tests before submitting changes: `npm test` or `pytest`

### 6. Security First
- NEVER commit secrets, API keys, or credentials — use `.env` files
- Validate all user input at system boundaries
- Follow OWASP top 10 guidelines
- Sanitize any text before rendering (XSS prevention)
- Use parameterized queries for all database operations

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14+ (App Router, TypeScript) |
| Styling | Tailwind CSS |
| Backend API | Next.js API routes + Python (FastAPI) for ML pipeline |
| LLM | Claude API (Anthropic SDK) |
| Knowledge Graph | Neo4j |
| Vector Store | Weaviate or ChromaDB |
| Embeddings | Voyage AI |
| Database | PostgreSQL (users, sessions, analytics) |
| Testing | Vitest (TS), Pytest (Python) |
| Package Manager | npm (frontend), uv or pip (Python) |

## Code Style

### TypeScript / JavaScript
- Strict TypeScript — no `any` unless absolutely unavoidable (add a comment explaining why)
- Prefer `const` over `let`, never use `var`
- Use async/await over raw promises
- Functional style preferred: pure functions, avoid mutation
- Use named exports, not default exports
- Error handling: use typed errors, not string throws

### Python
- Python 3.11+
- Type hints on all function signatures
- Use Pydantic for data validation/models
- Follow PEP 8 (enforced by ruff)
- Async where IO-bound (FastAPI async endpoints)

### Both
- No console.log / print in production code — use proper logging
- Environment-specific config via `.env` files, never hardcoded

## Git Practices

### Branching Strategy
- `main` — stable, deployable at all times
- `dev` — integration branch for features
- `feat/<name>` — feature branches (branch from `dev`)
- `fix/<name>` — bug fix branches
- `docs/<name>` — documentation changes
- `refactor/<name>` — refactoring (no behavior change)

### Commits
- **Atomic commits** — each commit does ONE thing and the project builds/passes tests at every commit
- **Commit as you go** — commit immediately after completing each logical unit of work (e.g., after setting up infrastructure, after writing a new module, after integrating it). Do NOT batch all changes into commits at the end. Each step should be committed before moving to the next.
- Use conventional commits format:
  ```
  type(scope): short description

  Optional longer body explaining WHY, not WHAT.
  ```
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`
- Scope examples: `rag`, `graph`, `ui`, `api`, `auth`, `ingest`
- Keep commits small and reviewable

### Pull Requests
- One feature/fix per PR
- PR description must include: what changed, why, how to test
- Link related issues
- All PRs require passing CI before merge
- Squash merge to keep history clean

## Project Structure (Target)

```
gitaai/
├── CLAUDE.md                 # This file — agent instructions
├── README.md                 # Project overview
├── CONTRIBUTING.md           # Contribution guidelines
├── LICENSE                   # Open source license
├── .env.example              # Template for environment variables
├── .gitignore
│
├── docs/                     # Design docs and architecture
│   ├── ARCHITECTURE.md       # System architecture and decisions
│   ├── DATA_MODEL.md         # Knowledge graph schema
│   └── API.md                # API documentation
│
├── apps/
│   └── web/                  # Next.js frontend
│       ├── src/
│       │   ├── app/          # Next.js App Router pages
│       │   ├── components/   # React components
│       │   ├── lib/          # Shared utilities, API clients
│       │   └── hooks/        # Custom React hooks
│       ├── public/
│       ├── package.json
│       └── tsconfig.json
│
├── services/
│   └── pipeline/             # Python ML/RAG pipeline
│       ├── src/
│       │   ├── ingest/       # Text ingestion and processing
│       │   ├── embeddings/   # Embedding generation
│       │   ├── retrieval/    # RAG retrieval logic
│       │   ├── graph/        # Knowledge graph operations
│       │   └── api/          # FastAPI endpoints
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
│
├── data/
│   ├── raw/                  # Original text files (gitignored if large)
│   ├── processed/            # Cleaned, chunked, structured data
│   └── seeds/                # Graph seed data (concepts, relationships)
│
└── scripts/                  # One-off scripts, data processing
```

## Domain-Specific Rules

### Handling Sacred Texts
- Always preserve original verse numbering (e.g., BG 2.47, KU 1.2.12)
- Store Sanskrit text alongside transliteration and translation
- Attribute translations to their source (e.g., "Translation by Swami Sivananda")
- Never paraphrase a verse without also providing the original
- When multiple interpretations exist, present them — don't pick favorites

### Knowledge Graph Conventions
- Node labels: `Scripture`, `Chapter`, `Verse`, `Concept`, `Person`, `School`, `Commentary`
- Relationship types: UPPERCASE_SNAKE_CASE (e.g., `PART_OF`, `TEACHES`, `INTERPRETS`)
- Every node must have a `source` property indicating where the data came from
- Prefer explicit relationships over inferred ones

### LLM Integration
- System prompts live in `src/lib/prompts/` — version controlled, not hardcoded
- Always include relevant retrieved context in the prompt
- Set temperature low (0.1-0.3) for factual answers about scripture
- Log token usage for cost monitoring
- Implement rate limiting on API routes

## When in Doubt

1. Read the existing code first
2. Check `docs/` for design decisions
3. Keep changes small and reversible
4. Ask the user rather than guessing
5. Prioritize correctness over cleverness
