# STATE (max 30 lines, overwrite only)
Repo: sr-drawing-pack
Branch: main
Last_Verified_SHA: b4aa9fa
Updated: 2026-11-27 -- Claude (claude.ai chat, coordinator), sr-drawing-pdf joined here (ADR-065)

## Current Goal
- Objective: One repo for rules and engine (ADR-065). Engine: get AOI Exact cached <= 60 s with hardware shown, then fix the v4 defects (BACKLOG 2026-11-27). Then the 3D viewer (ADR-066).
- Spec_Ref: docs/SPEC.md#interfaces

## Active Blocker
- Status: BLOCKED (timing only)
- Detail: no agent link to the work PC (RESEARCH-SPARK-ENGR) from Claude; the AOI STEP is not on DansPC. Question E4.

## Next Single Step
- [NEXT] Time AOI Exact cold/cached and Quick on main with hardware shown, from a scratch clone on the work PC.

## Pointers
- Branch_States: generated (state_manager.py branches)
- Backlog: BACKLOG.md
- Latest_ADR: ADR-067
- Last_Cleanup: 2026-11-23 @ 818b35e
- Question_Counter: E4
