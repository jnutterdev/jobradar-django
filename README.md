# Job Radar

A Django app that pulls job postings on a schedule, turns each one into structured data with the Claude API, scores it against my skills profile in plain Python, and writes a short "why it fits / where the gaps are" note with a local Ollama model. A dashboard ranks the week's shortlist.

> **Status:** in progress. The project scaffold, the eval set, and the labeling script (with tests) are done. The ingest → extract → score → summarize pipeline is next. See the [build guide](docs/job-radar-guide.md) for progress.

## Why

1. **Make my job search faster:** less time reading postings that were never a fit.
2. **Show the skills recent postings ask for, in one repo:** building on LLM APIs, scheduled automation pipelines, a REST API, and testing and evaluating LLM output.

## Design principles

- **Only public data leaves the machine.** Posting text goes to Claude. My resume and skills profile never do; the fit summary runs on local Ollama.
- **Deterministic where possible.** Scores are computed in Python from structured fields, so every number can be explained. LLMs only read unstructured text (extraction) and write prose (summaries).
- **Cheap by default.** Claude Haiku with the Batches API for extraction, free local inference for summaries, and a hard cost cap per run.
- **Measured, not assumed.** Model choices are backed by a hand-labeled eval set of real postings.

## Pipeline

| Stage | Runs on | What it does |
| --- | --- | --- |
| Fetch | Local | Pulls postings from public job-board APIs and RSS, deduplicated by content hash |
| Extract | Claude API | Skills, seniority, location, salary, and red flags as structured fields |
| Score | Local Python | Weighted, explainable match against the skills profile |
| Summarize | Local Ollama | 1–2 sentence fit note for postings above a threshold |

Each stage is its own management command, and `run_pipeline` runs them all on a daily schedule. A hosted, read-only demo will run on seeded data with no API keys.

## Stack

Python 3.13, Django, Django REST Framework, SQLite, `uv`, `pytest` + `pytest-django`, Ruff, Doppler for secrets.

## Running it

```sh
uv sync
doppler setup            # or provide env vars another way
uv run manage.py migrate
uv run manage.py runserver
uv run pytest
```

Build the eval label file from the saved postings:

```sh
uv run scripts/job_labeler.py
```

## Docs

- [Tech spec](docs/job-radar-spec.md): architecture, data model, scoring, evals
- [Build guide](docs/job-radar-guide.md): step-by-step plan and progress
