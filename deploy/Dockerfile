FROM node:22-alpine AS web
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend/ /app/backend/
COPY --from=web /build/frontend/dist /app/frontend/dist
RUN useradd --uid 10001 --create-home escape && mkdir -p /app/data && chown escape:escape /app/data
USER escape
ENV ESCAPE_DATA=/app/data
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "escapeplan.server:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-max-size", "16384", "--proxy-headers"]
