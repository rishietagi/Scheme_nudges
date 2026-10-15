"""FastAPI entry point: `uvicorn app.main:app --reload --port 8000` from backend/."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cohorts, distributors, plan, sim, survey, territory
from app.config import settings
from app.models import Health

app = FastAPI(title="Emami — Distributor Experience Platform (POC)", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (sim.router, plan.router, survey.router, territory.router, cohorts.router, distributors.router):
    app.include_router(r)


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", llm_mode=settings.llm_mode, world_db=settings.world_db.exists())
