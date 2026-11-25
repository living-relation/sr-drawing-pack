# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: research/render-tests-aoi-pdm
Last_Verified_SHA: none
Updated: 2026-11-24 -- Claude (claude.ai chat, coordinator, working this branch)

## Current Goal
- Objective: Render modes that meet ADR-051 (over 2 min from STEP = fail) on all models-folder STEPs (ADR-047), then Daniel picks 2 modes and names them (ADR-048).
- Spec_Ref: docs/SPEC.md#milestones-and-done-criteria

## Active Blocker
- Status: BLOCKED
- Detail: waiting on Daniel (restate in full each reply). B1: pick 2 render modes and name them; XQ (exact edges, GPU depth buffer) passes ADR-051 on all 16 models (max 88 s from STEP), UHQ and FAST fail. B2: add the 2-character question-ID rule to workstation-core? a = yes, separate workstation PR (recommended); b = this repo only. B3: session hook adds a fusion-desktop app lock, but AGENTS.md says the Fusion lock is retired (2026-11-22); which wins? a = use the lock, update AGENTS.md (recommended); b = keep retired here. B5: next speed step for big assemblies (STEP read is 48 % of the worst time)? a = cache by STEP file hash (recommended); b = parallel STEP read in worker processes; c = stop here.

## Next Single Step
- [NEXT] Get B1; record it as an ADR; then build the picked modes into the drawing engine path (xq_render.py output -> sheet + DXF + PDF) and add the sparkCAD data hook (BACKLOG 2026-11-24).

## Pointers
- Branch_States: generated (state_manager.py branches)
- Backlog: BACKLOG.md
- Latest_ADR: ADR-051
- Question_Counter: B5
