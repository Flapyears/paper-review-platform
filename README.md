# Paper Review Platform (MVP)

## Quick Start

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Auth Headers

All APIs use headers for MVP auth:

- `X-User-Id`: integer user id
- `X-Role`: `student` / `reviewer` / `admin`
- `X-User-Name`: optional display name

## Run Tests

```bash
python -m pytest -q
```

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

- Trigger: `push` and `pull_request`
- Job: install dependencies and run `python -m pytest -q`

## Implemented Phase Docs

- `tasks/task01.md`
- `tasks/task02.md`
- `tasks/task03.md`
- `tasks/task04.md`
