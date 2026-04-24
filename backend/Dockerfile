# Brandy Box backend + optional web SPA (multi-stage). Build from repository root:
#   docker build -f backend/Dockerfile .

FROM node:22-bookworm AS webbuild
WORKDIR /web
COPY web/package.json ./
RUN npm install
COPY web/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/

COPY --from=webbuild /web/dist ./web_dist

ENV BRANDYBOX_STATIC_DIST_PATH=/app/web_dist

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
