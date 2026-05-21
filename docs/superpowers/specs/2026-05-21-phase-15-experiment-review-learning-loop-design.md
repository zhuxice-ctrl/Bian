# Phase 15 Experiment Review Learning Loop Design

## Goal

Turn one saved backtest experiment review draft into durable learning-loop records through a Chinese Brain command.

## User Command

Primary user-facing command:

```text
沉淀实验复盘 实验=EXPERIMENT_ID 日期=2026-05-21
```

The command is normalized to an internal Brain command so existing audit logging and local-only execution rules continue to apply.

## Behavior

The command reads the requested experiment review draft. If no draft exists, it generates and persists one through the existing experiment review path. It then writes the learning loop:

- A daily review for the requested date, derived from the experiment summary and risk flags.
- One knowledge card for each review question and learning task.
- Tags for the generated knowledge cards, based on draft risk flag codes.
- A review-to-experiment link.
- Review-to-knowledge links for generated cards.
- A daily learning report for the same date.

Existing records are updated or ignored where uniqueness already exists, so rerunning the same command is safe and does not duplicate links.

## Boundaries

This phase does not add dashboard writes, trading actions, live order logic, or external AI calls. It reuses deterministic review drafts and SQLite storage only.

## Testing

Tests should cover the Chinese alias, the Brain command's persistence behavior, idempotent reruns, missing experiment handling, and learning report generation.
