FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY .env /app/.env
COPY backend/pyproject.toml backend/requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/backend/
COPY frontend/.next/server/app/index.html /app/backend/static/index.html
COPY frontend/.next/static /app/backend/static/_next/static


EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
