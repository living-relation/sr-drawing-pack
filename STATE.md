# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: main
Last_Verified_SHA: none
Updated: 2026-11-23 -- Claude worker (moved from the store into the repo)

## Current Goal
- Objective: M1 decided (editor ADR-024/037; views from STEP + sr-export bom.json ADR-028/029; render modes ADR-040/042). Now: render tests on Spark hub models in local desktop Fusion (H34b, ADR-042), then the M2 build plan for Daniel's yes. Single coordinator: the claude.ai "Fusion SR Drawing Tool" project chat. Drift watcher re-runs every 4 h (send_later in this chat).
- Spec_Ref: docs/SPEC.md#milestones-and-done-criteria

## Active Blocker
- Status: BLOCKED
- Detail: waiting on Daniel: H39 (where docs/DATA-CARD.md goes: no sparkCAD PDM repo exists yet)

## Next Single Step
- [NEXT] Find the test models in the Spark hub (filament cabinet, RTR, AOI, PDM, fuse boxes, fuel hanger), export STEP + bom.json with sr-export in local Fusion, run UHQ/HQ/DRAFT/FAST DRAFT with tangent drawn and the anti-aliasing fixes; results to docs/RESEARCH.md

## Pointers
- Branch_States: generated (state_manager.py branches)
- Backlog: BACKLOG.md
- Latest_ADR: ADR-042
- Last_Cleanup: 2026-11-23 @ ba08c78
- Question_Counter: H41
