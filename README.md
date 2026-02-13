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

## Login Accounts (Default)

Seeded automatically on startup:

- Student: `student1` / `student123`
- Admin: `admin1` / `admin123`
- Reviewer: `reviewer1` / `reviewer123`
- Reviewer: `reviewer2` / `reviewer123`

Login API:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

## Auth Headers

Browser frontend now uses Bearer token auth after login.

For tests/dev fallback, APIs still support headers:

- `X-User-Id`: integer user id
- `X-Role`: `student` / `reviewer` / `admin`
- `X-User-Name`: optional display name

Vue frontend includes a header simulator, so you can switch roles directly in browser.

## Frontend Pages

After opening the app, use top navigation to enter role workspaces:

- `/`: role workbench (my todos + quick entries + recent items)
- `/help`: process help
- `/student/*`: thesis overview, thesis info, upload and submission
- `/admin/*`: dashboard, thesis list, assignment, task operations
- `/reviewer/*`: task list, task detail/download, review form submission

## Admin Assignment Guide

Open `/admin/assign`:

1. Select a `SUBMITTED` thesis.
2. Load reviewer candidates from `GET /api/admin/reviewers?thesis_id=<id>`.
3. Choose reviewers by:
   - `is_conflicted=false` (conflicted reviewers are disabled in UI)
   - lower `active_task_count`
   - higher `available_slots` and `recommendation_score`
4. Click assign to call `POST /api/admin/review-tasks/assign`.

The candidate list includes:

- reviewer basic info (`id`, `name`, `email`)
- workload (`active_task_count`, `submitted_task_count`)
- capacity (`max_task_limit`, `available_slots`)
- conflict check (`is_conflicted`, `conflict_reason`)
- scheduling hint (`latest_assigned_at`, `recommendation_score`)

## Frontend Layouts

- `AuthLayout`: for `/login`, no system topbar/menu.
- `MainLayout`: for authenticated pages, includes topbar + role-based sidebar + main content.

## DevTools Drawer

Identity switching is moved to `DevToolsDrawer` (mock user/role):

- shown in development mode automatically
- or enable with env: `VITE_ENABLE_DEVTOOLS=true`

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
