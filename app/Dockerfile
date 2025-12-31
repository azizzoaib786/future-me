# Builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into the default locations
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Pre-download the HuggingFace embedding model so runtime doesn't hit HF
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user
RUN useradd -m appuser

# Copy installed Python libs and binaries from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache /root/.cache

# Copy app code
COPY app.py .
COPY static ./static

# Fix permissions
RUN chown -R appuser:appuser /app /root/.cache

USER appuser

EXPOSE 8000

# Gunicorn with Uvicorn worker
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "app:app"]
