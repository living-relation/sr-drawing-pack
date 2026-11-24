# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: research/render-tests-real-models
Last_Verified_SHA: none
Updated: 2026-11-23 -- Claude (worker for the coordinator), render tests on real models

## Current Goal
- Objective: H34b render tests (ADR-040, ADR-042) on 3 of Daniel's hub models (fuse box, fuel hanger, filament cabinet): UHQ / HQ / DRAFT / FAST DRAFT, 4 views each, with the H40a anti-aliasing fixes before and after; results in docs/RESEARCH.md
- Spec_Ref: docs/SPEC.md#milestones-and-done-criteria

## Active Blocker
- Status: NONE
- Detail: none

## Next Single Step
- [NEXT] Run render_modes.py on the fuse box and the cabinet, then write the RESEARCH section and open the PR

## Done on this branch
- STEP + bom.json exported from local Fusion for all 3 models; each closed unmodified, without saving
- research/render-tests/render_modes.py and fusion_export.py; automation.yml entry
- Fuel hanger run complete

## Pointers
- Branch_States: none
- Backlog: BACKLOG.md
- Latest_ADR: ADR-044
