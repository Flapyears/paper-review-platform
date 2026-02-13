# Paper Review Platform (MVP)

## Quick Start

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open frontend workbench: `http://127.0.0.1:8000/`

## Frontend (Vue)

### Development mode

```bash
cd frontend
npm install
npm run dev
```

Then open `http://127.0.0.1:5173/` (API requests are proxied to `http://127.0.0.1:8000`).

### Build and serve by FastAPI

```bash
cd frontend
npm install
npm run build
```

After build, start backend:

```bash
uvicorn app.main:app --reload
```

FastAPI will serve `frontend/dist` at `http://127.0.0.1:8000/` with SPA fallback routing.

## Auth Headers

All APIs use headers for MVP auth:

- `X-User-Id`: integer user id
- `X-Role`: `student` / `reviewer` / `admin`
- `X-User-Name`: optional display name

Vue frontend includes a header simulator, so you can switch roles directly in browser.

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
