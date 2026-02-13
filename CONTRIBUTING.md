# Contributing Guide

## 1. Branch Strategy

- `main`: always releasable.
- `feat/*`: new features.
- `fix/*`: bug fixes.
- `chore/*`: tooling/config/maintenance.
- `docs/*`: documentation updates.
- `test/*`: test-only changes.

Branch naming examples:

- `feat/student-upload-versioning`
- `fix/reviewer-submit-status-sync`
- `chore/add-git-workflow-rules`

## 2. Commit Convention

Use Conventional Commits:

`<type>(optional-scope): <short summary>`

Allowed `type` values:

- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `chore`
- `perf`
- `build`
- `ci`

Examples:

- `feat(student): support final thesis upload with versioning`
- `fix(admin): enforce advisor conflict check on assignment`
- `test(workflow): add end-to-end review lifecycle coverage`

Rules:

- Keep subject <= 72 characters.
- Use imperative mood (e.g. `add`, `fix`, `remove`).
- One logical change per commit.

## 3. Local Development Flow

1. Sync latest main:
   `git checkout main && git pull`
2. Create branch:
   `git checkout -b feat/your-topic`
3. Develop and test:
   `python -m pytest -q`
4. Commit with conventional message.
5. Push and open PR to `main`.

## 4. Pull Request Requirements

- PR title follows commit convention format.
- Include clear description of:
  - Goal
  - Main changes
  - Test evidence
  - Risks / rollback plan
- Link related task file under `tasks/`.
- Ensure tests pass locally before requesting review.

## 5. Recommended Hooks and Linting (Optional)

If you want commit message validation:

1. Install Node.js.
2. Add commitlint packages:
   `npm i -D @commitlint/cli @commitlint/config-conventional`
3. Use project `.commitlintrc.json`.
4. Wire a `commit-msg` hook to run:
   `npx --no -- commitlint --edit "$1"`

