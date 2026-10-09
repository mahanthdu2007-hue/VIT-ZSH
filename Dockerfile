# PRISM Engine as one container: FastAPI serves the API and the built React app.
# Built for Hugging Face Spaces (Docker SDK, free CPU tier, port 7860).

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=auto \
    DEMO_MODE=1
WORKDIR /home/user/app

COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user backend/ backend/
COPY --chown=user --from=frontend /app/frontend/dist frontend/dist

USER user
WORKDIR /home/user/app/backend
# Download the models and build the search index at build time, so the Space starts fast.
RUN python scripts/warmup.py; python -m app.rag.index

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
