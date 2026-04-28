# Paper Review Platform (MVP)

当前这套系统默认按“正式可用”方式启动，不再自动灌入学生和教师演示账号。

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

## Default Account

默认只会自动创建 1 个管理员账号：

- 管理员：`admin` / `admin`

首次登录后系统会强制要求修改密码，修改完成后才能继续使用。

系统启动时不会自动创建学生和教师账号。需要登录管理员后，通过以下方式补充：

- 教师管理页手动新增
- 学生管理页手动新增
- 教师 / 学生 Excel 导入

Login API:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/change-password`
- `POST /api/auth/logout`

## Auth Headers

Browser frontend now uses Bearer token auth after login.

For tests/dev fallback, APIs still support headers:

- `X-User-Id`: integer user id
- `X-Role`: `student` / `reviewer` / `admin`
- `X-User-Name`: optional display name

正常使用时不需要手工传这些头。它们主要用于测试和开发态接口联调。

## Frontend Pages

After opening the app, use top navigation to enter role workspaces:

- `/`: role workbench (my todos + quick entries + recent items)
- `/help`: process help
- `/student/*`: thesis overview, thesis info, upload and submission
- `/admin/*`: dashboard, thesis list, assignment, task operations
- `/admin/reviewers`: reviewer account management (create/update/enable-reset)
- `/admin/students`: student account management (create/update/enable-reset)
- `/account/password`: current user password change page
- `/reviewer/*`: task list, task detail/download, review form submission

## Account Management Notes

- 所有角色登录后都可以从左侧菜单进入“修改密码”页面
- 管理员可以重置教师和学生密码
- 教师管理和学生管理都支持 Excel 模板下载与 Excel 导入
- 导入时可以为本次导入账号指定默认初始密码

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
- reviewer department quota (`department_assigned_count`, `department_max_limit`)

Department assignment rule (Rule B):

- each reviewer belongs to a `department`
- per thesis, the same department can have at most `N` reviewers
- configure `N` by env `MAX_REVIEWERS_PER_DEPARTMENT` (default `1`)

Admin task operation page (`/admin/tasks`) now uses task list selection flow:

- first load and select target review task from `GET /api/admin/review-tasks`
- then execute replace/cancel/return operations with visible thesis + reviewer context

Admin assignment supports auto mode for unassigned theses:

- `POST /api/admin/review-tasks/auto-assign`
- assign reviewers automatically by existing conflict + department quota + workload rules

Reviewer management APIs:

- `GET /api/admin/reviewers/manage`
- `POST /api/admin/reviewers`
- `PATCH /api/admin/reviewers/{reviewer_id}`
- `POST /api/admin/reviewers/{reviewer_id}/toggle-active`
- `POST /api/admin/reviewers/{reviewer_id}/reset-password`

Student management APIs:

- `GET /api/admin/students/manage`
- `POST /api/admin/students`
- `PATCH /api/admin/students/{student_id}`
- `POST /api/admin/students/{student_id}/toggle-active`
- `POST /api/admin/students/{student_id}/reset-password`

Student thesis helper API:

- `GET /api/thesis/advisors` for advisor dropdown options on thesis create page
- advisor is required when creating thesis (`POST /api/thesis/my`)
- student can update advisor only when thesis status is `DRAFT` (`PUT /api/thesis/{thesis_id}`)
- thesis versions use per-thesis sequence `version_no` (V1, V2...), not global id

## Frontend Layouts

- `AuthLayout`: for `/login`, no system topbar/menu.
- `MainLayout`: for authenticated pages, includes topbar + role-based sidebar + main content.

## DevTools Drawer

Identity switching is moved to `DevToolsDrawer` (mock user/role):

- shown in development mode automatically
- or enable with env: `VITE_ENABLE_DEVTOOLS=true`
- supports one-click dev data generation via `/api/dev/*` endpoints

说明：

- 这是开发辅助能力，不属于正式使用流程
- 正式启动时默认账号仍只有 `admin / admin`

## Dev Seed APIs

Enabled when:

- `APP_ENV != production` (default)
- and `ENABLE_DEV_ENDPOINTS=true` (default in non-production)

Endpoints:

- `GET /api/dev/accounts`
- `POST /api/dev/seed/users`
- `POST /api/dev/seed/workflow`
- `POST /api/dev/reset`

`POST /api/dev/seed/users` supports `student_thesis_status`:

- `NO_THESIS`
- `FINAL_UPLOADED`
- `REVIEW_REQUESTED`

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
