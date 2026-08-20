# Dockerfile
# Uses Astral's official uv+python combined image — avoids manually
# installing uv via curl, and matches the project's package manager
# exactly (same tool used locally: uv sync, uv run).

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy dependency files FIRST, install, THEN copy the rest of the code.
# Layer caching: Docker only re-runs `uv sync` when pyproject.toml or
# uv.lock actually change, not on every source edit — same lesson
# learned on ml-baseline-service (P1), where getting this order wrong
# meant every code change triggered a full dependency reinstall.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Now copy everything else — source code, data/cache/*.json (required:
# the live demo must run from cache, never from a live API call).
COPY . .

RUN uv sync --frozen --no-dev

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# --host 0.0.0.0 is required inside any container — uvicorn's default
# 127.0.0.1 is unreachable from outside the container, exactly the same
# issue documented from P1. ${PORT:-8000}: Railway injects PORT at
# runtime; falls back to 8000 for local testing where PORT isn't set.
CMD uv run uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}