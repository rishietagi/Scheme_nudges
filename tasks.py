"""Task runner (works on Windows without make).  python tasks.py <seed|dev|test|demo>

Python interpreter: $EMAMI_PYTHON, else the conda env `pmo-intel-engine`, else the current one.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
CONDA_PY = Path(r"C:\miniconda\envs\pmo-intel-engine\python.exe")
PY = os.getenv("EMAMI_PYTHON") or (str(CONDA_PY) if CONDA_PY.exists() else sys.executable)
NPM = shutil.which("npm") or "npm"
ENV = {**os.environ, "PYTHONUTF8": "1"}   # the generator prints ₹; Windows consoles need UTF-8


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print(f"$ {' '.join(cmd)}   (in {cwd.name}/)")
    subprocess.run(cmd, cwd=cwd, env=env or ENV, check=True)


def seed() -> None:
    run([PY, "scripts/generate_data.py"], BACKEND)


def dev() -> None:
    api = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], cwd=BACKEND, env=ENV)
    web = subprocess.Popen([NPM, "run", "dev"], cwd=FRONTEND, env=ENV)
    print("API http://localhost:8000 · App http://localhost:3000 · Ctrl+C to stop")
    try:
        api.wait()
        web.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (api, web):
            p.terminate()


def test() -> None:
    run([PY, "-m", "pytest", "-q"], BACKEND, {**ENV, "LLM_MODE": "mock"})
    run([NPM, "run", "lint"], FRONTEND)
    run([NPM, "run", "build"], FRONTEND)


def demo() -> None:
    # Phase 7: reset the simulator to the default seed in replay mode, then start everything.
    os.environ["LLM_MODE"] = "replay"
    ENV["LLM_MODE"] = "replay"
    dev()


TASKS = {"seed": seed, "dev": dev, "test": test, "demo": demo}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        sys.exit(f"usage: python tasks.py <{'|'.join(TASKS)}>")
    TASKS[sys.argv[1]]()
