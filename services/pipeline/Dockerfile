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

# Copy processed data needed for ingestion
COPY data/processed/ data/processed/

ENV DATA_DIR=/app/data
ENV CHROMA_PERSIST_DIR=/app/data/chroma

# Run verse ingestion at build time so ChromaDB is ready on startup
RUN python3 -c "from services.pipeline.src.ingest.load_verses import ingest; ingest()"

ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn services.pipeline.src.api.main:app --host 0.0.0.0 --port ${PORT}
