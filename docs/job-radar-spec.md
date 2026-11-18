# Job Radar — Tech Spec

**Status:** Draft v0.2 · 2026-11-11
**Owner:** John Nutter
**Type:** Portfolio project (job search), sized for ~4 weeks part-time

**Changes since v0.1:** split LLM work by privacy. Public posting data goes to Claude Haiku 5.5. Scoring is now deterministic Python, and the fit summary (the only step that reads the resume) runs on local Ollama. The pipeline runs on John's Mac; the hosted instance becomes a seeded, read-only demo.

---

## 1. Summary

Job Radar is a Django app that pulls job postings on a schedule, uses the Claude API to turn each one into structured data, scores it against John's skills profile in plain Python, and uses a local Ollama model to write a short "why it fits / where the gaps are" note. A dashboard shows a ranked weekly shortlist.

It exists to do two things:

1. Make John's job search faster: less reading of postings that were never a fit.
2. Show, in one repo, the skills recent postings keep asking for: building on LLM APIs, automation pipelines, scheduled jobs, a REST API, and testing and evaluating LLM output. It also shows a deliberate privacy and cost tradeoff between hosted and local models.

## 2. Design principles

- **Only public data leaves the machine.** Posting text goes to Claude. The resume and skills profile never do.
- **Deterministic where possible.** The score is computed in Python from structured fields, so every number can be explained. LLMs are used only for reading unstructured text (extraction) and writing prose (fit summary).
- **Cheap by default.** Haiku 5.5 plus the Batches API for extraction, free local inference for summaries, and a hard cap per run.
- **Measured, not assumed.** Model choices are backed by the eval set (§11), not by gut feel.

## 3. Goals and non-goals

### Goals (v1)

- Ingest postings from a few legitimate sources on a schedule, with deduplication.
- Extract structured fields from each posting with Claude (skills, seniority, location, salary, red flags).
- Score each posting against a stored skills profile with a transparent, weighted formula.
- Generate a 1–2 sentence fit summary locally with Ollama.
- A dashboard that ranks this week's postings and lets John mark them (interested, applied, pass).
- A DRF API over the same data.
- An eval set that measures extraction quality, and compares Claude with a local model on the same postings.
- A public, read-only demo on seeded data, plus a README good enough for interviews.

### Non-goals (v1)

- Scraping sites whose terms forbid it (LinkedIn, Indeed). Use public job-board APIs, RSS feeds and manual entry only.
- Auto-applying or generating cover letters.
- Multiple users or auth beyond Django admin login. It's single-user.
- A Celery/Redis task queue. A scheduled management command is enough at this volume.
- Running the real pipeline in the cloud. The real pipeline runs locally; only the demo is hosted.

## 4. Architecture

```
 ┌──────────────────────────── John's Mac (launchd, daily) ────────────────────────────┐
 │                                                                                      │
 │  Sources ──▶ fetch ──▶ Posting ──▶ extract ──────────▶ Extraction ──▶ score ──▶ Score ──▶ summarize ──▶ fit_summary
 │  (Greenhouse,         (dedupe)     │                                  (Python,          (Ollama,
 │   Lever, RSS,                      │  public posting text only        no LLM)           local only;
 │   manual)                          ▼                                                    reads resume)
 │                           Claude Haiku 5.5                                              │
 │                           (Batches API)  ◀── the only network LLM call                  │
 │                                                                                         ▼
 │                                         Django views (dashboard) + DRF API + Django admin
 └──────────────────────────────────────────────────────────────────────────────────────┘

 Hosted demo (Railway / Fly.io / Render): same app, RADAR_DEMO_MODE=true, seeded data, no pipeline, no API keys.
```

**Pipeline stages are separate commands** so each one can be re-run, tested and logged on its own:

| Stage | Command | Runs on | What it does |
|---|---|---|---|
| Fetch | `uv run manage.py fetch_postings` | Local | Pulls from every active `Source` and stores new `Posting` rows. Hashes the text to skip duplicates. |
| Extract | `uv run manage.py extract_postings` | Claude API | Sends unextracted postings in one batch. Saves an `Extraction` per posting. |
| Score | `uv run manage.py score_postings` | Local Python | Compares each extraction with the active `SkillsProfile`. Saves a `Score`. |
| Summarize | `uv run manage.py summarize_postings` | Local Ollama | Writes `fit_summary` for postings above a score threshold. |
| All | `uv run manage.py run_pipeline` | — | Runs all four in order and records a `PipelineRun`. This is what launchd calls. |

Manual entry (pasting a URL or text) runs all stages right away, with a normal (non-batch) Claude call for extraction.

## 5. Stack

| Concern | Choice | Notes |
|---|---|---|
| Language / env | Python 3.13, `uv` | `uv venv`, `uv add`, `uv run` |
| Web | Django 5.x | Server-rendered dashboard |
| API | Django REST Framework | Read and update endpoints |
| DB | SQLite | Single user, single machine. Postgres only if that ever changes. |
| Hosted LLM | Anthropic Python SDK (`anthropic`), Claude Haiku 5.5 | Extraction only |
| Local LLM | Ollama, via the `ollama` Python package | Fit summaries; extraction in evals for comparison |
| HTTP fetch | `httpx` | Job-board APIs and RSS |
| RSS parsing | `feedparser` | |
| HTML → text | `selectolax` or `beautifulsoup4` | Pick one; strips posting HTML |
| Schemas | Pydantic v2 | Shared by structured outputs and validation |
| Scheduling | macOS `launchd` agent | Runs `run_pipeline` daily; catches up after sleep |
| Tests | `pytest`, `pytest-django` | |
| Lint / format | `ruff` | |
| CI | GitHub Actions | Tests on every PR; evals on demand |
| Demo hosting | Railway, Fly.io or Render | Web service only, no cron |

**New dependencies to note:** `django`, `djangorestframework`, `anthropic`, `ollama`, `httpx`, `feedparser`, `pydantic`, one HTML parser, `pytest`, `pytest-django`, `ruff`, plus `django-environ` (or `dj-database-url`) for env-driven settings. Ollama itself is a local install, not a Python dependency.

## 6. Data model

Every model follows the house rules: UUID primary key (`default=uuid.uuid4`), `created_at` (`auto_now_add`), `updated_at` (`auto_now`), nullable `deleted_at` for soft delete, and `USE_TZ = True`. A shared abstract `BaseModel` holds these fields, and a default manager filters out soft-deleted rows.

### `Source`
- `kind`: `greenhouse` | `lever` | `rss` | `manual`
- `name`: e.g. "Coca-Cola (Greenhouse)"
- `identifier`: board token, Lever company slug, or feed URL
- `is_active`: bool
- `last_fetched_at`: datetime, nullable

### `Posting`
- `source`: FK → Source
- `external_id`: the board's own ID, when it has one
- `url`: unique
- `title`, `company`, `location_raw`
- `body_text`: cleaned plain text
- `content_hash`: SHA-256 of `body_text`, for deduplication
- `posted_at`: datetime, nullable
- `status`: `new` | `interested` | `applied` | `passed`

### `Extraction`
One per posting; re-extraction soft-deletes the old row.
- `posting`: FK → Posting
- `data`: JSONField, validated against the Pydantic `PostingExtraction` schema (§7.2)
- `provider`: `anthropic` | `ollama`
- `model`: model ID used
- `prompt_version`: string, e.g. `extract-v3`
- `input_tokens`, `output_tokens`: ints, for cost tracking

### `SkillsProfile`
What the scorer compares postings against. **Stays local, and is never sent to any API.** The hosted demo uses a fictional profile.
- `name`: e.g. "Frontend-leaning," "Full stack"
- `resume_text`: plain text; used only by the local summarizer
- `skills`: JSONField, list of `{name, level}` where level is `strong` | `working` | `learning`
- `target_seniority`: list, e.g. `["mid", "senior"]`
- `work_modes`: list, e.g. `["remote", "hybrid"]`
- `locations`: list of acceptable locations
- `salary_floor`: int, nullable
- `is_active`: bool (only one active at a time)

### `SkillAlias`
Normalizes skill names so "JS," "Javascript" and "JavaScript (ES6+)" all match.
- `alias`: string, unique, lowercased
- `canonical`: string

### `Score`
- `posting`: FK → Posting
- `profile`: FK → SkillsProfile
- `overall`: int 0–100
- `breakdown`: JSONField, the sub-scores and weights used (§8)
- `matched_skills`, `missing_skills`: JSONField lists
- `fit_summary`: text, nullable (filled by the summarize stage)
- `summary_model`: Ollama model ID used, nullable
- `formula_version`: string, e.g. `score-v1`

### `PipelineRun`
- `started_at`, `finished_at`
- `status`: `running` | `succeeded` | `partial` | `failed`
- `fetched_count`, `extracted_count`, `scored_count`, `summarized_count`
- `error_log`: text
- `estimated_cost_usd`: decimal (Claude spend only)

## 7. LLM integration

### 7.1 Provider layer

`radar/llm/` holds one small interface and two implementations. Nothing else imports either SDK directly.

- `providers/base.py`: a `Protocol` with `extract(posting_text) -> PostingExtraction` and `summarize(score, profile) -> str`.
- `providers/anthropic.py`: extraction via Claude. Also implements batch submit and collect.
- `providers/ollama.py`: summaries in production, plus extraction for eval comparisons.
- Which provider handles which task is set by env vars (`RADAR_EXTRACT_PROVIDER`, `RADAR_SUMMARY_PROVIDER`), with a guard: **the summary provider must be `ollama`** unless `RADAR_ALLOW_REMOTE_RESUME=true` is set explicitly. That makes the privacy rule enforced in code, not just written down.

### 7.2 Extraction (Claude Haiku 5.5)

- Model from `RADAR_CLAUDE_MODEL`, default `claude-haiku-5-5`. Effort set explicitly to `low` (`output_config.effort`); raise it only if the evals show it helps.
- Output is a Pydantic `PostingExtraction`, validated by the SDK's `messages.parse()`:
  - `title_normalized`, `seniority` (`junior` | `mid` | `senior` | `staff+` | `unknown`)
  - `required_skills[]`, `nice_to_have_skills[]`
  - `years_experience_min` (nullable int)
  - `work_mode` (`remote` | `hybrid` | `onsite` | `unknown`), `locations[]`
  - `salary_min`, `salary_max`, `salary_currency` (nullable)
  - `domain_tags[]`, `red_flags[]`, `ai_exposure`
- The prompt tells the model to use `unknown` or null rather than guess.
- Check `stop_reason` before reading content; catch specific SDK exceptions and retry only the retryable ones.
- `ANTHROPIC_API_KEY` comes from the environment. Never commit it. The hosted demo has no key at all.

### 7.3 Batching

The scheduled run sends extraction through the **Message Batches API**: half the price, and nobody's waiting. Results come back in any order and are matched to postings by `custom_id` (the posting UUID). `extract_postings` submits the batch and stores the batch ID on the `PipelineRun`; a follow-up step collects results when the batch ends, so a slow batch doesn't block scoring of earlier postings.

### 7.4 Fit summary (Ollama, local)

- Model from `RADAR_OLLAMA_MODEL` (start with whatever runs well on John's Mac; a 7B–8B instruct model is a reasonable first try, with Qwen 2.5 3B from rag-pipe as the fallback).
- Input: the `Score` breakdown, matched and missing skills, the extraction, and `resume_text`. Output: plain text, 1–2 sentences, with no new claims beyond what's in the inputs.
- Only runs for postings at or above `RADAR_SUMMARY_MIN_SCORE` (default 60), so slow local inference isn't spent on obvious misses.
- If Ollama isn't running, the stage is skipped and logged. The scores still show; summaries fill in on the next run.

### 7.5 Cost guardrails

- `RADAR_MAX_POSTINGS_PER_RUN` (default 50) caps each run.
- Token usage is stored on every `Extraction`, and `PipelineRun.estimated_cost_usd` adds it up. The runs page shows spend per week.
- `--dry-run` on every LLM command prints what would be sent without calling anything.
- Rough cost estimate: well under $1/month at 50 postings/day on Haiku 5.5 with batching. Check this against real `usage` numbers in week 2.

## 8. Scoring (deterministic)

`radar/scoring.py` is a pure function, `score(extraction, profile, weights) -> ScoreResult`, with no database or network access, so it's easy to test.

| Component | Weight (v1) | How it's computed |
|---|---|---|
| Required skills | 45 | Share of `required_skills` (after alias normalization) found in the profile, with `strong` = 1.0, `working` = 0.7, `learning` = 0.3 |
| Nice-to-have skills | 10 | Same, over `nice_to_have_skills` |
| Seniority | 20 | 1.0 if in `target_seniority`, 0.5 if one level off, 0 otherwise, `unknown` = 0.5 |
| Work mode / location | 15 | 1.0 if work mode and a location match, partial credit otherwise |
| Salary | 5 | 1.0 if `salary_max` ≥ floor or salary unknown, 0 if clearly below |
| Red flags | −5 each | Subtracted, floor at 0 |

- Weights live in settings, and the `formula_version` is stored on every `Score`, so changing the formula is visible and re-runnable.
- `breakdown` stores each component's raw value and weighted points, so the detail page can show "82 = 38 skills + 20 seniority + 15 location + 5 salary + 4 nice-to-have."
- Skills in a posting that aren't in `SkillAlias` or the profile are listed on the admin page, so the alias table grows from real data.

## 9. API (DRF)

Paginated JSON. Session auth locally. In demo mode, read endpoints are open and write endpoints are disabled.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/postings/` | List, filterable by `status`, `min_score`, `work_mode`, `since` |
| GET | `/api/postings/{id}/` | Detail with extraction, score and breakdown |
| PATCH | `/api/postings/{id}/` | Update `status` |
| POST | `/api/postings/manual/` | Submit a URL or raw text; runs every stage synchronously |
| GET / POST | `/api/sources/` | List or add sources |
| GET | `/api/runs/` | Pipeline run history |

## 10. UI

Plain Django templates. Styling is open (see §13).

- **Shortlist** (`/`): this week's new postings sorted by score: title, company, work mode, score, fit summary, top gaps, status buttons.
- **Posting detail** (`/postings/{id}/`): full extraction, the score breakdown laid out as a sum, and a link to the original posting.
- **Tracker** (`/tracker/`): postings marked interested or applied.
- **Runs** (`/runs/`): the last 30 runs with counts, errors and Claude spend.
- **Django admin:** sources, skills profiles, skill aliases, unmatched skills, re-running a stage for one posting.

## 11. Scheduling and deployment

### Local (the real pipeline)
- A `launchd` agent (`~/Library/LaunchAgents/dev.jnutter.jobradar.plist`) runs `uv run manage.py run_pipeline` daily at 7:00 AM. launchd runs missed jobs after the Mac wakes, unlike cron.
- Logs go to a file in the project, and failures show up on the runs page.
- The repo ships the plist as a template plus a `make install-schedule` (or `uv run manage.py install_schedule`) helper.

### Hosted demo
- A single web service on Railway, Fly.io or Render with `RADAR_DEMO_MODE=true`.
- It loads seeded fixtures (about 30 real, public postings with their extractions, a fictional skills profile, and precomputed scores and summaries).
- It has no API keys, no pipeline and no write endpoints, so visitors can't trigger any cost and none of John's personal data is on the server.

### Settings
Env-driven. Start with a single `settings.py`, then split into `settings/base.py`, `dev.py` and `prod.py` (prod = demo) once they diverge.

## 12. Testing and evals

### Unit and integration tests (`pytest` + `pytest-django`)
- Fetchers: recorded fixture responses for Greenhouse, Lever and RSS. No live HTTP.
- Scoring: table-driven tests for each component, alias normalization and red-flag penalties. This is the most heavily tested module.
- Providers: SDK clients mocked. Tests cover parsing, refusal handling, batch result matching by `custom_id`, Ollama-down skipping, and the remote-resume guard.
- Deduplication, soft-delete managers, status transitions, demo-mode write blocking.
- API: DRF endpoint tests for filters and manual entry.

### Evals
- `evals/postings/`: 20–30 real postings saved as text, each with hand-labeled expected fields (seniority, work mode, 5–10 must-find required skills).
- `uv run manage.py run_evals --provider anthropic|ollama` runs extraction and reports per-field accuracy, skill recall and precision, latency and cost per posting.
- **The comparison:** run the same set through Claude Haiku 5.5 and one or two local models, and save the results as a markdown table in `evals/results/`. The README shows that table and explains the choice of production model.
- CI runs evals only when triggered by hand or by a PR label, so routine PRs don't spend money. CI can't reach Ollama, so local-model results are produced on John's Mac and committed.

## 13. Open questions

1. **Building the skills profile:** hand-written list, or have Ollama extract one from the resume once and John edits it in admin? *(Leaning: Ollama extracts, John edits. It's quick to start, stays local, and stays accurate.)*
2. **Score weights:** are the v1 weights in §8 roughly right for how John actually judges a posting? Test them against 10 postings he's already judged by hand.
3. **Which Ollama model** for summaries: pick after a quick side-by-side on John's hardware.
4. **Demo hosting:** Railway, Fly.io or Render. The demo is just a small always-on (or sleep-on-idle) web service with SQLite.
5. **Styling:** Tailwind per the app-project convention, unless John wants otherwise.
6. **Email ingestion** (forwarded job-alert emails): v1 or v2? Locally this could be an IMAP poll rather than an inbound webhook.
7. **Seed sources:** a starter list of 10–20 target companies on Greenhouse or Lever.

## 14. Milestones

| Week | Deliverable |
|---|---|
| 1 | Scaffold (`uv`, Django, DRF, pytest, ruff, CI). Models + migrations. Greenhouse/Lever/RSS fetchers with fixture tests. Admin. Skills profile + alias table. |
| 2 | Provider layer. Claude Haiku extraction with structured output, manual-entry endpoint. Deterministic scorer with full tests. First 10 eval postings labeled; check real token costs. |
| 3 | Batches API in the pipeline. Ollama summaries. `run_pipeline` + `PipelineRun` + launchd agent. Eval set to 20–30; Claude vs. local comparison table. |
| 4 | Dashboard, tracker, runs page. Demo mode + seeded fixtures, deployed. README with architecture diagram, privacy split and eval results. |

## 15. Interview story (what this project demonstrates)

- **LLM APIs:** structured outputs, batch processing, refusal handling, token and cost tracking.
- **Hosted vs. local tradeoff:** public data goes to a cheap hosted model and personal data stays on a local one. The split is enforced in code and backed by eval numbers.
- **Automation:** a multi-stage scheduled pipeline with idempotent, re-runnable stages and an audit log.
- **Explainable scoring:** a deterministic, versioned formula instead of "the LLM said 82."
- **Backend:** Django models, DRF API, soft deletes, UUID keys, env-driven settings, a demo mode that holds no secrets.
- **Quality:** an eval set measuring extraction accuracy across providers and prompt versions.
