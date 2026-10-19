"""App settings, read once from the environment (and the repo-root .env if present)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
load_dotenv(REPO_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    world_db: Path = BACKEND_DIR / "data" / "emami_dx.sqlite"   # provided Day-0 world, read-only
    runs_db: Path = Path(os.getenv("RUNS_DB", BACKEND_DIR / "data" / "runs.sqlite"))
    rules_dir: Path = BACKEND_DIR / "app" / "rules"
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_mode: str = os.getenv("LLM_MODE", "mock")
    sim_seed: int = int(os.getenv("SIM_SEED", "42"))
    sim_scenario: str = os.getenv("SIM_SCENARIO", "typical")
    sim_autopilot: bool = _bool("SIM_AUTOPILOT", False)
    # Hosted review copy: a fresh server opens on this day of the default run (30 = a finished cycle, so every page
    # has data). The Simulation tab's Reset still replays from Day 0. 0 = start at Day 0 (local demo).
    sim_start_day: float = float(os.getenv("SIM_START_DAY", "0"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")


settings = Settings()
