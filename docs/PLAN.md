# SR Drawing Pack: coordinator plan (draft 1, 2026-11-19)

Draft written before `state-init` has run. Once the store exists, live status moves to the store's
STATE and BACKLOG files and this file keeps only the plan.

## Coordination model

- One coordinator chat owns the plan and the root STATE. Workers are dispatched from it, one branch each.
- Every repo change goes through `safe-repo-preflight`: branch, checks, PR. No force-push. Pulls are fast-forward only.
- Read-only sources: everything in [REFERENCES.md](REFERENCES.md). Copy in, never edit there.
- Nothing is installed into Fusion's AddIns folder until Daniel approves an iteration.
- Never walk the Fusion cloud hub recursively (it crashed Fusion once).

## Phase 0: set up the repo (run in order, each one interrogates Daniel)

| Step | Action | Done when |
|---|---|---|
| 0.1 | Run `state-init`. Let it ask its questions and pick the repo profile. | Router role table, DECISIONS, rules, SPEC exist in the repo; STATE, BACKLOG, archives exist in the store. |
| 0.2 | Run `coordinator-kit`. Confirm who owns which STATE file and how workers are dispatched. | Coordinator and worker STATE layout agreed and written. |
| 0.3 | Run `session-start`. | It reports the repo state in 3 lines with no drift. |
| 0.4 | Fold [REQUIREMENTS.md](REQUIREMENTS.md) into SPEC and DECISIONS. Flag conflicts. | Every line in REQUIREMENTS is in SPEC, DECISIONS, or BACKLOG. |
| 0.5 | Decide the license (Q2). Repo is personal now, to be handed to Spark Robotic later. | LICENSE committed. |
| 0.6 | Declare agent tooling in the repo: AGENTS.md required-skills list, `.mcp.json` for the Fusion MCP (Q3). | A fresh agent in this repo can reach Fusion and knows which skills to load. |

## Phase 1: decide the editing surface (blocks all build work)

The requirements now describe an interactive drawing editor: drag views, linked projected views,
add and remove sheets, linked BOM copies, per-view auto annotate. The decision recorded as D1
(add-in + engine that writes PDF/DXF) does not provide that by itself. See Q1.

| Step | Action | Done when |
|---|---|---|
| 1.1 | Spike A: can a native Fusion drawing carry the target style? Test a custom drawing template (sheet 1 title block, simpler continuation sheet), creating a drawing from it through the API, native parts list modes, native revision support, and custom tables for thumbnails. | Pass / fail per requirement group, with evidence. |
| 1.2 | Spike B: size a custom editor on the handbuilt-cad engine (view model, drag and projection rules, sheet model, linked BOM). | Written estimate and the list of hard parts. |
| 1.3 | Spike C: engine output opened in an existing 2D CAD editor via DXF/DWG. Record which links survive. | Pass / fail per requirement group. |
| 1.4 | Daniel picks the surface. Record in DECISIONS. | Q1 closed. |

## Phase 2: first iteration (after Q1)

- Test assembly with sub-assemblies, built with sr-cadlib.
- BOM extraction from Fusion: full tree, indented and parts-only, quantities checked against the model.
- Spec-file override of BOM fields (D2).
- Thumbnails (D3).
- Sheet 1 and continuation templates.
- Generation from an open design and from an .f3d on disk.
- Review step: open every generated drawing, or a pick list in batch mode.

## Phase 3 and later (outline only)

- Auto annotation set: item numbers, hole table, callouts, feature dims, weld marks, center lines and marks.
- Export check boxes: PDF, DXF, DWG. Fix or document the inch-unit quirk in DXF.
- Port to the Spark Robotic team account on the work PC.

## Open questions

| ID | Question | Blocks |
|---|---|---|
| Q1 | Editing surface: native Fusion drawing, custom editor, or external 2D CAD? | Phase 2 onward |
| Q2 | Answered: personal now (living-relation), hand to Spark Robotic later. License still open. | 0.5 |
| Q3 | Commit skills into this repo, or only declare them in AGENTS.md? | 0.6 |
| Q4 | "Click thumbnail to expand": where does this happen (Fusion palette, the editor, the PDF)? | Thumbnail design |

## Test evidence so far

See [RESEARCH.md](RESEARCH.md).
