# ──────────────────────────────────────────────────────────────
# Market Digest — Docker Build
# ──────────────────────────────────────────────────────────────
# Build:  docker compose up --build
# Or:     docker build -t market-digest .
#         docker run -p 8550:8550 --env-file .env market-digest
# ──────────────────────────────────────────────────────────────

# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/ui/frontend
COPY ui/frontend/package*.json ./
RUN npm ci --silent
COPY ui/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY config/ config/
COPY src/ src/
COPY ui/ ui/
COPY scripts/ scripts/

# Copy built frontend from stage 1
COPY --from=frontend /app/ui/frontend/dist ui/frontend/dist

# Create runtime directories
RUN mkdir -p logs/retrace cache

EXPOSE 8550

CMD ["python", "-m", "uvicorn", "ui.server:app", "--host", "0.0.0.0", "--port", "8550"]
