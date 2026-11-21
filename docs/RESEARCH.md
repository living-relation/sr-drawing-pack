# Research and test results (2026-11-19)

Tested on DansPC, Fusion 2706.1.17, through the autodesk-fusion-mcp add-in (`execute_python`).
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

Tested on DansPC, Fusion 2706.1.17, through Fusion's built-in MCP (script tool). Scratch design
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

Tested on DansPC. Engine: handbuilt-cad `drawing/dwg.py`, imported read-only, run out of process with
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
