# Build context is the repository root (see docker-compose.yml) so that the
# nginx config under deploy/ is reachable. All frontend paths are prefixed
# with frontend/ accordingly.

# ── Stage 1: build the Vite SPA ──────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
# Use a clean, reproducible install when a lockfile exists; fall back otherwise.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/ ./
RUN npm run build

# ── Stage 2: serve static assets via nginx ───────────────────
FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
