# Job Radar — Build Guide

A step-by-step path from an empty folder to a deployed demo. It goes with [job-radar-spec.md](job-radar-spec.md); section numbers like §6 point there.

## How to use this guide

- **One step per sitting.** Each step is roughly 1–3 hours. Don't read ahead and plan everything up front. Finish a step, commit, and stop.
- **Each step has the same parts:**
  - **Goal:** what's true when you're done.
  - **Build:** the pieces to write.
  - **Think first:** questions to answer *before* coding. Jot your answers in a notes file; they're also good interview material.
  - **Done when:** a check you can actually run. If it doesn't pass, you're not done.
- **When you get stuck,** bring me the step number, what you tried, and the error or the part that doesn't make sense. I'll ask questions before handing you code.
- **Commit at the end of every step** with a message that says what now works.

Checkboxes are there so you can track progress in the file.

---

## Phase 0 — Before any code

### Step 0: Collect your ground truth
- **Goal:** 10 saved postings, each with your own labels and gut score.
- **Build:** a folder `evals/postings/` with one `.txt` per posting and one `labels.json` (or a spreadsheet for now) holding, per posting: seniority, work mode, 5–10 required skills, and your 0–100 gut score.
- **Think first:** what makes *you* say no to a posting in the first 30 seconds? Write it down; it'll shape the red flags and the score weights.
- **Done when:** 10 postings saved and labeled, including at least 2 you'd never apply to.
- [ ] Done

---

## Phase 1 — Foundation (week 1)

### Step 1: Scaffold the project
- **Goal:** an empty Django project that runs, tests, and lints.
- **Build:** `uv init`, add Django/DRF/django-environ and the dev tools (§5), `startproject config .`, `startapp radar`, a `pytest.ini` (or `[tool.pytest.ini_options]` in `pyproject.toml`) pointing at your settings, a `.env.example`, and a `.gitignore` that excludes `.env` and `db.sqlite3`.
- **Think first:** which settings should come from environment variables right now, even before you need them? (Hint: anything that differs between your Mac and the demo.)
- **Done when:** `uv run manage.py runserver` shows the Django welcome page, `uv run pytest` runs (zero tests is fine), `uv run ruff check .` passes, and `.env` is not tracked by git.
- [ ] Done

### Step 2: GitHub + CI
- **Goal:** every push runs tests and lint automatically.
- **Build:** push to a new GitHub repo, then a GitHub Actions workflow that installs `uv`, syncs dependencies, and runs `ruff` and `pytest`.
- **Think first:** what should CI *never* have access to in this project? (Look at §2.)
- **Done when:** a green check on GitHub for your first commit.
- [ ] Done

### Step 3: The `BaseModel`
- **Goal:** an abstract model every other model inherits from (§6).
- **Build:** UUID primary key, `created_at`, `updated_at`, nullable `deleted_at`, a `soft_delete()` method, and two managers: a default one that hides deleted rows and one that includes them.
- **Think first:**
  - If the default manager hides deleted rows, how will the admin show them, or restore one?
  - Should `soft_delete()` call `save()` on the whole object or update just one field? What's the difference?
  - Where should this live: `radar/models.py`, or a separate `core` app?
- **Done when:** tests prove that a soft-deleted row disappears from `Model.objects` but shows up in the all-rows manager. (You'll need a small concrete test model, or wait until Step 4 and test on `Source`.)
- [ ] Done

### Step 4: `Source` and `Posting` models
- **Goal:** the first two real tables, visible in the admin.
- **Build:** both models per §6, with `kind` and `status` as `TextChoices`. Run `makemigrations`, **read the migration file**, then `migrate`. Register both in the admin with useful `list_display` and `list_filter`.
- **Think first:**
  - `url` is unique. What happens if a soft-deleted posting has the same URL as a new one?
  - What should `content_hash` be computed from, and when: in `save()`, or in the fetcher?
- **Done when:** you can create a superuser, log into `/admin`, and add a Source and a Posting by hand.
- [ ] Done

### Step 5: Your first fetcher (Greenhouse)
- **Goal:** turn a Greenhouse board into `Posting` rows.
- **Build:**
  1. In a browser, open `https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true` for a company you're interested in, and look at the JSON shape.
  2. Save that response as `radar/tests/fixtures/greenhouse_<company>.json`.
  3. Write the **test first**: given that fixture, the fetcher returns a list of clean, plain-text postings.
  4. Write `radar/fetchers/greenhouse.py`: a function that takes JSON in and returns posting data out (no database). Strip the HTML here.
- **Think first:** why keep "parse the JSON" separate from "make the HTTP request" and "save to the database"? What does that buy you in tests?
- **Done when:** the fetcher test passes with no network access.
- [ ] Done

### Step 6: `fetch_postings` command + deduplication
- **Goal:** one command pulls every active source into the database, and running it twice adds nothing new.
- **Build:** a management command that loops over active sources, calls the right fetcher with `httpx`, and saves postings. Skip any posting whose URL or `content_hash` already exists. Update `last_fetched_at`.
- **Think first:** if one source fails (timeout, 404), should the whole command fail? What should happen instead?
- **Done when:**
  - The real command pulls live postings into SQLite.
  - Running it a second time adds zero rows.
  - A test with a mocked HTTP response proves the dedupe logic.
- [ ] Done

### Step 7: Lever + RSS fetchers
- **Goal:** two more source types, same pattern.
- **Build:** repeat Step 5 for Lever (`https://api.lever.co/v0/postings/<company>?mode=json`) and for RSS (`feedparser`). Fixture first, test first, then the parser.
- **Think first:** now that you have three fetchers, what do they have in common? Is it worth a shared interface (a `Protocol`), or is a simple dict mapping `kind` → function enough?
- **Done when:** all three source types work from `fetch_postings`, each with a fixture test.
- [ ] Done

**Checkpoint:** you have a working data pipeline with no AI in it at all. That alone is a decent portfolio piece. Take a breath.

---

## Phase 2 — Extraction and scoring (week 2)

### Step 8: `SkillsProfile` + `SkillAlias`
- **Goal:** your skills in the database, with aliases.
- **Build:** both models (§6), admin pages, and a data migration or fixture that seeds 20–30 common aliases (JS → JavaScript, TS → TypeScript, Postgres → PostgreSQL…). Fill in your own profile by hand in the admin for now.
- **Think first:** where should "lowercase it, trim it, look up the alias" live, so that the scorer and the admin both use the same logic?
- **Done when:** your real profile is saved, and a test proves `normalize_skill("js ")` returns `"JavaScript"`.
- [ ] Done

### Step 9: The Pydantic extraction schema
- **Goal:** the shape of a good extraction, written as code (§7.2).
- **Build:** `radar/llm/schemas.py` with `PostingExtraction`. Hand-write the expected extraction for 2 of your Step 0 postings as JSON and validate them against it in a test.
- **Think first:** which fields should be allowed to be `unknown` or null, and which must always be filled? What does the model do if you don't make that clear?
- **Done when:** your two hand-written extractions validate, and an obviously bad one (for example, `seniority: "wizard"`) fails.
- [ ] Done

### Step 10: The deterministic scorer
- **Goal:** `score(extraction, profile, weights)` returns a number and a breakdown (§8), with no AI involved.
- **Build:** `radar/scoring.py` as a pure function, plus table-driven tests: perfect match, no skills, wrong seniority, unknown salary, red flags.
- **Think first:** run your 2 hand-written extractions through it. Do the scores roughly match your gut scores from Step 0? If not, is the formula wrong or your gut?
- **Done when:** tests pass, and you've written down how close the scores came to your gut scores for those 2.
- [ ] Done

### Step 11: Provider layer + Claude extraction
- **Goal:** extract one real posting with Claude Haiku 5.5.
- **Build:** the `Protocol` in `providers/base.py`, then `providers/anthropic.py` using `messages.parse()` with your Pydantic schema (§7.1–7.2). Get an API key from the Anthropic Console and set a spending limit there first. Add a `--dry-run` flag. Bring this step to me when you get here, and we'll look at the current SDK docs together rather than guessing at the API.
- **Think first:**
  - What should happen if the model refuses, the response hits `max_tokens`, or the output fails validation?
  - Which SDK errors are worth retrying, and which aren't?
- **Done when:** one real posting goes in, a valid `Extraction` row comes out, and the input/output token counts are saved. A mocked test covers the failure cases.
- [ ] Done

### Step 12: `extract_postings` + `score_postings` commands
- **Goal:** the pipeline goes from raw postings to scores (no batching yet).
- **Build:** two commands, each processing only rows that still need that stage, respecting `RADAR_MAX_POSTINGS_PER_RUN`.
- **Think first:** how does each command know what's "still needed"? What happens if you change the score formula and want to re-score everything?
- **Done when:** fetch → extract → score works on 10 real postings, and you've checked the real cost per posting against the estimate in §7.5.
- [ ] Done

### Step 13: Manual entry endpoint
- **Goal:** paste a URL or text and get a score back in one request.
- **Build:** a DRF serializer and view for `POST /api/postings/manual/` that runs every stage synchronously.
- **Think first:** what happens if the same URL is submitted twice?
- **Done when:** a `curl` (or the DRF browsable API) returns a scored posting, and a test covers it with a mocked provider.
- [ ] Done

---

## Phase 3 — Batching, local summaries, scheduling (week 3)

### Step 14: Batches API
- **Goal:** the scheduled run extracts at half price.
- **Build:** submit unextracted postings as one batch with `custom_id` = posting UUID, store the batch ID, and collect results later (§7.3).
- **Think first:** results come back in any order and some may fail. How do you make "collect results" safe to run twice?
- **Done when:** a real batch of 10 completes and every result lands on the right posting.
- [ ] Done

### Step 15: Ollama summaries
- **Goal:** fit summaries written locally (§7.4).
- **Build:** `providers/ollama.py`, the `summarize_postings` command, the score threshold, skip-if-Ollama-is-down handling, and the remote-resume guard from §7.1.
- **Think first:** how will you test the privacy guard? What exactly should the test assert?
- **Done when:** postings scoring 60 or more get a summary, stopping Ollama makes the stage skip cleanly, and the guard test passes.
- [ ] Done

### Step 16: `run_pipeline` + `PipelineRun`
- **Goal:** one command runs everything and records what happened.
- **Build:** the orchestrating command, the `PipelineRun` model, status logic (`succeeded`, `partial`, `failed`), and cost totals.
- **Think first:** what counts as `partial` versus `failed`?
- **Done when:** a run shows up in the admin with accurate counts, and a deliberately broken source produces `partial`, not a crash.
- [ ] Done

### Step 17: Schedule it with launchd
- **Goal:** the pipeline runs every morning without you.
- **Build:** the plist template and an install helper (§11). Logs go to a file.
- **Done when:** it runs on its own the next morning, and you can see that run on the runs page (or in the admin).
- [ ] Done

### Step 18: The eval runner
- **Goal:** numbers behind your model choice (§12).
- **Build:** grow `evals/postings/` to 20–30, write `run_evals --provider anthropic|ollama`, and produce a markdown results table.
- **Think first:** what's a "correct" skill match? Exact string, after aliasing, or close enough? Decide before you see the numbers, not after.
- **Done when:** a committed table compares Haiku with at least one local model on accuracy, skill recall, latency and cost.
- [ ] Done

---

## Phase 4 — UI, demo, polish (week 4)

### Step 19: Shortlist + detail pages
- **Build:** the templates from §10. Set up Tailwind first (or decide on open question #5).
- **Done when:** you'd actually use the shortlist on a Monday morning.
- [ ] Done

### Step 20: Tracker + runs pages
- **Done when:** you can mark a posting applied and see it move, and the runs page shows the last 30 runs with costs.
- [ ] Done

### Step 21: Demo mode + seed data
- **Build:** `RADAR_DEMO_MODE`, write endpoints blocked, a fictional profile, and a fixture of public postings with precomputed results.
- **Think first:** go over the fixture once more. Does anything in it point back to your real profile or resume?
- **Done when:** with demo mode on, a fresh database loaded from fixtures looks complete, and nothing can write or call an API.
- [ ] Done

### Step 22: Deploy the demo
- **Build:** pick the host (open question #4) and deploy the web service only.
- **Done when:** a public URL works, holds no secrets, and survives a redeploy.
- [ ] Done

### Step 23: README
- **Build:** what it is, the architecture diagram, the privacy split, the scoring formula, the eval table, how to run it locally, and what you'd do next.
- **Done when:** someone who's never seen it understands the project in five minutes. Try it on a friend.
- [ ] Done

---

## Concepts you'll meet along the way

If something here is new, it's worth 20 minutes of reading before the step that uses it:

| Concept | First used in |
|---|---|
| Abstract models, custom managers and querysets | Step 3 |
| Migrations and reading them before applying | Step 4 |
| `TextChoices` | Step 4 |
| Test fixtures, mocking HTTP (`respx` for `httpx`, or `unittest.mock`) | Step 5 |
| Management commands | Step 6 |
| `typing.Protocol` | Step 7 |
| Pydantic models and validation | Step 9 |
| Table-driven tests (`pytest.mark.parametrize`) | Step 10 |
| DRF serializers and views | Step 13 |
| Idempotency | Steps 6, 14 |
| launchd plists | Step 17 |
