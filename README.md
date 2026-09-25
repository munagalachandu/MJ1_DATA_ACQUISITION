# Student Profile — Data Acquisition (Task 1, deployable version)

Pure extraction/acquisition — **no confidence scores or weighting are assigned
anywhere in this code.** Every skill/project/certification/hackathon record
just carries `source` (where it came from), so a later stage can decide how
to weigh sources without this stage needing to change.

```
project/
├── backend/            FastAPI app — one endpoint, does all extraction
│   └── app/
│       ├── main.py          POST /api/submit — the only real endpoint
│       ├── config.py        env vars (API keys, CORS)
│       ├── llm.py           Gemini primary + Groq fallback (text + vision)
│       ├── normalizer.py    skill name canonicalization only
│       ├── aggregator.py    combines extractors' output + computes CGPA
│       └── extractors/      one file per source (marksheet, resume, github, leetcode, certificate, hackathon, achievement)
├── frontend/            Plain HTML/CSS/JS, no build step
│   ├── index.html           multi-step intake form
│   ├── style.css
│   └── app.js                step logic, FormData submit, results rendering
└── render.yaml          One-click Render blueprint for both services
```

## Local run

**Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # fill in your keys, then export them or use a tool like `direnv`
export GEMINI_API_KEY=...
export GROQ_API_KEY=...   # optional fallback
export GITHUB_TOKEN=...   # optional, raises GitHub rate limit
export ALLOWED_ORIGINS=http://127.0.0.1:5500   # or wherever you serve the frontend from
uvicorn app.main:app --reload --port 8000
```

**Frontend** — no build step, just open `frontend/index.html` with a local
static server (VS Code's "Live Server", or `python -m http.server` from
inside `frontend/`). Before that, edit the top of `frontend/app.js`:

```js
const API_BASE = "http://127.0.0.1:8000";   // point at your local backend
```

## Deploying on Render

Two separate services (already described in `render.yaml` — you can create
them individually in the dashboard, or use **New → Blueprint** and point it
at this repo to create both at once):

1. **Backend — Web Service**
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables: `GEMINI_API_KEY`, `GROQ_API_KEY`, `GITHUB_TOKEN`, `ALLOWED_ORIGINS` (set this to your frontend's Render URL once you have it)

2. **Frontend — Static Site**
   - Root directory: `frontend`
   - Build command: (leave empty)
   - Publish directory: `.`
   - After the backend is live, edit `frontend/app.js`'s `API_BASE` constant to the backend's `https://....onrender.com` URL, commit, and Render will redeploy the static site automatically.

Render's free-tier web services spin down when idle — the first request
after inactivity can take 30–60s to wake up. Worth mentioning if you're
demoing this live at a review.

## Why Gemini + Groq specifically

- **Gemini** (primary): one API handles both text extraction (resume) and
  vision extraction (marksheets, certificates, hackathon proofs) directly —
  you don't need a separate OCR step, it reads the image/PDF natively.
- **Groq** (fallback, free tier): OpenAI-compatible API, so `llm.py` calls
  it with the same request shape as Gemini's response is parsed into. Only
  kicks in if Gemini's key is missing or a call fails/rate-limits — you
  won't notice it unless Gemini is unavailable.
- If Groq's free tier is unavailable to you, swapping in a different
  fallback (e.g. Hugging Face Inference API, OpenRouter's free models) is a
  ~15-line change confined entirely to `llm.py` — nothing else in the
  codebase talks to a provider directly.

## What's intentionally NOT here yet

- No database — each submission returns its JSON directly and nothing is
  persisted server-side. Add a `students` table / simple JSON-file store in
  `aggregator.py` once you need profiles to persist across sessions.
- No skill-confidence weighting — per this stage's scope, everything is
  extraction only. That logic belongs in Stage 2 (Knowledge Graph /
  reasoning), reading the `source` field this JSON already provides.
- No auth — anyone with the URL can submit a profile. Fine for a review
  demo; add a login step before treating this as production.
