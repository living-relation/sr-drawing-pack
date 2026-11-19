# SPEC

Owner: Daniel. Agents read this file; they change it only after his yes.
Status: skeleton from `PLAN.md`, **not yet confirmed by Daniel**. Feature detail lives in
`REQUIREMENTS.md` until plan step 0.4 folds it in here.

## Milestones and done criteria

| ID | Milestone | Done when |
|---|---|---|
| M0 | Repo set up | Router, DECISIONS, rules and SPEC in the repo; STATE and BACKLOG in the store; session-start reports no drift |
| M1 | Editing surface chosen | Spikes A and B each report pass / fail per requirement group, including a views row; Daniel picks; recorded in DECISIONS |
| M2 | First iteration | TBD after M1 |

## Interfaces

- Input: Fusion design (f3d preferred, STEP if needed). See ADR-008.
- Output: standard files that open without Fusion. See ADR-004, ADR-013. Format list per drawing purpose: TBD.
- PDM: the app hands files over; the PDM owns state, approval and revs. See ADR-012.
- BOM fields: `part_number`, `description`, `material`, as sr-bom writes them.

## Tolerances and values

- None yet. Title block and sheet values: TBD from the reference drawings.
