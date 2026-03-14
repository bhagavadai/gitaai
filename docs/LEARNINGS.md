# GitaAI — Learnings & Pitfalls

Issues, debugging insights, and design decisions accumulated during development. Read this before making changes to avoid repeating past mistakes.

## Environment & Tooling

### Python version mismatch
- **Problem:** `command not found: python` — macOS only has `python3` (3.9.6).
- **Fix:** Always use `python3`, never `python`.
- **Also:** Python 3.9 does not support `X | None` union syntax. Use `from __future__ import annotations` and `Optional[X]` from `typing`.

### Package manager
- **Problem:** `spawn pnpm ENOENT` — pnpm/yarn/bun are not installed.
- **Fix:** Use `npm` for all frontend operations. `create-next-app` needs `--use-npm` flag.

### Pydantic Settings .env path resolution
- **Problem:** `model_config = {"env_file": "../../.env"}` resolves relative to the config file's location, NOT the working directory. This caused settings to silently use defaults (empty strings) instead of actual values.
- **Fix:** Compute the absolute path from `__file__`: `Path(__file__).resolve().parent.parent.parent.parent / ".env"`. Always verify settings load correctly after changing config paths.

## Data & Ingestion

### UTF-8 BOM in JSON files
- **Problem:** `JSONDecodeError: Unexpected UTF-8 BOM` when loading fetched JSON data.
- **Fix:** Use `decode("utf-8-sig")` instead of `decode()` to strip the BOM.

### Translation-verse number mapping
- **Problem:** The praneshp1org dataset uses a **global sequential verse_number** (1-701) for translations, NOT chapter-specific numbering. BG 3.25 was getting BG 1.25's translation because we were matching on `verse_number` directly.
- **Fix:** Map translations via `seq_index + 1` (the verse's position in the full array) instead of `verse.verse_number`. Always verify data joins with a sanity check — "does BG 2.47 actually get the karmany evadhikaras te translation?"

### ChromaDB exception types
- **Problem:** `client.delete_collection()` raises `NotFoundError`, not `ValueError` as expected.
- **Fix:** Use `except Exception` for defensive cleanup operations where the specific exception type may vary across library versions.

## Knowledge Graph

### Concept alias matching — false positives
- **Problem:** Generic single-word aliases like `"nature"` for Prakriti or `"path"` for Yoga caused false matches. "What is the nature of the soul?" would incorrectly match Prakriti.
- **Fix:** Single-word aliases must be specific enough that they almost always mean that concept. Use multi-word phrases for ambiguous terms: `"material nature"` instead of `"nature"`, remove `"path"` and `"practice"` from Yoga.
- **Rule of thumb:** If the word commonly appears in everyday questions without referring to the concept, it's too generic.

### Concept alias matching — punctuation
- **Problem:** `query.split()` produces tokens like `"soul?"` which don't match the alias `"soul"`.
- **Fix:** Use `re.findall(r"\w+", query)` to extract clean words without punctuation.

### Speaker detection from Sanskrit text
- **Insight:** Verse speaker data wasn't in the dataset, but speakers can be reliably detected from Sanskrit text patterns: `श्रीभगवानुवाच` = Krishna, `अर्जुन उवाच` = Arjuna, `सञ्जय उवाच` = Sanjaya, `धृतराष्ट्र उवाच` = Dhritarashtra.
- **Pattern:** Track the "current speaker" and update it only when an explicit speaker marker is found. Default narrator is Sanjaya.

## API & Backend

### Uvicorn CWD for module imports
- **Problem:** `ModuleNotFoundError: No module named 'services'` when starting uvicorn from the wrong directory.
- **Fix:** Always run `python3 -m uvicorn services.pipeline.src.api.main:app` from the project root directory. Module imports are relative to CWD.

### Port conflicts on restart
- **Problem:** `[Errno 48] Address already in use` when restarting the backend.
- **Fix:** Check if the port is already in use with `curl -s http://localhost:8000/health` before starting. Kill existing process with `lsof -ti :8000 | xargs kill` if needed.

### Graceful degradation for optional services
- **Insight:** Neo4j may not always be running (dev setup, CI, etc.). The chat endpoint should still work with vector-only search.
- **Pattern:** Wrap optional service calls in try/except with empty fallback: `try: graph_result = get_concept_context(msg) except Exception: graph_result = {}`

## Frontend

### Streaming response parsing
- **Insight:** The backend streams a JSON metadata line first (verses, concepts, language), then the LLM text. The frontend must detect the first newline to split metadata from content.
- **Gotcha:** The first chunk might not contain the full JSON line — accumulate until you find `\n`.

## Git & Workflow

### Atomic commits mean commit-as-you-go
- **Problem:** Batching all changes into commits at the end of a feature loses the step-by-step history and makes commits harder to review.
- **Rule:** Commit immediately after each logical step (infra setup, new module, integration, UI). Each commit should be independently meaningful.

### Separate concerns in commits
- **Problem:** Combining frontend and backend changes in one commit violates atomic commit principles.
- **Rule:** One commit = one concern. FE and BE changes go in separate commits even if they're part of the same feature.

### No Co-Authored-By: Claude
- **Rule:** Do not include `Co-Authored-By` lines in commit messages.
