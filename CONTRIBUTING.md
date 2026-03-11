# Contributing to GitaAI

Thank you for your interest in contributing to GitaAI! This project bridges technology and ancient wisdom, and we value contributions that respect both.

## Code of Conduct

- Treat all contributors and the source material with respect
- Be constructive in code reviews
- When in doubt about representing a text or tradition, err on the side of accuracy and cite your sources

## Getting Started

1. Fork the repository
2. Create a feature branch from `dev`: `git checkout -b feat/your-feature dev`
3. Make your changes (see guidelines below)
4. Run tests and linting
5. Submit a pull request to `dev`

## Development Workflow

### Before You Code

- **Check existing issues** — someone may already be working on it
- **Open an issue first** for non-trivial changes to discuss the approach
- **Read the relevant docs** in `docs/` to understand architectural decisions
- **Plan your approach** — write a brief outline in the issue before implementing

### Writing Code

- Follow the coding standards in [CLAUDE.md](CLAUDE.md)
- Keep changes focused — one feature or fix per PR
- Write tests for new functionality
- Update documentation if your change affects APIs or architecture

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description

Optional body explaining WHY the change was made.
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

**Scopes:** `rag`, `graph`, `ui`, `api`, `auth`, `ingest`, `data`

Examples:
```
feat(rag): add verse retrieval for Upanishads
fix(graph): correct relationship direction for INTERPRETS edges
docs(api): add endpoint documentation for /chat
test(ingest): add tests for Sanskrit transliteration parser
```

### Atomic Commits

Each commit should:
- Do exactly ONE thing
- Leave the project in a buildable, testable state
- Be small enough to review in a few minutes

Bad: "Add search feature, fix styling, update deps"
Good: Three separate commits for each of those changes.

## Pull Request Process

1. **Title**: Clear, concise summary (under 70 chars)
2. **Description**: Include:
   - What changed and why
   - How to test it
   - Screenshots for UI changes
   - Link to related issue(s)
3. **Size**: Keep PRs under ~400 lines of meaningful changes. Split larger work into stacked PRs.
4. **CI must pass** before review
5. **One approval required** before merge
6. **Squash merge** to keep main history clean

## Areas of Contribution

### For Developers
- Frontend components and UX improvements
- RAG pipeline optimization
- Knowledge graph schema and queries
- API endpoints
- Testing and CI/CD

### For Sanskrit/Vedic Scholars
- Verify verse accuracy and translations
- Suggest concept relationships for the knowledge graph
- Review AI-generated answers for correctness
- Add new texts and commentaries

### For Everyone
- Bug reports and feature requests
- Documentation improvements
- Accessibility improvements
- Translations (Hindi, Sanskrit UI)

## Working with Sacred Texts

This section is important. These texts are sacred to millions of people.

- **Accuracy over speed** — double-check verse numbers, translations, and attributions
- **Cite your sources** — every translation must be attributed (e.g., "Translation by Swami Sivananda")
- **Preserve originals** — always store original Sanskrit alongside translations
- **Multiple perspectives** — don't favor one school of interpretation. If Shankaracharya and Ramanuja differ, represent both.
- **No editorializing** — present what the texts say, don't add modern opinions as if they're scripture
- **Copyright** — only use public domain or explicitly licensed translations

## Running Tests

```bash
# Frontend (TypeScript)
cd apps/web && pnpm test

# Pipeline (Python)
cd services/pipeline && pytest

# Linting
cd apps/web && pnpm lint
cd services/pipeline && ruff check .
```

## Questions?

Open an issue with the `question` label, or start a discussion in the Discussions tab.
