# Hosted review copy of the Emami Distributor Experience Platform (concept prototype, synthetic data).
# One container: the Next.js server on $PORT (public) + the FastAPI API on 127.0.0.1:8000 (private, reached via /api).
# Build:  docker build -t emami-dx .      Run:  docker run -p 10000:10000 -e DEMO_PASSWORD=secret emami-dx

# ---------- 1. Build the website (Next.js standalone output)
FROM node:24-bookworm-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# The browser calls the API on the same origin; next.config.ts forwards /api/* to the private API.
ENV NEXT_PUBLIC_API_URL=/api \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- 2. Runtime: Node (website) + Python 3.11 (API)
FROM node:24-bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv curl \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=web /app/frontend/.next/standalone ./web
COPY --from=web /app/frontend/.next/static ./web/.next/static
COPY --from=web /app/frontend/public ./web/public
COPY deploy/start.sh ./start.sh

# Fixtures only (no LLM key on the server), and a fresh server opens on a finished Day-30 cycle.
ENV LLM_MODE=mock \
    LLM_CHAT_LIVE=false \
    SIM_START_DAY=30 \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=10000
EXPOSE 10000
CMD ["sh", "start.sh"]
