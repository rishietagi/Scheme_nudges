# Deploy the review copy (free, Render)

One free **Render** web service runs the whole app from the `Dockerfile`:
- the website (Next.js) on Render's public port;
- the API (FastAPI) privately inside the same container — the website forwards `/api/*` to it.

There is one URL and one password. AI text comes from the hand-written fixtures (no Gemini key on the server), and a fresh server opens on a finished Day-30 cycle.

## One-time setup (about 10 minutes)

1. **Push this repo to GitHub.** The repo must include `Dockerfile`, `render.yaml`, `.dockerignore`, `deploy/start.sh`, `frontend/proxy.ts` and the data in `backend/data/` (`emami_dx.sqlite`, `csv/`). `.env` is never shipped: `.gitignore` and `.dockerignore` keep it out.
2. Sign in at **https://render.com** with GitHub. The free plan needs no card.
3. **New + → Blueprint** and pick this repository. Render reads `render.yaml` and proposes one service, `emami-dx-prototype` (Docker, Free).
4. When asked for **`DEMO_PASSWORD`**, type the password reviewers will use. The username is `emami`; you can change `DEMO_USER` in the service's Environment tab.
5. **Apply.** The first build takes about 5–8 minutes. When the service shows **Live**, open its `https://emami-dx-prototype.onrender.com` URL (Render shows the exact one) and sign in.

Every push to the default branch redeploys automatically (`autoDeploy: true`).

## What to send reviewers

> Emami Distributor Experience Platform — concept prototype (synthetic data)
> https://emami-dx-prototype.onrender.com · username `emami` · password `<the password>`
> If it takes a minute to open, it's waking up — the free server sleeps when nobody's using it.
> Start on **Cohorts**. To replay the whole cycle: **Simulation → Reset to Day 0 → Play**, then accept / modify / reject on
> **Approvals** when it pauses at Day 7.

## How the free hosting behaves

| What | Detail |
|---|---|
| Sleep | After 15 minutes with no visitors the server sleeps. The next visit wakes it in about 1 minute (the browser just waits). |
| Fresh start | Each wake-up rebuilds the demo at **Day 30** (everything filled in). Anything changed before it slept is gone: approvals, Keep/Drop, chat and **saved Set-up edits** (cohort rules, survey). |
| Shared | Everyone shares one simulation. If two reviewers press Reset or Approve at the same time, they see each other's changes. |
| Speed | The free plan has a small CPU share. Pages open in 1–4 s; a full replay (Reset → Play → Day 30) takes about 45 s. |
| Limits | 750 free hours a month, which is enough to leave it up. Memory use is about 150 MB of the 512 MB allowed. |
| Data | Synthetic only; WhatsApp and DMS are simulated. No Gemini key or other secret is on the server. |

Optional: to avoid the 1-minute wake-up during a review week, point a free uptime monitor (e.g. UptimeRobot) at `https://<your-url>/healthz` every 10 minutes. `/healthz` sits outside the password gate.

## Test the exact image locally (optional)

```bash
docker build -t emami-dx .
docker run -p 10000:10000 -e DEMO_PASSWORD=secret emami-dx      # open http://localhost:10000  (emami / secret)
```

## Settings (Render → service → Environment)

| Variable | Default | Meaning |
|---|---|---|
| `DEMO_PASSWORD` | — (required) | The shared password. Leave it empty to make the site public. |
| `DEMO_USER` | `emami` | The shared username. |
| `SIM_START_DAY` | `30` | The day a fresh server opens on (`0` = start like the live demo). |
| `LLM_MODE` | `mock` | `mock` = fixtures only. To use live Gemini, set `LLM_MODE=live` and add `GEMINI_API_KEY` + `GEMINI_MODEL`. The free tier allows 5 requests/minute shared by everyone. |

Local development is unchanged: `python tasks.py dev` (no password, API on :8000).
