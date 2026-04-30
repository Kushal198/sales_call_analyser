# Sales Call Analyser

A backend API for analysing sales call transcripts using AI. Built with Python, Django, Django REST Framework, Celery, Redis, and Docker.

---

## Tech Stack

- **Django + DRF** — API framework
- **Celery + Redis** — background job processing
- **SQLite** — zero-config local database, easily swappable to Postgres
- **OpenAI / Anthropic** — pluggable LLM provider via adapter pattern
- **Docker Compose** — single command setup

---

## Setup

### Prerequisites

- Docker and Docker Compose
- An OpenAI or Anthropic API key

### 1. Clone the repo

```bash
git clone <repo-url>
cd sales-call-analyser
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```bash
SECRET_KEY=your-secret-key-here
DEBUG=True

# Choose your provider: openai, anthropic
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 3. Start the services

```bash
docker compose up --build
```

This starts three services: `web`, `worker`, and `redis`.

### 4. Run migrations

In a separate terminal:

```bash
docker compose exec web uv run python manage.py migrate
```

---

## API

### Create a Call

```
POST /api/calls/
```

```json
{
  "title": "Demo call with Acme Corp",
  "transcript": [
    { "speaker": "Rep", "text": "Hi John, thanks for jumping on the call." },
    { "speaker": "Prospect", "text": "Sure, though I only have 20 minutes." },
    { "speaker": "Rep", "text": "What are your biggest challenges with your current CRM?" },
    { "speaker": "Prospect", "text": "The reporting is terrible and my team hates using it." },
    { "speaker": "Rep", "text": "That is exactly what we solve. Our reporting suite takes 2 minutes to build a dashboard." },
    { "speaker": "Prospect", "text": "Sounds good but what does it cost? Our budget is tight." },
    { "speaker": "Rep", "text": "We start at $200 per month. I can send a full breakdown after this call." },
    { "speaker": "Prospect", "text": "Ok, send it over and we can revisit next week." },
    { "speaker": "Rep", "text": "Perfect. I will send the pricing doc today and follow up Friday." },
    { "speaker": "Prospect", "text": "Friday works." }
  ]
}
```

Returns `201` with the created call including its `id`.

---

### Trigger Analysis

```
POST /api/calls/{call_id}/analyse/
```

Returns `202 Accepted` immediately with a `job_id`. Does not block on the AI call.

If an analysis is already in progress for this call, returns the existing job instead of creating a duplicate.

---

### Poll Job Status

```
GET /api/jobs/{job_id}/
```

Returns the job status and, once complete, the full analysis nested inside.

```json
{
  "id": "uuid",
  "status": "completed",
  "error_message": null,
  "created_at": "...",
  "analysis": {
    "summary": "...",
    "sentiment": "positive",
    "key_topics": ["pricing", "CRM reporting", "onboarding"],
    "action_items": ["Send pricing breakdown today"],
    "objections_raised": ["Budget is tight"],
    "next_steps": "Rep to send pricing doc and follow up on Friday",
    "talk_ratio": { "Rep": 0.58, "Prospect": 0.42 },
    "score": 7,
    "score_rationale": "Rep demonstrated strong discovery and handled the pricing objection well, but could have confirmed the follow-up time more explicitly.",
    "created_at": "..."
  }
}
```

Poll this endpoint until `status` is `completed` or `failed`. While pending or running, `analysis` will be `null`.

---

### List All Calls

```
GET /api/calls/
```

### List Jobs for a Call

```
GET /api/calls/{call_id}/jobs/
```

Useful if you lose the `job_id` — returns all analysis jobs for a given call ordered by most recent.

---

## Design Decisions

### What does your analysis contain, and why?

| Field | Why |
|---|---|
| `summary` | TL;DR — a manager scanning 20 calls a day needs a 2-3 sentence overview |
| `sentiment` | Prospect's overall tone — instant signal on deal health |
| `key_topics` | What was actually discussed — pricing, features, competitors |
| `action_items` | Concrete things the rep committed to post-call — highest immediate value |
| `objections_raised` | What the prospect pushed back on — gold for coaching and training |
| `next_steps` | Was there a clear agreed next step? This separates a good call from a great one |
| `talk_ratio` | Computed from speaker labels in the transcript — reliable because we have structured data |
| `score + score_rationale` | Overall call quality 1-10 with reasoning — the rationale stops it feeling like a black box |

The score is designed as a manager-facing metric. Reps seeing a live score on every call can be counterproductive — this is better surfaced in coaching conversations.

---

### How does your system behave if the AI call fails mid-job?

Celery handles retries automatically — `max_retries=3` with a 5 second delay between attempts. If all three attempts fail, the job is marked `failed` and the `error_message` is persisted to the database so the client knows what went wrong.

The client can re-trigger analysis at any time by posting to `/api/calls/{call_id}/analyse/` — a fresh job is created and the failed one is left in history.

One known edge case: if the Celery worker process dies mid-task, the job can get stuck in `running` state. In production this is solved with `task_acks_late = True` combined with Redis visibility timeouts so the broker re-queues the task automatically. A management command is also included to clean up stuck jobs manually:

```bash
docker compose exec web uv run python manage.py cleanup_stuck_jobs
```

---

### If you were to add a sharing model (reps and managers see different things), how would you approach it?

I would add a `role` field to the user model — `rep` or `manager` — and link each `Call` to the rep who owns it.

The serializer would check `request.user.role` and return different fields based on role. The key difference: `score` and `score_rationale` would be manager-only. Reps seeing a numerical score on every call can be demoralising and counterproductive — managers use it for structured coaching conversations, not as a live feed to the rep.

No separate endpoints needed — same `GET /api/jobs/{id}/` returns a different shape depending on who is asking. Clean, no duplication.

---

### What would you change or add with another day of work?

- **Postgres** — swap SQLite for Postgres in Docker Compose. The ORM calls are identical, it is a one-line settings change
- **Authentication** — JWT-based auth so calls are scoped to users, not globally visible
- **Celery Beat** — scheduled task to automatically clean up jobs stuck in `running` state beyond a timeout
- **Webhook support** — instead of polling, clients register a callback URL and get notified when analysis completes
- **Pagination** — `GET /api/calls/` needs pagination before it hits any real volume

---

## Switching LLM Provider

The LLM layer uses an adapter pattern — swapping providers is a single environment variable change, no code changes needed.

```bash
# Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Use Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Adding a new provider in future means writing one class that implements `LLMProvider.analyse()` and adding one `elif` to `get_llm_provider()`. Nothing else in the codebase changes.

---

## Scalability Note

The current setup runs a single Celery worker process. For thousands of concurrent calls, you would scale horizontally — run multiple worker containers and let Redis distribute the queue across them. Docker Compose makes this trivial:

```bash
docker compose up --scale worker=4
```

The application code requires no changes.