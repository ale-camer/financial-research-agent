# Workflow Rules (living document)

These rules apply to the whole life of the project, from issue 0 to the last milestone.
If the way of working changes, update this file in the SAME issue where it changes and
record the change in that issue's `## Decisions`.

## 1. Git Flow
- Two permanent branches: `main` (production, always green) and `develop` (integration).
- NEVER work directly on `main` or `develop`.
- One dedicated branch per issue, created from `develop`: `feature/issue-X-name` or `fix/issue-X-name`.
- Issue branches are merged into `develop` via PR (squash).
- Only `develop` is merged into `main`, when a milestone closes (merge commit, NO squash, so branches never diverge).
- Conventional Commits everywhere: `type(scope): description` with types `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.

## 2. Two-phase cycle per issue
- **Phase A (plan)**: on "Hacé el plan para el issue X", the agent ONLY creates `docs/issue_X_name.md` (Status: Planned). No code, no other files.
- The user runs `make start-issue ID=X NAME=short-name`.
- **Phase B (implementation)**: on "Hacé los puntos del 2 al N de docs/issue_X_name.md", the agent:
  - sets Status to In Progress;
  - implements ONLY those tasks (out-of-scope needs go to `## Decisions` or become a new issue);
  - ALWAYS runs the Verification & Quality Gates task (N+1), even if outside the requested range;
  - ticks the fulfilled Acceptance Criteria with `[x]`, sets Status to Done and reports.
- The user runs `make finish-issue ID=X MSG="type(scope): description"`.
- If the issue is the LAST of its milestone (see `docs/roadmap.md`), the plan includes step N+3 (`make finish-milestone MILESTONE=MX`) and the agent reminds the user in the final report.
- Phase A of the next issue does not start until the user confirms `finish-issue` (and `finish-milestone` if applicable) was run.
- Exception: issue 0 lists the STEP ZERO git commands instead of `make start-issue`.

## 3. Issue file format (identical for every issue)
```
# Issue X: [Issue Name]

**Branch**: `feature/issue-X-short-name`
**Status**: Planned | In Progress | Done
**PR**: opened by `make finish-issue` → `develop` (Closes #X)
**Milestone**: MX - [Milestone Name]

## Objective
## Acceptance Criteria
## Implementation Tasks
### 1. Preparation & Branching
### 2..N. [Task Name]  (File / Change)
### N+1. Verification & Quality Gates
### N+2. Git & Issue Finish
### N+3. Milestone Finish (ONLY if this issue closes the milestone)
## Decisions   (ONLY if autonomous design decisions were made)
```
- No extra or renamed sections.
- Tasks 2..N are atomic: one task = one block = one file (or a small cohesive group of files).
- N+1, N+2, N+3 use their real numbers.

## 4. Makefile and pyproject
- The `Makefile` is self-documenting: `help` is the default target and lists every target.
- Every target calls binaries in `.venv/bin/`, so it never depends on an activated environment.
- Lifecycle targets validate required parameters and abort with a clear message:
  - `start-issue ID NAME [TYPE=feature|fix]`
  - `finish-issue ID MSG` (check → commit → push → PR → squash merge → delete branch → close issue; ID=0 skips "Closes" and `gh issue close`)
  - `finish-milestone MILESTONE` (PR `develop` → `main`, merge commit, tag, close milestone)
- Quality: `venv`, `deps`, `lint`, `format`, `typecheck`, `check`, `security`, `clean`.
- Tests: `test`, `test-unit`, `test-integration`, `test-issue ID=X` (fails if nothing is marked), `ci`.
- `pyproject.toml` holds ruff, mypy (strict) and pytest config, plus optional dependency groups: `dev`, one per layer and `all`.
- pytest runs with `--strict-markers`; every `issue_X` marker must be registered.

## 5. Language
- All code, identifiers, docstrings, commit messages and documentation (README, `docs/`, issues, milestones, `.agents/`) are in ENGLISH.
- Chat replies to the user may be in Spanish.

## 6. Autonomy and decisions
- On technical doubts or open questions, do NOT block: pick the most robust option aligned with the architecture, record it in `## Decisions` (decision + one-line rationale) and move on.
- Autonomy applies to TECHNICAL decisions only. It never justifies ignoring or postponing a question from the user.

## 7. Who runs what
- ONLY the user runs anything that changes git or GitHub state: `make start-issue`, `make finish-issue`, `make finish-milestone`, STEP ZERO, `scripts/bootstrap_github.sh`, and any `git commit/push/checkout/merge` or state-changing `gh ...`.
- The agent may use git read-only (`git status`, `git diff`, `git log`).
- The agent MUST run verification commands: `make venv`, `make deps`, `make format`, `make lint`, `make typecheck`, `make check`, `make test-issue ID=X`, `make test`, `make ci` (and `make security` if present).
- If a command needs network (e.g. `make deps` after adding a dependency), the agent asks for permission or asks the user to run it instead of retrying.

## 8. Quality gate
- Never hand over code unless ruff (lint + format), mypy and the issue tests pass. Minimum: `make check` and `make test-issue ID=X`, both green.
- If something fails, the agent fixes it before reporting.
- Every new test carries `@pytest.mark.issue_X` and the marker is registered in `pyproject.toml` (already pre-registered up to `issue_22`).
- Disabling ruff/mypy rules or using `# noqa` / `# type: ignore` is forbidden unless justified in `## Decisions`.

## 9. Communication
- Ultra-short replies: what was done, whether checks passed, next command.
- End of Phase A:
  ```
  ✅ Plan: docs/issue_X_name.md (N tasks)
  ▶️ Next command: make start-issue ID=X NAME=short-name
  ```
- End of Phase B:
  ```
  ✅ Done: [1-3 lines]
  🧪 Checks: ruff ✅ · mypy ✅ · tests issue_X ✅ (N passed)
  ▶️ Next command: make finish-issue ID=X MSG="type(scope): description"
  🏁 [Only if it closes a milestone] Then: make finish-milestone MILESTONE=MX
  ```
- If the user asks a question, answer it FIRST and do not write code until told to.
- If blocked (hung command, repeated error, missing permissions or network), say so in ONE line with what is needed instead of retrying silently.

## 10. Internal plans
- The single source of truth is `docs/issue_X_name.md`. A plan exists only when that file physically exists in the repo.
- Internal checklists or artifacts are temporary helpers only. If they differ from the file, the file wins, and scope changes are reflected in the file first.
