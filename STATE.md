# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: main
Last_Verified_SHA: none
Updated: 2026-11-23 -- Claude (claude.ai chat), coordinator handoff to a new chat

## Current Goal
- Objective: M1 decided (ADR-024/028/029/037/040/042). Now: render tests on Daniel's real models in local desktop Fusion (H34b, ADR-042), then the M2 build plan in SPEC for Daniel's yes (H34a). Coordinator: a new claude.ai "Fusion SR Drawing Tool" project chat.
- Spec_Ref: docs/SPEC.md#milestones-and-done-criteria

## Active Blocker
- Status: BLOCKED
- Detail: waiting on Daniel: H43 (RTR file name; AOI and PDM file picks), H44 (re-run session-start), H45 (watcher scope)

## Next Single Step
- [NEXT] Check the render-test worker branch research/render-tests-real-models (fuse box rev7, FH-200, FC5-000 Rev H; uncommitted in the main clone at handoff): finish or review its PR, merge when green, then run the H43 models

## Pointers
- Branch_States: generated (state_manager.py branches)
- Backlog: BACKLOG.md
- Latest_ADR: ADR-044
- Last_Cleanup: 2026-11-23 @ 818b35e
- Question_Counter: H45
