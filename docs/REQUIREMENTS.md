# Requirements captured from Daniel (2026-11-19)

Raw capture, not yet a spec. `state-init` / the SPEC step turns this into the real SPEC.

## Decisions made

Moved to [DECISIONS.md](DECISIONS.md) (D1 to D10 are ADR-001 to ADR-010).

## Review rule

- No generated drawing is assumed correct unseen.
- Every generated drawing opens for review: annotate, edit, add views, add or remove sheets.
- Batch mode opens all of them, or offers a pick list of which to open after generating.

## Generation

- Auto insert and auto annotate options at generation time, and in the app per sheet or per view.
- Auto-placeable at generation or per sheet: item numbers, hole table, hole and thread callouts,
  feature dimensions, weld marks, hole center lines, hole center marks.

## Views

- Pre-populated views can be dragged and dropped onto sheets.
- Any view can generate projected views. A projected view is a child of the view it came from.
- Children move with the parent. The parent can be dragged anywhere.
- A left or right child, dragged directly, moves only left-right. A top or bottom child only up-down.
- The link can be broken by the user. A freed child moves freely and can make its own projected views.

## Sheets

- Add or remove sheets.
- Sheet 1 template: full title block and revision table. Only one sheet may use it.
- Continuation template (sheet 2+): drawing number, description, revision, sheet x of x, tolerance
  block. No revision table.
- All sheets share one sheet size and change size together.

## BOM

- Populated accurately from Fusion, showing all sub-assemblies and parts.
- Two modes: indented top-level BOM with thumbnails, or parts-only BOM with thumbnails.
- The BOM can be placed on any sheet.
- Copies can be placed on any sheet and stay linked to the parent BOM.
- Child BOMs are read-only, except rows may be removed, based on the parts visible on the sheet
  where the child was first placed.
- Quantities always match the model. Part visibility never changes the parts listed or their
  quantities in the parent BOM.

## Revision table

- Fully functioning revision table. Model and drawing revision must match.
- Rev format and rules: ADR-011 in [DECISIONS.md](DECISIONS.md).

## Project rules that apply (Custom CAD Designs)

- Drawings are generated from the model, never the other way round.
- The drawing file is saved next to its model. Every assembly and machined part gets a drawing.
- Part models are STEP, usable in Fusion.
