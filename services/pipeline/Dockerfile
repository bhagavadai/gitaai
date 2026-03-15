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

# Data is mounted as a volume at runtime — not baked into the image.
# This keeps the image small and allows data updates without rebuilds.
# Mount your data/ directory to /app/data when running.

ENV DATA_DIR=/app/data
ENV CHROMA_PERSIST_DIR=/app/data/chroma

# Create data dirs so app doesn't crash before volume is mounted
RUN mkdir -p /app/data/chroma

ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn services.pipeline.src.api.main:app --host 0.0.0.0 --port ${PORT}
