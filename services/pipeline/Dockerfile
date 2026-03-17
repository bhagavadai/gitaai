FROM python:3.11-slim

WORKDIR /app

# System dependencies for ChromaDB (hnswlib compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/pipeline/pyproject.toml services/pipeline/
RUN pip install --no-cache-dir ./services/pipeline

# Copy pipeline source
COPY services/pipeline/src/ services/pipeline/src/

# Copy data needed for ingestion
COPY data/processed/ data/processed/
COPY data/seed/ data/seed/

ENV DATA_DIR=/app/data
ENV CHROMA_PERSIST_DIR=/app/data/chroma
ENV KUZU_DB_DIR=/app/data/kuzu

# Run verse ingestion and graph seeding at build time
RUN python3 -c "from services.pipeline.src.ingest.load_verses import ingest; ingest()"
RUN python3 -c "from services.pipeline.src.ingest.seed_graph import seed; seed('/app/data/kuzu')"

ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn services.pipeline.src.api.main:app --host 0.0.0.0 --port ${PORT}
