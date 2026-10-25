FROM node:24-bookworm-slim AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /app/dist ./frontend/dist/
RUN useradd --create-home --uid 10001 winddesk
USER winddesk
EXPOSE 8080
CMD ["sh", "-c", "exec python -m uvicorn backend.production:app --host 0.0.0.0 --port \"$PORT\""]
