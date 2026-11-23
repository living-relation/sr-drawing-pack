---
description: House drawing style for every sheet this repo makes or tests (template, views, labels, dimensions, holes, render modes). Read before making or changing any drawing.
---
# Drawing style (how every sheet is made)

Source: Daniel's instruction of 2026-11-22 (follow the style note), reconciled with DECISIONS. Where this file and
`docs/DECISIONS.md` disagree, DECISIONS wins. The engine's own rule list is handbuilt-cad `drawing/DRAWING-RULES.md`.

## Sheet and template
- Size B, 11x17 in landscape (431.8 x 279.4 mm). Double border, 8 x 4 zone grid (8..1 across, D..A down).
- Title block bottom right: COMPANY / PROJECT, TITLE, PART / DWG NO., REV, MATERIAL (`SEE BOM` on an assembly),
  SCALE (the sheet scale), UNITS (mm), SIZE `B (11x17)`, SHEET `n OF N`, DATE (yyyy-mm-dd), DRAWN, SOURCE (the STEP
  name), third-angle symbol. Every field filled on a released sheet. REV equals the newest rev-log row (ADR-011).
- DRAWN and BY are a person's initials from the drawing-initials setting, never an agent or tool name.
- Sheet 1: REVISIONS table top right (Rev | Description | By | Date dd/mm/yy, newest 6 rows, Rev A = `Initial`).
  Sheet 2 and on: the continuation block (SPEC), no rev table. Add a sheet only when it carries content.
- Tolerance block bottom centre-left. Notes block bottom left, numbered, upper case.
- No edge-break, torque or threadlocker note unless Daniel asks for one (edge breaks: DRAWING-RULES 19).
- DejaVu Sans fonts embedded as subsets. Text 3.0 mm; view and section labels 3.5 mm bold.

## Views
- Visible edges only. Never hidden lines, in any view, and no switch for them (ADR-033).
- Lines are smooth and continuous and never look like a mesh, whatever the model is (ADR-039). A mesh body is drawn
  from its creases and silhouettes, never from its triangles.
- Render modes per view (ADR-040): UHQ exact B-rep, HQ fast joined, DRAFT fast pieces, FAST DRAFT mesh creases and
  silhouettes. Released files use HQ or UHQ.
- Tangent edges: three settings per view, hidden, drawn or partial (ADR-040). Default: drawn, thin solid, in every
  view (this differs from handbuilt-cad DRAWING-RULES 16 on purpose).
- Centre marks on every visible hole and on arcs of 150 deg or more.
- Third-angle projection: top above front, right to the right, aligned.
- One sheet scale, set by the template: the largest standard scale that fits with room for dimensions (ADR-035).
- Labels (ADR-026): default views (front, top, right, left, back, bottom, trimetric, isometric) get no label and no
  scale. A view at another scale, or one the user labels, gets a subtitle. Detail views: letter and scale
  (`DETAIL B  SCALE 3:1`). Section views: cutting line with arrows and letters, label `SECTION A-A`, plus scale if
  different (ADR-035).
- Sections are capped (solid, hatched cut faces); in assemblies parts are hatched in different directions and
  fasteners are not cut.
- A detail view is made only when it carries a dimension, callout or fit.

## Dimensions and holes
- Each key dimension once, in the view where the feature is true size; repeats as `4X` / `(xN)`. No unit suffix.
- Assemblies: overall sizes as reference dimensions in parentheses (ADR-006). Hole positions and fabrication-critical
  sizes go in dimensioned assembly sections and details, never separate part sheets (ADR-034).
- Tolerance by decimals: the tolerance block sets the tolerance per number of decimal places; each dimension shows
  the default decimals or more or fewer, as the user sets it; hole tables per row or per table (ADR-038).
- Hole callouts in ISO syntax: through holes `THRU`, no depth; tapped holes thread plus tap drill; blind holes the real
  thread depth and the drill depth when deeper. Never invent a depth (ADR-034, DRAWING-RULES 21a).
- The model drives the drawing: change the model or spec and regenerate; never hand-edit a PDF or DXF.

## Balloons and BOM
- The drawing carries its own BOM; every row links to its part in every view (ADR-029). Balloon number = BOM item.
- A finished sub-assembly is one item and one balloon in its parent (ADR-034).
- Leaders end on a visible line of their own part, never cross linework where avoidable, never overlap.
- Thumbnails may live in an external BOM file (ADR-036), made with F3D (ADR-039).

## Self-check before showing a sheet
Open every PNG at print scale: no hidden lines; no mesh look; centre marks on holes; sections and details lettered;
labels per the rules above; title block filled and REV matching the rev log; rev table and BOM present; BOM,
balloons and quantities agree (count, do not eye); nothing overlaps or leaves the sheet; callouts per the rules
above; no edge-break, torque or threadlocker notes. The engine's `<pdf>.checks.json` says `ok: true`.
