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
- Detail: waiting on Daniel (restate in full each reply). B1: after fix2, pick 2 render modes (one very fast that may give up line quality, one accurate high-quality that may take longer) and name them by what they give (ADR-048). B2: add the 2-character question-ID rule (1 capital letter + 1 digit, choices 1 lower-case letter) to workstation-core? a = yes, separate workstation PR (recommended); b = this repo only. B3: session hook now injects a fusion-desktop app lock, but AGENTS.md says the Fusion lock is retired (2026-11-22); which wins? a = use the lock, update AGENTS.md (recommended); b = keep retired here.

## Next Single Step
- [NEXT] When research/_local/out/render-tests/fix2/queue.log says QUEUE DONE (16 models-folder STEPs, all fixes, UHQ 600 s), run compile_results.py on fix2, rate each compare.png 1-5, replace the table in docs/RESEARCH.md "All render tests compared", then ask B1 (pick 2 modes + names)

## Pointers
- Branch_States: generated (state_manager.py branches)
- Backlog: BACKLOG.md
- Latest_ADR: ADR-050
- Question_Counter: B3