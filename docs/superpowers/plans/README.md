# Implementation roadmap

| Plan | Day | File | Detail level |
|---|---|---|---|
| 1 | Aug 27 | `2026-08-26-plan-1-foundation.md` | full: tests + code per step (16 tasks) |
| 2 | Aug 28 | `2026-08-28-plan-2-reconcile-act-plan.md` | contracts: files, signatures, test names, behaviour (14 tasks) |
| 3 | Aug 29 | `2026-08-29-plan-3-follow-through-brain.md` | contracts (8 tasks) |
| 4 | Aug 30 | `2026-08-30-plan-4-report-console-evals.md` | contracts (6 tasks) + day-5 checklist |

Spec (source of truth): `../specs/2026-08-26-pm-agent-design.md` (rev 2).

## How we work (human codes, Claude supplies code per task)

1. Start of a session: read the spec, the current plan, and `git log --oneline | head` to see which task is next (commit messages match the plan's commit lines).
2. For the next task, Claude produces **two paste-ready blocks**: the failing tests, then the implementation — exactly the files the task lists, nothing more. For Plans 2–4 the code is written at that moment from the contracts, against the real code that exists by then.
3. The human pastes, runs `uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q`, and commits with the task's commit message. Failures are pasted back verbatim; Claude fixes the code, not the test's intent.
4. One task per exchange. No skipping ahead; no code for a task whose predecessor isn't green.
5. End of each day: the demo line from the spec's §17 table must be true on the deployed service, not just locally.

## Conventions the code must keep
Everything in the spec's §15: strict mypy with no debt list; the import-linter contracts; JSON-native across task boundaries; hand-rolled fakes; behaviour-sentence test names; comments say why; never a secret value in a log or a message; stage files by name; no AI attribution in commits. The model never enqueues, never writes to Linear/Slack/Firestore, never picks an identifier it didn't read.
