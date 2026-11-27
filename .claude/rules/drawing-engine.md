---
paths: ["SRDrawingPDF/**", "tests/**", "dev/**"]
description: How the drawing engine must draw (exact lines, view modes, hardware outline, speed limits, sheet items). Read before changing SRDrawingPDF.
---
# Drawing engine (how the engine must draw)

Source: Daniel's drawing rules as handed over from sr-drawing-pdf (2026-11-26) and that repo's AGENTS.md.
Where this file and `docs/DECISIONS.md` disagree, DECISIONS wins. Sheet layout rules are in `drawing-style.md`.

## Lines and views
- Lines come from exact solid edges. A mesh is only the GPU visibility (depth) buffer. The old mesh engine is retired.
- Two view modes: DRAFT = XQ Quick, HQ = XQ Exact.
- Visible edges only. Hardware (screws, nuts, washers, standoffs, inserts) draws as its outline only. Hardware is
  found by name with the same rules everywhere (`sheet2d.meshparts.is_hardware`, used by `vieweng.xq.name_is_fastener`).
- Tangent edges show by default, with a per-view option to hide them.
- The user picks each view's scale. Lines shorter than the minimum paper length are dropped.
- Never add a detail view on its own; only suggest one.

## Speed
- More than 120 s to make the views of any assembly is a fail. Targets on the AOI test assembly: Exact cached
  <= 60 s, Exact cold < 120 s.

## Sheet items
- Title block has its own editor: editable layout (tolerance boxes), company logo, saved templates per sheet size.
- "Parts list" means BOM.
- Adding a drawing item: offer the options the SOLIDWORKS drawing editor offers for it (PropertyManager or table
  menu) and cite the SOLIDWORKS help page.
- No assembly instructions such as tightening torque or threadlocker notes.
