# PRISM Engine as one lite container: FastAPI serves the API and the built React app.
# Built for Render's free web service (512 MB), so it skips the ML models (see requirements-lite.txt).

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    SYSTEM1_BACKEND=keyword \
    LLM_PROVIDER=auto \
    DEMO_MODE=1
WORKDIR /app

COPY backend/requirements-lite.txt backend/requirements-lite.txt
RUN pip install --no-cache-dir -r backend/requirements-lite.txt

COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist

WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
