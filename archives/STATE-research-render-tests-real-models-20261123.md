# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: research/render-tests-real-models
Last_Verified_SHA: none
Updated: 2026-11-23 -- Claude (worker for the coordinator), render tests on real models done

## Current Goal
- Objective: H34b render tests (ADR-040, ADR-042) on 3 hub models (fuse box, fuel hanger, filament cabinet): UHQ / HQ / DRAFT / FAST DRAFT, 4 views each, H40a anti-aliasing fixes before and after. Done; results in docs/RESEARCH.md "Render tests on real models (2026-11-23)"
- Spec_Ref: docs/SPEC.md#milestones-and-done-criteria

## Active Blocker
- Status: NONE
- Detail: none

## Next Single Step
- [NEXT] Coordinator: review and merge the PR; take the DRAFT-mode question (BACKLOG 2026-11-23) to Daniel

## Done on this branch
- STEP + sr-export bom.json from local Fusion for all 3 models; each closed unmodified, without saving
- research/render-tests/render_modes.py and fusion_export.py; automation.yml entry; AGENTS.md map line
- Results: HQ + fixes 5-20 s for 4 views and right on all 3; UHQ 46-157 s, but 3 of 4 fuel hanger views timed out at 120 s; FAST DRAFT slower and dashed on B-rep; F3D 4.0.1 accepts --anti-aliasing=ssaa
- 6 BACKLOG lines (2026-11-23, render tests)

## Pointers
- Branch_States: none
- Backlog: BACKLOG.md
- Latest_ADR: ADR-044
