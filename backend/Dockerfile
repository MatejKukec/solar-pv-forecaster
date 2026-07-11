# Solar PV Forecaster backend. Build/run from the backend/ directory:
#   docker build -t solar-pv-backend .
#   docker run -p 8000:8000 --env-file .env solar-pv-backend
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
