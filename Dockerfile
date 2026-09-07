FROM python:3.12-slim

WORKDIR /app

# Pre-built nexo-platform wheel(s) must be present under vendor/ (see scripts/vendor_platform.py).
COPY vendor/ /tmp/vendor/
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations

ENV PIP_FIND_LINKS=/tmp/vendor \
    PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip \
    && pip install . \
    && rm -rf /tmp/vendor

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn nexo_vending.main:app --host 0.0.0.0 --port 8000"]
