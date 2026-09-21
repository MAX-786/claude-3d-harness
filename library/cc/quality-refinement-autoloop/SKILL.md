---
name: quality-refinement-autoloop
description: Run a refinement loop when a Blender result is subpar, user expectations are not met, validation fails, or repeated issues reveal a missing method. The loop freezes the work, captures evidence, diagnoses the failing dimension, decides which existing skill repairs it, records the lesson, and repairs the artifact from the correct baseline.
when_to_use: Subpar output, user rejects quality, repeated Blender failure, RALPH loop, skill gap diagnosis.
---

# Quality Refinement Autoloop

> Adapted for claude-3d-harness. The original went on to patch skill files, bump versions and prepare commits.
> Those phases were removed: a job never edits the skill library. See `docs/security-review.md`.

Use this when the user says the result is wrong, ugly, not aligned, not textured, not animated, not exportable, or otherwise below expectation. The goal is not to keep tweaking blindly. The goal is to name the failure, pick the method that addresses it, and only then try again.

## Autoloop phases

### 0. Freeze and preserve

- Stop making product changes immediately.
- Preserve the last accepted baseline and the failed artifact.
- Name the failed branch/version honestly; do not overwrite accepted outputs.

### 1. Evidence capture

Collect the smallest evidence set that proves the failure:

- user feedback quote or summary;
- source/reference files used;
- current output path/version;
- relevant render/contact sheet/overlay/audit report;
- scene/material/object inventory if the failure is inside Blender.

### 2. Diagnose failure dimension

Classify the primary gap:

- geometry / silhouette / landmarks;
- multiview/depth consistency;
- UV / atlas / texture fit;
- closed surface coverage (front/back/side);
- look/material/lighting calibration;
- animation/motion/export truth;
- orchestration/handoff between skills;
- missing validator or missing deterministic helper script.

### 3. Skill-gap decision

Ask: does the current skill stack already contain a generic method for this failure?

- If yes: run the existing skill and repair the artifact.
- If no: say so. Write the gap down as a lesson (what failed, what was tried, what a method for it would need) in the job report, repair with the closest existing method, and tell the user that the result rests on a workaround.
- If repeated failures come from skill interplay, record which handoff failed rather than blaming a leaf skill.

Do not edit, add or patch skill files, helper scripts or manifests. Improving the library is a separate, reviewed change to the harness repository, never a step of a job.

### 4. Repair the product

Rebuild or repair from the correct baseline using the chosen method. Do not reuse rejected outputs unless explicitly marked as source evidence.

## Hard rules

- Do not call overlay curves/planes “texture coverage” unless the real mesh surface also passes coverage gates.
- Do not tune lighting/materials to hide geometry or UV failures.
- Do not claim export support if the effect exists only in Blender Python or a render sequence.
- Do not commit, push, tag or publish anything as part of this loop.

## Recommended artifacts

Save these in the job folder when running the loop:

- `RALPH_OR_QUALITY_LOOP_REPORT.md`
- `failure_evidence/` or references to existing renders/reports
- `skill_gap_decision.json`
- `validation_report.json`

## Scripts

- `scripts/ralph_autoloop_plan.py` creates a generic failure-classification and loop plan from feedback/artifact hints.
