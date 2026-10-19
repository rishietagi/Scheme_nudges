#!/bin/sh
# Starts the private API, builds the demo run, then serves the website on $PORT.
set -e

cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning &
API_PID=$!

echo "Waiting for the API..."
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then break; fi
  if ! kill -0 "$API_PID" 2>/dev/null; then echo "API failed to start"; exit 1; fi
  sleep 1
done
# Build the default run now (Day 30 on a fresh server) so the first visitor doesn't wait for it.
curl -sf http://127.0.0.1:8000/sim/state >/dev/null && echo "Demo run ready."

cd /app/web
exec node server.js
