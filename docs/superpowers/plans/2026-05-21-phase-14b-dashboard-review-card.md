# Phase 14B Dashboard Experiment Review Card Plan

**Goal:** Render experiment review drafts inside the existing read-only dashboard so manual replay has questions, risk flags, focus trades, and learning tasks in the same workspace as the K-line and backtest report.

**Scope:**

- Keep the dashboard local and read-only.
- Use `/api/experiment-review?experiment=...`.
- Show generated previews when no persisted draft exists.
- Let focus-trade buttons locate the corresponding trade on the K-line.
- Preserve old local databases that do not yet have `experiment_review_drafts`.

## Tasks

- [x] Add static tests for review-card HTML and JS markers.
- [x] Add review draft UI containers to the dashboard report workspace.
- [x] Load experiment review data after loading an experiment replay.
- [x] Render summary, risk flags, focus trades, questions, and learning tasks.
- [x] Connect focus-trade location buttons to the existing `focusTrade` behavior.
- [x] Add old-database fallback when `experiment_review_drafts` is missing.
- [x] Run targeted tests, full tests, JS syntax check, and browser QA.
