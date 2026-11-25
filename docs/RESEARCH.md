# Research and test results (2026-11-19)

Tested on the test PC, Fusion 2706.1.17, through the autodesk-fusion-mcp add-in (`execute_python`).
Each tool's own code was run inside Fusion against a throwaway test plate (80 x 50 x 10 mm, four
6 mm holes, one pocket). No tool was installed as a Fusion add-in, so their buttons and dialogs are
untested. Test scripts: `research/fusion-tests/` (paths were rewritten after the move and not re-run).

## Results

| Tool | Test | Result |
|---|---|---|
| nvsdef `create_drawing` | Default run, automatic dimensions | PASS. Native drawing in 42 s: 3 views + iso, 9 linear + 1 diameter dimension, title block filled. |
| nvsdef `create_drawing` | `center_marks=True` | FAIL. `adsk.drawing.CenterMarkDisplayTypes not available in this Fusion build`. |
| fusion-export `export_drawing` | PDF + DWG | PASS. 0.5 s. DWG read by LibreDWG (AC1027). |
| Exporter-X export calls | DXF + DWG | PASS. DXF read by ezdxf, 10 DIMENSION entities, edit + re-save round trip passed. |
| extract_fusion_dwg | Pull DWG from cached .f2d | PASS after patching the macOS path. Only finds drawings in Fusion's local cache. |
| GhostForge technique | TEXT + LINE via `FusionDoc.ExecuteAcadCommand` | FAIL. Entities appear, then are gone after save, close, reopen. Tried from script context and from a command destroy handler. |

## Findings

- Fusion's drawing API is a preview. One option had already been renamed between the tool's release
  and this build.
- On the test sheet (Fusion 2706.1.17) the API exposed only `drawingSymbols` and `customTables`
  collections, and no way was found to build a revision table or a styled BOM through it.
  **Out of date:** Autodesk's API reference now lists `Sheet.addRevisionTable`, `RevisionTable.addRevision`
  and a `TitleBlocks` collection (preview, "Introduced in version October 2026"), and `Sheets.add`
  (September 2026). `Views.add` creates base views only. Not yet re-tested here; the build tested may
  predate them.
- Automatic dimensions missed pocket depth and hole depth.
- DXF export stores geometry in inches with dimension scale 25.4 on a mm drawing (`$INSUNITS` 1,
  `DIMLFAC` 25.4). Dimensions read correctly; raw measurements in another program would be inches.
- Fusion's embedded Python cannot be assumed to load build123d / OpenCascade, which the handbuilt-cad
  engine needs. Not tested directly; matteoimmorlano's tool runs its engine outside Fusion for this reason.
- handbuilt-cad's engine already produces the target sheet style from STEP: title block, revision
  table, BOM table, balloons, notes. PDFs are made with matplotlib; the engine also imports ezdxf.
- sr-bom reads counts, part number, description and material from Fusion and exports CSV / Excel.

## Not tested yet

- Assemblies and sub-assemblies.
- Opening an .f3d from disk and generating from it.
- How complete the handbuilt-cad engine's DXF output is.
- Anything on the Spark Robotic team hub or the work PC.

## Incident

- A recursive scan of the whole cloud hub from a test script (`t1.py`) crashed Fusion once. It was
  relaunched; no existing files were changed. Do not walk the hub recursively.

## How PDM systems take in files (web research, 2026-11-20)

Context for ADR-012, ADR-014 and ADR-022. Not tested; from vendor docs.

| System | How it gets its data |
|---|---|
| SOLIDWORKS PDM | Data card variables are mapped to named properties stored inside the file, two-way. Its PDF plug-in reads and writes PDF properties (Title, Author, Subject, Keywords and custom ones such as Part Number, Description). |
| Autodesk Vault | Each property has a mapping direction: File to Vault, Vault to File, or bidirectional. |
| Fusion Manage | Design and drawing each get an item number. A revision is assigned at release (Quick Release or Release with Change Order). Pre-production revs are numbers, production revs are letters. One change order can carry several design and drawing items. |

Common pattern: the metadata rides inside the files as named properties; the PDM reads it at import,
owns the revision and lifecycle, and links model and drawing by a shared number.

Sources: help.solidworks.com (PDM variable mapping, PDF plug-in), help.autodesk.com (Vault "Map
Properties", Fusion Manage "Change orders" and "Workflow and lifecycle management").

## Spark Robotic engineering rules outside this app (Daniel, 2026-11-19)

Background on where the drawings are used. The PDM and Fusion handle these, not this app (ADR-012).

- Each standard part has its own model in the Standard Components Library and can go in any assembly.
  An update shows in every assembly that uses it, the next time that assembly opens.
- Custom manufactured and 3D printed parts live in their own folder beside the assembly that owns
  them. Another assembly copies them; it never uses them directly.
- No part, subassembly or component exists only inside an assembly. If the part model can't be opened
  from the assembly, it's wrong. Fasteners placed by the SR-Fastener add-in are the exception.
- Fasteners from SR-Fastener carry simple, non-vendor part numbers that give size and length. Real
  vendor numbers are used only for fasteners downloaded because the add-in lacked them; those models
  go in Standard Components.
- Model and drawing share one filename, `<part number> <part description>`; only the extension differs.
- Each new revision replaces the last one. The PDM keeps a snapshot of every model and drawing
  revision; old snapshots are visible to engineers only.

## Spike A live results: native Fusion drawing through the API (2026-11-21)

Tested on the test PC, Fusion 2706.1.17, through Fusion's built-in MCP (script tool). Scratch design
`SRDP_SCRATCH_spikeA` (80 x 50 x 10 mm plate, four 6 mm through holes, one 20 x 20 x 4 mm pocket on
the bottom face) in the `_drawtest_tmp` folder. Scratch design and drawing were closed without saving
and deleted from the cloud afterwards. Every `adsk.drawing` call used is a Preview feature.

| Requirement group | Result | Evidence |
|---|---|---|
| Saved orientations (ADR-021) | PASS | `Design.namedViews` reads TOP, FRONT, RIGHT, HOME with their cameras; custom views are listed by `count` / `item`. |
| Create a drawing | PASS, automatic mode only | `DrawingManager.createDrawing` took 33 s and returns a cloud DataFile; the drawing must then be opened. Manual mode fails: "requires a template with view placeholder information". Opening the result leaves the Edit Auto Dimensions dialog active; `terminateActiveCommand` clears it. |
| Base views | PASS | `Views.add` with any of 10 orientations (6 orthographic, 4 iso). The placement point is in millimetres on this drawing, although the docs say centimetres. |
| Projected views | Read only | Automatic creation made two. The API has no call to create one. Their `orientation`, `scaleValue` and `style` raise errors; their `viewCurves` read fine. |
| Section, detail, break views | FAIL | No create call. `ViewTypes` only lets a script recognise them. |
| View linework | PARTIAL | `View.viewCurves` returns every edge as line / circle / arc with sheet coordinates in mm (top view 12 curves, front 11, iso 40). Hidden edges are included with no flag to tell them from visible ones, and the count does not change with the view style. |
| View style | PARTIAL | `View.style` can be set after creation. The style set on `BaseViewInput.viewParameters` was ignored (asked for visible only, got visible + hidden). |
| Revision table | PASS | `Sheet.addRevisionTable`, then `RevisionTable.addRevision` with free-text rev, description, date, approved. Rev text is not validated ("AA" accepted). The title block Rev field followed the last row. |
| Title block values | FAIL | `TitleBlock.getAttributes` lists 15 tags with positions (REV, DRAWING_NUMBER, TITLE_1 and so on). `setAttributes` returned false for a custom tag and for SCALE. No call sets a tag's value. |
| Add a sheet | PASS | `Sheets.add`. The new sheet got the same full title block; a simpler continuation block was not tested (needs a template). |
| Custom table (BOM, thumbnails) | FAIL | `customTables.add` returns a table but `count` stays 0, `setCellData` returns false, and nothing shows in the PDF. |
| Image on sheet | PASS | `Images.insert` from a PNG path; it shows in the PDF. |
| Sketch linework on sheet | Not confirmed | `sketches.add` and `lines.add` succeed, but the line was not seen in the PDF. |
| Balloons, parts list | FAIL | No class for either in `adsk.drawing` (only `PartsListSettings`). |
| PDF export | PASS | `DrawingExportManager` PDF: both sheets, views, dimensions, revision table, image. |
| DXF export | FAIL for views | The API's DXF export holds the border, title block and table blocks only: no view linework, no dimensions. `HIDDEN` and `CENTER` linetypes are defined but unused. (The 2026-11-19 DXF with dimensions came from a different export route.) |

What this means for M1:

- A native Fusion drawing cannot carry the target style through the API today: no title block
  values, no working custom table, no balloons or parts list, no section or detail views.
- Fusion can still serve as the view generator for a custom editor: base views in any standard
  orientation, with exact 2D edges readable through `viewCurves`. The gap is telling hidden edges
  from visible ones. Options to test next: compare each curve against the model's faces for
  visibility, or read line styles from the PDF export.
- Cost of that route: about 30 s and a cloud save per drawing, plus a Preview API that Autodesk says
  not to ship.

## Spike B results: custom editor on the handbuilt-cad engine (2026-11-21)

Tested on the test PC. Engine: handbuilt-cad `drawing/dwg.py`, imported read-only, run out of process with
that clone's Python 3.13 (build123d 0.13.0, ezdxf 1.4.4, matplotlib 3.11.2). Scripts:
`research/spike-b/` (`views_row.py`, `editor_model.py`, `fusion_export_step.py`). Outputs stay in
`research/_local/out/spike-b/` (not committed). Same test plate as spike A.

### Views row

| Requirement group | Result | Evidence |
|---|---|---|
| Fusion design to STEP | PASS | `ExportManager.createSTEPExportOptions` on a new unsaved design: 0.06 s, no cloud save, not a Preview API. The STEP read back as 1 solid, 15 faces, 37 269 mm3, 80 x 50 x 10 (matches the model). Scratch design closed without saving. |
| Base views | PASS | Front view from the STEP in 13 ms. Any camera direction works, so every saved orientation (ADR-021) is one call. |
| Projected views | PASS | Top and right are the same call with the camera turned 90 degrees. The parent / child link is the editor's data, not the engine's (see below). |
| Iso view | PASS | 3 ms. |
| Hidden vs visible edges | PASS | OCCT's hidden-line removal returns two separate lists. Plate: front 4 visible + 36 hidden, top 8 + 16, right 4 + 44, iso 21 + 35. The engine throws the hidden list away on purpose (handbuilt-cad rule of 2026-10-17: never show hidden lines); the spike draws it dashed. |
| Section view | PASS | Engine `section_view`: capped cut through two holes, 3 hatch regions, 50 ms. Part sections only; assembly sections (hatch per part, uncut fasteners) are not in the engine. |
| Detail view | PASS | Top view clipped to a circle and redrawn at 3:1, about 15 lines with shapely. The engine's own `draw_detail` is tied to its part spec file. |
| PDF | PASS | Engine `render`, house title block and border, 0.6 s for PDF + DXF + PNG. |
| DXF | PASS, with a gap | Views land on VISIBLE (54) and HIDDEN (132) layers, plus HATCH, CUTPLANE, DETAIL, TEXT. Units are millimetres (`$INSUNITS` 4), so no inch quirk. Gap: every curve is a polyline, so a hole is a 72-sided polygon, not a CIRCLE. |
| Speed on an assembly | PASS on a synthetic one | 108 filleted plates (2 052 faces): 0.5 s per view, 5 436 hidden pieces in the front view. No real assembly was tested. |
| Same result from Fusion's STEP | PASS | The STEP exported by Fusion gives the same counts as the plate built in build123d (front 4 + 36, iso 21 + 35). |

Compared with spike A (Fusion `View.viewCurves`): Fusion gives hidden and visible edges mixed with no
flag, needs about 30 s and a cloud save per drawing, and is a Preview API. The STEP route gives them
apart in milliseconds with a stable API. Fusion's counts are lower (top 12 against 24) because OCCT
also returns hidden edges that sit directly behind another edge.

### View, sheet and BOM rules

`editor_model.py` holds the SPEC rules as plain Python, 73 lines with its checks: children follow the
parent, a left / right child slides only left-right, a top / bottom child only up-down, a freed child
moves freely and can project its own views; one full title block sheet that cannot be removed, one
shared sheet size; a BOM copy that is read-only, can leave rows out, and always takes quantities from
the parent. All checks pass. The rules are small; they are not a hard part.

Sheet, title block, revision table, BOM table and PDF evidence comes from sr-drawing-pdf's `sheet2d`
package (its PR #4, still open): about 2 600 lines of code and 820 lines of tests, edited through a
JSON command API, no screen yet, view frames empty. Not repeated here (ADR-020).

### Estimate

Sizes are judgement, not measurement: S is days, M is one to two weeks, L is three weeks or more of
focused agent-assisted work. Treat the total as plus or minus half.

| Piece | Exists today | New work | Size |
|---|---|---|---|
| View generation (base, projected, iso, hidden / visible) | engine + this spike | merge overlapping hidden pieces, cache per view | S |
| Section and detail | engine calls + this spike | pick the cut line or circle on screen; assembly sections | M |
| View, sheet and BOM rules | `editor_model.py`, `sheet2d` | fold the rules into the `sheet2d` document | S |
| Sheet, title block, rev table, BOM table, PDF | `sheet2d` (PR open) | merge it, add thumbnails | S to M |
| Fusion link (thin add-in) | sr-bom, sr-export, spikes A and B | export STEP, component tree, saved orientations, thumbnails; start the engine | M |
| Editor screen | nothing | canvas, pan and zoom, select, drag, undo, side panels | L |
| Annotations | batch code in the engine (dims, hole callouts, balloons, center marks) | place and edit by hand; keep them attached when the model changes | L |
| DXF with true circles and arcs | polylines | write CIRCLE / ARC from the exact edge type | M |
| Install on 5 to 6 PCs | nothing | ship Python + build123d (a few hundred MB) beside the add-in | M |

First usable iteration (the M2 list: views, sheets, BOM, review and edit, PDF): roughly 6 to 10 weeks.
The M3 annotation set is on top of that.

### Hard parts

1. The editor screen. Nothing exists yet, and where it runs is undecided: a panel inside Fusion (a web
   page hosted by the add-in) or a separate window. Either way the engine runs as its own process,
   because build123d cannot be assumed to load in Fusion's Python (still not tested directly).
2. Annotations that survive a model change. STEP carries no stable edge names, so a dimension has to
   find its edge again by geometry after a re-export. This is the hardest single item.
3. Assemblies. Not tested: whether the STEP keeps Fusion's component tree and names well enough to
   tie views and balloons to BOM rows, assembly sections, and hidden-line time on a real assembly.
4. Hidden-line clean-up. Many hidden edges sit directly behind a visible edge or behind each other and
   need merging, and they skip the engine's seam and tangent-edge filter, which only handles visible edges.
5. DXF for cutting. Polylines are fine for viewing; laser and router software usually wants real
   circles and arcs.
6. Packaging. The engine's Python stack is large and has to be installed and updated on each PC.
7. Hidden lines are a rule question, not a technical one: handbuilt-cad never draws them; this app can
   show them per view if wanted.

### What this means for M1

- ADR-021's open point has an answer on the evidence: Fusion exports STEP, the engine makes the 2D
  views. Fusion's drawing engine is not needed for views.
- A custom editor is buildable. The view geometry, the sheet parts and the rules are proven; the cost
  is the editor screen and annotations.

## Spike B styled sheet: the house drawing rules on the test plate (2026-11-22)

Daniel's review of the first spike B sheet (2026-11-22) asked for the house style: visible edges only,
centre marks, lettered section and detail, a dimensioned detail, a group view label, a scale that fills
the sheet, a full title block, rev table, BOM, notes, dimensions with hole callouts, and real circles in
the DXF. Script: `research/spike-b/styled_sheet.py`. Output stays in `research/_local/out/spike-b/`
(`spike_b_sheet.pdf`, `.dxf`, `.checks.json`).

| Item | Result | How |
|---|---|---|
| Visible edges only, all views | PASS | Engine default. 0 hidden-line items on the sheet. |
| Centre marks on all holes | PASS | Engine `centermark` on the four holes in the top view. |
| Section with arrows and letters | PASS | Engine `section` spec: capped cut, cutting-plane line, arrows, `A` at both ends. |
| Detail with letter and dimensions | PASS, with a wrapper | Engine `details` spec letters the parent circle. Its detail dimensions can only sit above or beside a feature, so the pocket width and depth are added by a wrapper. |
| Group view label, `TRIMETRIC VIEW` | PASS, with a wrapper | The engine names the pictorial; the group label is added by the script. |
| Scale fills the sheet | PASS | Engine `pick_scale` chose 1.5:1 (2:1 leaves no room for dimensions). |
| Title block, rev table, notes | PASS | Engine `frame`, a `REVLOG.md` beside the STEP, spec `notes`. Initials come from the drawing-initials setting. |
| BOM | PASS, with a wrapper | Engine `asm.bom_table`. `make_part` has no BOM, so the script adds it and reserves its space. |
| Dimensions and hole callout | PASS | Ordinate hole locations, overall 80 / 50 / 10, `4X ⌀6 THRU`, pocket square 20 and depth 4. |
| Tapped-hole callouts | Not shown | The plate has no tapped holes. The engine's `hole_callouts` covers them; untested here. |
| DXF real circles | PASS for circles | The script's own DXF writer puts the four holes out as CIRCLE entities, with centre and radius taken from the B-rep. Holes in the trimetric view are ellipses and stay polylines. |
| Engine rule check | PASS | `spike_b_sheet.checks.json` reports `ok: true`. |

Gaps this showed in the engine, for our copy of it (ADR-009), and one note:

- A section takes over the front or right view slot, so a sheet cannot carry front, top and right views
  plus a section. This sheet has the section in the front slot, and the group label reads `TOP / RIGHT VIEWS`.
- No spec field for a BOM on a part sheet, a group view label, a view label offset, or a detail
  dimension below a feature.
- The DXF writer has no CIRCLE or ARC output.
- The test plate's material (`6061-T6 AL (TEST)`) was made up for the test so the field is filled.

## Editor slice and assembly test (2026-11-22)

Two worker results, merged as PRs #11 and #12. Details, run steps and sources are in each folder's
README: `research/editor-slice/` and `research/assembly-test/`. Outputs stay in `research/_local/`.

### Editor slice: the first clickable screen

A local web page (SVG, no framework) served by a small Python server that asks the engine for view lines.
Checked by clicking in a browser and by 16 tests.

| Item | Result |
|---|---|
| Drag a view from the side panel onto an 11x17 sheet, drag to move | PASS |
| Projected views left, right, top, bottom from any parent (third angle) | PASS |
| Link rules: children follow, one-axis slide, break link, freed child projects | PASS |
| Delete, undo, sheet scale, add / remove / switch sheets (sheet 1 stays) | PASS |
| Save, and PDF export through the engine with the title block | PASS |
| On-screen title block, continuation sheet frame, pan and zoom, group labels | Not built (placeholders) |
| Inside a Fusion panel, a real assembly, loading a STEP | Not tested |

- The screen basics were not the hard part. The server owns the document and the page only sends
  commands, which made undo nearly free.
- Main risk: two renderers. The screen and the PDF are drawn by different code; only the view lines are
  shared. Title block, tables and dimensions would be written twice unless the engine hands one item list
  to both.
- Estimate for the editor screen without annotations: about 3 to 5 weeks (judgement). Hand-placed
  annotations remain the largest item on top.

### Assembly test: an 8-row assembly drawn to the house rules

Test assembly `SRDP-T-100` (base plate, cover sub-assembly with handle, stop block, three screw sizes;
12 solids), built with build123d. sr-cadlib was not used: it only runs inside Fusion. Package: 3 sheets
(views and BOM, build order, section A-A with details B, C, D). Engine rule check: `ok: true`.

| Item | Result |
|---|---|
| BOM rows and quantities against the model (counted) | PASS, 8 rows, 12 leaf parts |
| Sub-assembly as one item on sheet 1, children on its build step | PASS, with a spec trick |
| Balloons tied to BOM rows | PASS, every row ballooned on some sheet |
| Tapped blind hole: thread depth and deeper drill | PASS (engine) |
| Tapped through hole: thread plus tap drill | PASS, tap-drill line added by a wrapper |
| Counterbore callout | PASS (engine) |
| Capped assembly section, parts hatched opposite ways, screws unhatched | PASS, with wrappers |
| Details carrying the callouts | PASS, with wrappers. Two detail circles overlap on the section. |
| Visible edges only, centre marks, title block, rev table, notes | PASS |
| DXF circles | PASS in the top view; pictorial views stay polylines |
| STEP keeps the tree, quantities and positions | PASS. The importer changes spaces and dots in names to underscores. |
| BOM from the STEP alone | PARTLY: rows, quantities, part numbers yes; description and material no |
| Hidden-line time, whole assembly | 0.14 to 0.21 s per view |
| Hole positions dimensioned | NOT DONE: the assembly flow has no hole table or per-part plan view |

- Engine gaps for our copy (ADR-009): no section, centre marks, cutting-plane line or details in the
  assembly flow; one hatch direction and no way to leave fasteners unhatched; no tap drill on a through
  tapped hole; no sub-assembly or indented BOM; no continuation title block; no CIRCLE / ARC in the DXF
  writer; no hole-position dimensions for an assembly-only package.
- A STEP does not say which holes are tapped or how deep the thread is. That has to come from Fusion or
  a spec file.
- Not verified: a Fusion round trip of this assembly. The STEP written by build123d is AP214; handbuilt-cad
  asks for AP242. Counterbore size, blind depths, plate sizes and materials are test values, not from a standard.

## Fusion data file with the STEP, and the F3D viewer (2026-11-22)

Tested on the test PC, Fusion 2706.1.17 through Fusion's built-in MCP, and F3D 4.0.1 (portable release,
unpacked in a scratch folder, not installed). Script: `research/fusion-data/export_step_and_data.py`.
Outputs stay in `research/_local/out/fusion-data/`.

### STEP plus a data file, exported together (ADR-028)

A scratch design with two components (a base plate with tapped holes, a cover plate used twice), part
numbers, descriptions and a material. One script wrote the STEP, an f3d and a JSON data file, then
closed the design without saving.

| Item | Result | Evidence |
|---|---|---|
| STEP export | PASS | 0.10 s. Read back: 3 solids, tree `Base_Plate`, `Cover_Plate` x2. |
| f3d export | PASS | 0.19 s, `createFusionArchiveExportOptions`. |
| BOM fields from Fusion | PASS | Part number, description, material and quantity per component (cover plate qty 2). |
| Tapped through hole | PASS | `M5x0.8`, class `6H`, tap drill 4.2, through = true, thread length 10 (Fusion's default; not full length unless set). |
| Tapped blind hole | PASS | `M4x0.7`, class `6H`, drill 3.3, hole depth 10, thread length 8. |
| Plain hole | PASS | Diameter 5.5, through, tap type `simple`. |
| Hole position and direction | PASS | Position and axis per hole, in the component's own coordinates. |
| Holes listed per component | NEEDS CARE | The base plate's hole list also returned the cover plate's four holes. Filter holes by the body they cut before use. |
| STEP names against the data file | PASS, by name | STEP has `Base_Plate`, the data file has `Base Plate` (spaces become underscores on import). Match on a cleaned name or on order; the part number is not in the STEP. |

- This closes the two gaps from the assembly test: BOM description and material, and which holes are tapped.
- Thread data exists only for holes made with Fusion's Hole or Thread tools. A plain extruded cut has none.
- Not tested: a real design from the hub, sub-assemblies, linked (external) components, counterbores, saved views in the data file (the scratch design had none).

### F3D viewer (f3d.app, Daniel's fork cloned to the active projects folder)

| Item | Result | Evidence |
|---|---|---|
| Open a Fusion `.f3d` | FAIL | "is of an unknown format". F3D the viewer and `.f3d` the Fusion archive only share a name. |
| Open our STEP | PASS | Assembly rendered to PNG in under 1 s from the command line. |
| Clean thumbnail from a STEP | PASS | 512 x 512, no background, grid, axis or file name, edges on: 0.45 s. |
| Reader for Fusion `.f3d` in the fork | Not practical | The `.f3d` is a zip (Zstandard) holding Autodesk's own solid format (`.smb`, `.smbh`). No open reader exists to build on. |

What is useful as it ships, with no change to the fork:

- Thumbnails. The command line makes a shaded picture of any STEP in about half a second. That fits
  BOM thumbnails (ADR-003) and data-card pictures in the PDM.
- Free STEP viewer for people without Fusion. It also has a Windows Explorer thumbnail extension
  (`winshellext/`), Python bindings (`python/`) and a browser build (`webassembly/`); none of those three was tested.
- Licence: BSD 3-Clause.

For the PDM project:

- A Fusion `.f3d` already holds a preview picture: `Previews/small.png` and `Previews/big.png` inside
  the zip. Windows `tar -xf` unpacks it; Python's `zipfile` cannot (Zstandard). So the PDM can show a
  picture of an `.f3d` without Fusion.
- Nothing else in the `.f3d` is readable without Fusion. BOM and hole data must come from the data file.
- F3D's command line can make the STEP thumbnails; its browser build may suit an in-browser STEP viewer,
  after a test that the build reads STEP.

## BOM thumbnails with F3D (2026-11-22)

Daniel chose to try the F3D viewer's command line for BOM thumbnails (ADR-003). Script:
`research/thumbnails/bom_thumbnails.py`, run on the test assembly `SRDP-T-100`. F3D 4.0.1, portable copy.
Output stays in `research/_local/out/thumbnails/`.

| Item | Result | Evidence |
|---|---|---|
| One shaded picture per BOM row | PASS | 8 rows, including the sub-assembly and its children. |
| Speed | PASS | 0.44 to 0.48 s each, 3.6 s for the 8 rows (420 x 420 pixels). |
| Part shown the way it was modelled | PASS | The placement is undone first, so a screw fitted upside down still shows head up. |
| Clean picture | PASS | No background, grid, axis or file name; edges on; same trimetric direction as the engine's pictorial view. |
| BOM page with pictures | PASS | Indented rows with picture, item, quantity, part number, description, material. |
| Colour or material look | Not shown | The test STEP carries no colours, so every part is grey. A STEP from Fusion may carry them; not tested. |
| Picture inside the drawing sheet | NOT DONE | The engine's sheet has no image item. The page here is a separate matplotlib layout. |

- A copied or re-wrapped shape is needed before export: build123d refused to write a STEP for a node taken straight from the imported tree.
- F3D becomes a tool the app needs on each PC (about 70 MB unpacked, BSD 3-Clause). The alternative is a picture from Fusion at export time.

## Real design test and faster views (2026-11-22)

Design: `custom-pdm-enclosure-v2c-F1` v17 (Daniel's hub, custom-pdm project): 147 top-level parts, 45 distinct
top-level rows, 155 BOM rows in all, 1,276 bodies, 58,187 faces, 98 linked parts, one sub-assembly. Opened read-only,
exported, closed without saving. Scripts: `research/real-test/`. Outputs stay in `research/_local/out/real-test/`.

### Export and BOM

| Item | Result | Evidence |
|---|---|---|
| STEP export from Fusion | PASS | 7.6 s, 71 MB. The design stayed unmodified. |
| Data file from Fusion | PASS | 0.02 s. |
| BOM: STEP against Fusion | PASS | All 45 top-level rows and all 147 parts match by name and quantity. |
| Part number and description | PASS | None blank. |
| Material | FAIL as data | Fusion's material is "Aluminum 6061" on bought parts and PCBs too; the real material is written in the description text. The spec-file override (ADR-002) is needed. |
| Hole and thread data | NOT AVAILABLE here | 0 Hole features (parts came in as STEP); the 13 thread features are all on screws. |
| f3d export | Not possible | The design has linked parts. |
| STEP import into the engine | 17 to 21 s | 4.5 GB of memory during exact hidden-line removal. |

### Hidden-line removal on a real assembly

| Method | Front view | Result |
|---|---|---|
| Exact (`HLRBRep_Algo`, the engine's current call), whole assembly | Did not finish in 7 min | Stopped. |
| Exact, parts over 1,500 faces left out (PCBs) | 262 s | 50,375 hidden pieces worked out and thrown away. |
| Exact, parts over 300 faces left out | 200 s | Other views ran over 2 hours without finishing. |
| Polygonal (`HLRBRep_PolyAlgo`) on a 0.2 mm mesh, whole assembly | 2.8 s (+3.8 s meshing once) | Clean, complete view. Top 2.5 s, trimetric 7.3 s. |
| Hybrid: exact edges kept where a z-buffer says they are in front | 47 s (z-buffer in plain numpy) | Exact lines, but silhouettes of curved faces are missing and some edges break. A real rasteriser would take it under a few seconds. |

- Why the exact method is slow: every view starts again from the whole B-rep, and every edge is tested against every
  face, including parts inside the enclosure that can never be seen. It also works out every hidden edge.
- The polygonal method is what other CAD tools offer as a fast mode: SolidWorks "draft quality" views, FreeCAD
  TechDraw "coarse view", Creo "fast HLR". Lines are short straight segments, so circles and arcs are polygons.
- Converting to DXF first would not help: DXF is already 2D, and the projection is the slow step.

### Angles found in Daniel's repos and Autodesk docs

- **sr-export already writes the data file.** Every STEP it exports gets `<name>.bom.json` (schema
  `sr-bom-sidecar` v1): BOM with occurrence paths, linked source and version, mass properties, holes, hole groups,
  thread data, tap drills from Fusion's own thread tables, thumbnails, and an "unsaved changes" warning.
  `research/fusion-data/export_step_and_data.py` duplicates part of it.
- **Linked part versions** are in that file, so view lines and thumbnails can be cached per part version.
- **Component visibility** is not in the file yet. Fusion knows it (light bulb per occurrence), so per-view
  hide lists are possible, like SolidWorks "hide components" in a view.
- **Fusion attributes** can be stored on faces and edges and survive model edits. Tagging features in Fusion and
  writing the tags into the data file is a route to dimensions that stay attached when the model changes.
- **Fusion Compute MCP** runs Fusion headless in the cloud (public beta, TypeScript API). It could do the
  re-export the PDM asks for at approval (ADR-022) with no Fusion seat on the PDM side. Not tested; access and cost unknown.
- **handbuilt-cad `tools/viewer.py`** writes a spin-around 3D viewer as one HTML file: a candidate for viewing
  models in the vault without any install. `tools/views.py` has a small z-buffer renderer.

## Fast-view draft package on the reference assembly (2026-11-23)

ADR-030 fast views on the reference assembly (ADR-031), with sr-export's `bom.json` (ADR-029). sr-export's own
sidecar code was run inside Fusion on the open design (0.9 s, design not modified). Script: `research/real-test/fast_sheet.py`.

| Item | Result | Evidence |
|---|---|---|
| sr-export `bom.json` | PASS | 155 rows, schema `sr-bom-sidecar` v1. Top-level rows (occurrence path with no `+`): 45 rows, 147 parts, matching the STEP. |
| Views (front, top, right, trimetric) | PASS | 2.9, 2.6, 3.4 and 7.0 s after a 17 s STEP import and 3.8 s meshing. Visible edges only; tangent edges in the trimetric only. |
| Two-sheet PDF and DXF | PASS | Sheet 1 views at 1:2.5 (trimetric 1:3, labelled); sheet 2 the 45-row BOM. Render 11.6 s. |
| F3D thumbnails, one per top-level row | PASS | 45 of 45, none failed; median 0.46 s, slowest 11.9 s (a PCB), 56 s in all. Settles H25 on speed and stability. |
| BOM material column | FAIL as data | Fusion says "ALUMINUM 6061" on bought parts and PCBs. Needs the spec-file override (ADR-002). |
| BOM rows linked to parts in views | NOT DONE | The fast method returns one set of lines for the whole assembly. Loading each part as its own shape gives per-part lines; next step. |
| Dimensions, balloons, rev table | NOT DONE | Draft only. |

- Whole run, views and both sheets: about 50 s; with thumbnails about 2 minutes. The exact method never finished one view.
- The top assembly's own part number is not in `bom.json` (it lists the parts). Taken from Fusion separately for this test.

## View methods compared, any model type (2026-11-23)

ADR-039 asks for smooth, continuous lines that never look like a mesh, from any model type. Script:
`research/real-test/compare_methods.py`, on the lid `CPDM-ENC-102` of the reference assembly (465 faces; as a mesh,
15,610 triangles). Output: `research/_local/out/real-test/compare/compare_methods.pdf`.

| Method | Front | Trimetric | Looks like a drawing? |
|---|---|---|---|
| 1 Exact B-rep | 0.4 s, 160 lines | 0.1 s, 442 lines | Yes (reference) |
| 2 Fast, raw pieces | 0.02 s, 566 pieces | 0.05 s, 1,774 pieces | Yes on screen, but every curve is many short pieces |
| 3 Fast, joined into polylines | 0.03 s, 110 lines | 0.07 s, 345 lines | Yes; matches 1 by eye, fewer lines than 1 |
| 4 Mesh body, fast | 1.1 s, 5,854 pieces | 1.3 s, 7,917 pieces | No: every triangle edge shows (the failure case) |
| 5 Mesh body, creases + silhouettes | 0.8 s, 1,010 lines | 1.3 s, 471 lines | Mostly; curved outlines break into dashes (z-buffer tolerance), fixable |

- On one part the exact method is fast (under half a second). It is only slow on whole assemblies (no view in 7
  minutes on the 147-part enclosure).
- A mesh body must never go through the B-rep methods: it needs the crease-and-silhouette method (5).
- Joining pieces (3) gives continuous lines for the PDF and DXF; true circles and arcs still need snapping to the
  exact edges where a B-rep exists.

## Render-mode switching and the other view types: how each can be made (2026-11-23)

Answers to Daniel's questions of 2026-11-23. Plans from what was tested; items marked "untested" are not proven.

### Switching a placed view to another render mode

| From -> to | What it needs | Cost |
|---|---|---|
| DRAFT -> HQ | Only the view's own lines: the pieces are joined. No model needed. | Instant (0.03 s on the lid) |
| FAST DRAFT or DRAFT -> HQ / UHQ | The model, but only that one view's camera is projected again | One view's time, not the whole drawing |
| HQ -> UHQ | The B-rep, that view only | 0.1 to 0.5 s on one part; minutes on a 147-part assembly |

- A view is stored as model reference + model version + camera + scale + mode + its lines. Switching mode re-runs only
  that view. The mesh and the imported model are cached per model version, so reopening a drawing does not rebuild them.
- Placing views at DRAFT first and upgrading in a background process (one process per view, as SOLIDWORKS does for
  high-quality views) makes the first placement fast: about 3 to 7 s per view on the reference assembly instead of
  minutes. The final save waits for any upgrade still running. Untested as a pipeline; each step is tested alone.

### View palette

- Yes: every view is a camera, so a palette can list front, back, left, right, top, bottom, trimetric, the model's
  saved named views (Fusion `Design.namedViews`, tested in spike A) and the user's own saved views. The palette is
  saved in the drawing, so views can be dragged onto any sheet later, like the SOLIDWORKS View Palette. The editor
  slice already has a side panel of standard views. sr-export's `bom.json` does not carry named views yet.

### Other view types

| View | Method | State |
|---|---|---|
| Projected | Parent camera turned 90 deg, linked to the parent | Built in the editor slice |
| Auxiliary | Camera along the normal of a face or edge picked in a parent view, linked like a projected view | Untested; same projection call |
| Section (part) | Cut the solid with a plane, keep one side, cap and hatch the cut faces | In the engine (`section_view`) |
| Section (assembly) | Cut each part, hatch each a different way, leave fasteners uncut | Done by a wrapper in the assembly test |
| Detail | Clip the parent view's lines to a circle, scale up; UHQ projects that region again | Done in spike B and the assembly test |
| Broken view | Remove a band of the view's lines and close the gap, add break lines; 2D only | Untested; simple |
| Broken-out section | Cut the model with a prism from a closed profile drawn on the view, then project | Untested; needs a B-rep cut |
| Crop view | Clip the view's lines to a profile; 2D only | Untested; simple |
| Exploded view with trail lines | Move parts along an insertion direction per assembly step; dotted lines join each part to its place | In the engine (`exploded_shapes`, `explode_lines`, `stage_sheets`) |

- Exploded steps need an order and a direction per part. The engine takes them from a spec. Sources to test: the
  directions of Fusion joints between parts, and a step list the engineer edits in the editor. Untested.
- Every one of these works on the camera and the view's lines, so each can use any render mode.

## Render tests on real models (2026-11-23)

H34b: the four render modes of ADR-040 on three of Daniel's hub models (ADR-042), tangent edges drawn (the default),
each run before and after the H40a anti-aliasing fixes. STEP and sr-export `bom.json` came from local desktop Fusion
(`research/render-tests/fusion_export.py`); each design was opened by file id, read only, and closed unmodified without
saving. Views: `research/render-tests/render_modes.py`, one child process per job, UHQ killed after 120 s per view.
Outputs stay in `research/_local/out/render-tests/` (`<model>_compare.png` rows = modes, `<model>_picker.png` the
mode-picker strip, `<model>_aa_zoom.png` and `<model>_f3d_zoom.png` the anti-aliasing before / after).

Times are for the four views (front, top, right, trimetric) after the fixes, then before them in brackets. They
leave out the shared steps: STEP import (1.4 / 17.5 / 2.0 s for the three models) and meshing (0.2 to 3.9 s). "Lines"
counts what is written: pieces for DRAFT, polylines plus fitted arcs and circles for HQ and FAST DRAFT, sampled exact
edges for UHQ. Sizes are the DXF of the four views and the 150 dpi PNG of the sheet.

### Fuel hanger `FH-200_Fuel-Hanger-Billet-Assembly_revA`: 19 occurrences, 12 solids, 1,806 faces, STEP 8.1 MB, 1:4

| Mode | Views done | Time, 4 views | Lines | DXF / PNG | Looks right? |
|---|---|---|---|---|---|
| UHQ | 1 of 4 | right 87 s; front, top and trimetric timed out (120 s each) | 1,646 (right only) | 460 kB / 54 kB | Yes where it finished |
| HQ | 4 | 5.4 s (7.7 s) | 6,022 (4,417) | 1.4 MB / 168 kB | Yes |
| DRAFT | 4 | 4.5 s (7.5 s) | 38,003 pieces (22,809) | 7.1 MB / 166 kB | Yes on screen |
| FAST DRAFT | 4 | 11.1 s (7.5 s) | 48,123 (25,115) | 9.1 MB / 170 kB | No: edges missing (bracket outline in the trimetric, the foot in front), outlines dashed |

### Fuse box `ST185_fusebox_rev7`: 73 occurrences, 816 solids, 35,004 faces, STEP 62.9 MB, 1:4

| Mode | Views done | Time, 4 views | Lines | DXF / PNG | Looks right? |
|---|---|---|---|---|---|
| UHQ | 4 of 4 | 156.5 s (21, 76, 21, 39 s) | 22,625; 260 true arcs | 5.9 MB / 374 kB | Yes |
| HQ | 4 | 19.8 s (13.0 s) | 12,256 (8,739) | 3.8 MB / 389 kB | Yes; matches UHQ by eye at print scale |
| DRAFT | 4 | 17.8 s (12.6 s) | 74,014 pieces (46,544) | 13.6 MB / 375 kB | Yes on screen |
| FAST DRAFT | 4 | 44.3 s (26.5 s) | 260,170 (83,174) | 47 MB / 358 kB | Mostly: dashed outlines, some broken edges |

### Filament cabinet `FC5-000 Filament Cabinet V5 Assy Rev H`: 1,117 occurrences, 1,130 solids, 16,521 faces, STEP 9.1 MB, 1:10

| Mode | Views done | Time, 4 views | Lines | DXF / PNG | Looks right? |
|---|---|---|---|---|---|
| UHQ | 4 of 4 | 46.0 s (16, 10, 10, 10 s) | 6,434; 459 true arcs | 3.6 MB / 327 kB | Yes |
| HQ | 4 | 11.9 s (7.7 s) | 5,604 (3,987) | 1.3 MB / 328 kB | Yes |
| DRAFT | 4 | 10.8 s (7.5 s) | 41,081 pieces (22,717) | 7.6 MB / 328 kB | Yes on screen |
| FAST DRAFT | 4 | 63.8 s (40.0 s) | 175,376 (149,924) | 31 MB / 341 kB | Mostly; the slowest mode on this model |

### Anti-aliasing fixes (H40a), before and after

| Fix | Result |
|---|---|
| Mesh deflection scaled to the view (0.02 mm on paper / sheet scale, 0.01 to 0.2 mm; 0.25 rad instead of 0.5) | 0.08 mm at 1:4 (fuel hanger, fuse box). At 1:10 it clamps at 0.2 mm, so only the angle changed (cabinet). HQ time +52% (fuse box, 13.0 to 19.8 s) and +55% (cabinet); the fuel hanger came out faster only because of the first-view cost below. Smoother curves in the trimetric, where circles are ellipses and no arc can be fitted. |
| Arcs and circles fitted where every point is within 0.02 mm | HQ: 1,793 arcs + 13 circles (fuel hanger), 2,731 + 57 (fuse box), 1,798 + 192 (cabinet); at most 1 s per view. HQ DXF size about the same (+5%, +13%, -17%), and arcs and circles are now true DXF ARC / CIRCLE entities. |
| PNG drawn 3x and downsampled (Lanczos) | Visibly smoother edges at 150 dpi; HQ after matches UHQ by eye (`<model>_aa_zoom.png`). PNG files +38 to 51%; 1 to 2.5 s per sheet instead of 0.1 s. |
| F3D thumbnails with `--anti-aliasing=ssaa` | Supported by F3D 4.0.1 (`none`, `fxaa`, `ssaa`, `taa`). Same time (2.5 / 26 / 5.8 s for the whole model), files 6 to 15% smaller, smoother edges (`<model>_f3d_zoom.png`). |
| FAST DRAFT: visibility tested against the farthest depth in a 3x3 pixel patch | More edges kept (fuel hanger front 554 to 1,396 lines) but outlines still break into dashes; 50 to 70% slower. |

### What failed or surprised

- UHQ timed out on 3 of 4 views of the fuel hanger, the smallest model (12 solids). The time is all in the hidden-line
  step (`Hide()`, over 116 s; setup 3.5 s). The 35,004-face fuse box finished every view in 21 to 76 s, so face count
  does not predict UHQ time; some surface types (likely the billet's threads, knurls or the hose clamp) are slow. Which
  body is slow was not found.
- FAST DRAFT on B-rep models is slower than HQ and looks worse: dashed or missing outlines, tens to hundreds of
  thousands of short pieces, a 47 MB DXF on the fuse box. It never draws tangent edges (it sees only creases over 25 deg).
- The first polygonal view of each run took 3 to 7 s, even on the fuel hanger, whose other views took 0.2 to 1.3 s:
  a one-time cost, not the view itself.
- sr-export's data file took 419 s on the cabinet's 1,117 occurrences (22 s on the fuel hanger), longer than one Fusion
  MCP call waits. Fusion was busy, not hung, and the file was complete.
- Fusion MCP script `print()` output is not returned; the export script writes `fusion_info.json` instead.

### Recommendation

- HQ with the three fixes is the right default for placing views: 5 to 20 s for four views on all three models, and
  it looks right on every one.
- UHQ only in the background, one process per view with a timeout, keeping the HQ view when it times out (the fuel
  hanger). It is not needed for the screen; it is for released files where true curves matter.
- DRAFT saves almost no time over HQ here (joining and fitting took about 1 s at most per view) and writes DXFs 3.6
  to 6 times bigger. Daniel to decide whether it stays a separate mode.
- FAST DRAFT is not worth it on B-rep models of these sizes. Keep it for mesh bodies (ADR-039) once the dashed outlines
  are fixed.
- Use `--anti-aliasing=ssaa` for F3D thumbnails.

## All render tests compared (2026-11-24, H52; fix2 re-run, ADR-049)

Sixteen models from Daniel's OneDrive models folder (ADR-047), four views each, every mode after the ADR-049 fixes,
UHQ timeout 600 s per view. Times are the sum of the four views; `research/render-tests/compile_results.py` builds the
numbers from each `render_modes.json` (run on `research/_local/out/render-tests/fix2`). Quality is rated 1-5 by eye
from each `compare.png`: 5 = complete and smooth, 3 = a visible defect, 1 = most views missing or wrong. PDM skipped
(ADR-050).

| Model | Solids / faces | UHQ s (Q) | HQ s (Q) | DRAFT s (Q) | FAST s (Q) |
|---|---|---|---|---|---|
| Spacer | 1 / 4 | 11.2 (5) | 2.8 (5) | 2.8 (5) | 4.1 (4) |
| Catch can scan (surfaces) | 0 / 9 | 16.2 (2, right view collapsed to a line) | 3.4 (4) | 3.2 (4) | 10.4 (3, broken edges) |
| PCV tee | 1 / 50 | 64.0 (5) | 3.1 (5) | 2.9 (5) | 15.1 (2, tee outlines missing) |
| AOI yoke | 1 / 57 | 11.5 (5) | 2.8 (5, slot bow fixed) | 2.8 (5) | 5.0 (5) |
| CSB3 body | 1 / 149 | 11.3 (5) | 2.9 (5) | 2.8 (5) | 7.9 (3, front/right lines missing) |
| Bezel (surfaces) | 0 / 237 | 24.9 (4, broken hidden edges) | 3.1 (4) | 2.9 (4) | 7.8 (3, stray boxes) |
| Pedal adapter | 1 / 292 | 16.6 (4, stray lines) | 3.4 (5) | 3.1 (5) | 9.7 (3, gaps) |
| Knuckle rev4b | 1 / 406 | 97.6 for 2 of 4 (2, 2 timeouts) | 4.4 (4) | 3.5 (4) | 18.1 (3, lines missing) |
| Fuel hanger | 12 / 1,217 | 84.4 (2, long stray line, wrong extents) | 4.3 (5) | 3.8 (5) | 9.3 (3, clamp detail lost) |
| Knuckle billet LF26 | 1 / 1,248 | 23.0 (5) | 3.8 (5) | 3.2 (5) | 10.6 (3, dashed edges) |
| X-carriage asm | 47 / 3,637 | 1,204.5 for 3 of 4 (2, 1 timeout) | 6.0 (5) | 5.3 (5) | 19.8 (3, motor lines lost) |
| DRB102 plate asm | 12 / 5,576 | 47.4 (5) | 7.2 (5) | 6.3 (5) | 21.8 (4) |
| FC6 cabinet | 432 / 13,434 | 360.9 for 1 of 4 (1, 3 timeouts) | 17.2 (4) | 16.5 (4) | 238.8 (3) |
| CC-500 pendant | 359 / 17,392 | 130.4 (4, stray marks) | 9.3 (5) | 9.0 (5) | 18.6 (2, broken outlines) |
| Fuse box | 816 / 35,004 | 167.9 (5) | 18.1 (4, sparse front) | 16.0 (5) | 37.6 (3) |
| CC-000 panel | 3,637 / 86,300 | 755.7 (4) | 60.1 (4) | 59.0 (5) | 62.2 (3, pendant broken) |
| **Average Q** | | **3.8** | **4.6** | **4.8** | **3.1** |

- HQ and DRAFT are the fastest on every model (under 20 s up to 35k faces, 60 s on the 86k-face panel) and the best
  looking. HQ is DRAFT plus polyline joining and true-arc fitting: same speed, smaller DXF, real ARC/CIRCLE.
- The ADR-049 fixes worked for HQ: the AOI yoke slot bow is gone.
- UHQ gives exact true arcs from the B-rep, but timed out on 3 models and drew wrong lines on 4 more. It does not
  follow face count. Slowest by 5-50x.
- FAST is never fastest and never best (FC6: 239 s). It loses to HQ/DRAFT on both speed and quality.

## XQ: exact edges, visibility from the GPU depth buffer (2026-11-24, ADR-051)

Daniel's rule (ADR-051): over 2 minutes from STEP to views is a fail. UHQ (exact HLR, `HLRBRep_Algo`) runs on one CPU
core and compares every edge with every face, so it grows with the square of the model; it took 756 s on the CC-000
panel and timed out on 3 models. The PC has a Ryzen 5 7600X (6 cores, 12 threads), 64 GB RAM and an RTX 3060 12 GB,
and every old mode used one core and no GPU.

How other CAD tools do it: SOLIDWORKS offers "High quality" (exact, model resolved) and "Draft quality" (lightweight,
tessellated) drawing views; the most common hidden-line method in CAD viewers is to draw the shaded model into a depth
buffer and keep only the parts of each line in front of it (Cole & Finkelstein 2009/2010). XQ uses that for
**visibility only** and keeps the **exact B-rep edges** for the line shapes (true lines and arcs), so lines are as good
as UHQ. Silhouettes of curved faces are traced inside the mesh triangles with smoothed normals (Hertzmann & Zorin
2000), so they are smooth, not stair-stepped.

Pipeline (`research/render-tests/xq_render.py`): STEP read (OCC, 1 core) -> mesh (OCC, all cores) -> depth buffer for
the 4 views (VTK/OpenGL on the GPU) at the same time as exact edge sampling (10 worker processes) -> visibility per point
(numpy) -> join, fit true arcs. Run on all 16 models straight from STEP (queue `xq/full4`):

| Model | Faces | XQ total s (from STEP) | of which STEP read s | UHQ s (fix2, cached) | XQ Q |
|---|---|---|---|---|---|
| Spacer | 4 | 4.4 | 0.0 | 11.2 | not rated |
| Catch can scan | 9 | 5.2 | 0.2 | 16.2 (view broken) | 4 |
| PCV tee | 50 | 5.5 | 0.1 | 64.0 | 5 |
| AOI yoke | 57 | 5.1 | 0.0 | 11.5 | 5 |
| CSB3 body | 149 | 5.6 | 0.1 | 11.3 | not rated |
| Bezel | 237 | 5.9 | 0.2 | 24.9 | not rated |
| Pedal adapter | 292 | 6.2 | 0.5 | 16.6 | not rated |
| Knuckle rev4b | 406 | 16.3 | 8.3 | 2 of 4 timed out | 4 (cast surfaces a little rough) |
| Fuel hanger | 1,217 | 8.2 | 1.2 | 84.4 (stray line) | not rated |
| Knuckle billet LF26 | 1,248 | 7.4 | 0.8 | 23.0 | not rated |
| X-carriage asm | 3,637 | 10.1 | 1.4 | 1 of 4 timed out | 5 |
| DRB102 plate asm | 5,576 | 13.4 | 2.7 | 47.4 | not rated |
| FC6 cabinet | 13,434 | 43.7 | 17.3 | 3 of 4 timed out | 5 |
| CC-500 pendant | 17,392 | 22.4 | 10.0 | 130.4 | 4 (small gaps, front view) |
| Fuse box | 35,004 | 40.8 | 15.5 | 167.9 | 5 |
| CC-000 panel | 86,300 | 88.4 | 42.5 | 755.7 | 5 |

- Every model passes the 2-minute rule; the worst is 88 s, and 48 % of that is the STEP read.
- The STEP read is now the largest cost on big assemblies (CC-000: parse 14 s, transfer 28 s, one core). Open-source
  OCCT 8 has no parallel STEP reader (OCCT's multi-threaded transfer is a commercial add-on), and turning off shape
  healing is not possible in OCCT 8 (`read.step.sequence` is gone). Next options: cache by file hash (re-render of
  CC-000 is then about 46 s), or read the assembly in parallel worker processes.
- Next largest: exact edge sampling, 20 s on CC-000 (213k edges, Python per edge in 10 workers).
- Fixes found while testing: flat faces seen edge-on gave fake outlines (float noise); cylinder strips had no smoothed
  normals (every vertex is on a cap edge), so outlines went missing until normals were smoothed per corner; outlines
  seen end-on (vertical extrusions in the top view) collapsed to points and made the joining step 54 s; a circle seen
  edge-on was lost by straight-line thinning. All fixed and checked on small test parts (filleted box with holes, sphere and torus, slanted cylinders, a grid of
  900 tall cylinders).
- Known left: hidden back edges that lie exactly under a visible edge draw as short dashes on top of it (harmless on
  paper, extra DXF entities); some cast-surface outlines are a little rough.

