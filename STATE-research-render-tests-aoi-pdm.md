# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: research/render-tests-aoi-pdm
Last_Verified_SHA: none
Updated: 2026-11-24 -- Claude (claude.ai chat, coordinator, working this branch)

## Current Goal
- Objective: Compile all render tests (OneDrive models only, ADR-047) and get Daniel's pick of two modes and their names (ADR-048, H55).
- Spec_Ref: docs/SPEC.md#milestones-and-done-criteria

## Active Blocker
- Status: BLOCKED
- Detail: waiting on Daniel: H55 (which two modes and names), H53 (PDM external-reference STEP: load Parts or skip)

## Next Single Step
- [NEXT] When research/_local/out/render-tests/fix2/queue.log says QUEUE DONE (16 models-folder STEPs, all fixes, UHQ 600 s), run compile_results.py on fix2, rate each compare.png 1-5, replace the table in docs/RESEARCH.md "All render tests compared", then ask H55 (pick 2 modes + names)

## Pointers
- Branch_States: generated (state_manager.py branches)
- Backlog: BACKLOG.md
- Latest_ADR: ADR-049
- Question_Counter: H56