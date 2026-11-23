# SPEC

Owner: Daniel. Agents read this file; they change it only after his yes.
Folded in from the old `PLAN.md` and `REQUIREMENTS.md` on 2026-11-20 with his yes. Why each choice was
made is in [DECISIONS.md](DECISIONS.md). Test evidence is in [RESEARCH.md](RESEARCH.md).

## Milestones and done criteria

| ID | Milestone | Done when |
|---|---|---|
| M0 | Repo set up | Router role table, DECISIONS, rules, SPEC, STATE, BACKLOG and archives exist in the repo (live state at the repo root, workstation #114; Daniel's yes 2026-11-23, H41). LICENSE committed. A fresh agent in this repo can reach Fusion and knows which skills to load. session-start reports the repo state in 3 lines with no drift. |
| M1 | Editing surface chosen (blocks all build work) | Each spike below reports pass / fail per requirement group, with evidence. Daniel picks the surface. Recorded in DECISIONS (ADR-001, ADR-016). |
| M2 | First iteration (after M1) | Every item in the M2 list below works on the test assembly. |
| M3 | Later (outline only) | TBD. See the M3 list below. |

### M1 spikes

The requirements describe an interactive drawing editor: drag views, linked projected views,
add and remove sheets, linked BOM copies, per-view auto annotate. The decision recorded as ADR-001
(add-in + engine that writes PDF/DXF) does not provide that by itself.

| Spike | Action | Done when |
|---|---|---|
| A | Can a native Fusion drawing carry the target style? Test a custom drawing template (sheet 1 title block, simpler continuation sheet), creating a drawing from it through the API, native parts list modes, native revision support (re-test the preview revision table and title block API), custom tables for thumbnails, and a views row: base + projected + iso, plus section and detail. | Pass / fail per requirement group, with evidence. |
| B | Size a custom editor on the handbuilt-cad engine (view model, drag and projection rules, sheet model, linked BOM), with a views row: base + projected + iso, plus section and detail. Evidence for the sheet, BOM and rev table parts comes from sr-drawing-pdf's sheet editor (its view frames are empty); that spike is not repeated here (ADR-020). | Written estimate and the list of hard parts. |

Spike C (DXF into an existing 2D CAD editor) was dropped on 2026-11-23 (Daniel): the editor is our own (ADR-024).
How a picked view becomes 2D geometry: from STEP with the engine (ADR-028); method per model type: ADR-030, ADR-039.

### M2 list

- Test assembly with sub-assemblies, built with sr-cadlib.
- BOM extraction from Fusion: full tree, indented and parts-only, quantities checked against the model.
- Spec-file override of BOM fields (ADR-002).
- Thumbnails (ADR-003).
- Sheet 1 and continuation templates.
- Generation from an open design and from an .f3d on disk.
- Review step: open every generated drawing, or a pick list in batch mode.

### M3 list

- Auto annotation set: item numbers, hole table, callouts, feature dims, weld marks, center lines and marks.
- Export check boxes: PDF and DXF (ADR-018). Fix or document the inch-unit quirk in DXF.
- Port to the Spark Robotic team account on the work PC.

## Requirements (captured from Daniel, 2026-11-19)

### Workflow (Daniel, 2026-11-22, added to SPEC 2026-11-23)

- At creation the user picks the style, sheets, sheet size, default views and an auto-dimension scheme.
- The app then generates most of the drawing: default views placed, automatic dimensions, automatic annotation.
- The engineer has full control over everything already on the sheet, and adds sheets and detail views as needed.
- The editor has built-in agent help or automation for when the engineer wants help while editing.
- Why: ADR-024. The editor is a separate window opened from Fusion (ADR-037).

### Review rule

- No generated drawing is assumed correct unseen.
- Every generated drawing opens for review: annotate, edit, add views, add or remove sheets.
- Batch mode opens all of them, or offers a pick list of which to open after generating.

### Generation

- Auto insert and auto annotate options at generation time, and in the app per sheet or per view.
- Auto-placeable at generation or per sheet: item numbers, hole table, hole and thread callouts,
  feature dimensions, weld marks, hole center lines, hole center marks.

### Views

- Pre-populated views can be dragged and dropped onto sheets.
- Any view can generate projected views. A projected view is a child of the view it came from.
- Children move with the parent. The parent can be dragged anywhere.
- A left or right child, dragged directly, moves only left-right. A top or bottom child only up-down.
- The link can be broken by the user. A freed child moves freely and can make its own projected views.
- Where views come from (saved model orientations, side panel, never rotating the model in the drawing): ADR-021.

### Sheets

- Add or remove sheets.
- Sheet 1 template: full title block and revision table. Only one sheet may use it.
- Continuation template (sheet 2+): drawing number, description, revision, sheet x of x, tolerance
  block. No revision table.
- All sheets share one sheet size and change size together.

### BOM

- Populated accurately from Fusion, showing all sub-assemblies and parts.
- Two modes: indented top-level BOM with thumbnails, or parts-only BOM with thumbnails.
- The BOM can be placed on any sheet.
- Copies can be placed on any sheet and stay linked to the parent BOM.
- Child BOMs are read-only, except rows may be removed, based on the parts visible on the sheet
  where the child was first placed.
- Quantities always match the model. Part visibility never changes the parts listed or their
  quantities in the parent BOM.

### Revision table

- Fully functioning revision table. Model and drawing revision must match.
- Rev format and rules: ADR-011 in [DECISIONS.md](DECISIONS.md).

### Project rules that apply (Custom CAD Designs)

- Drawings are generated from the model, never the other way round.
- The drawing file is saved next to its model. Every assembly and machined part gets a drawing.
- Part models are STEP, usable in Fusion.

## Interfaces

- Input: Fusion design (f3d preferred, STEP if needed). See ADR-008.
- Output: standard files that open without Fusion: PDF and DXF. See ADR-013, ADR-018.
- PDM: the app hands files over; the PDM owns numbers, state, approval and revs, and calls the app to re-export with the rev filled in. See ADR-012, ADR-019, ADR-020, ADR-022.
- BOM fields: `part_number`, `description`, `material`, as sr-bom writes them.

## Tolerances and values

- None yet. Title block and sheet values: TBD from the reference drawings.
