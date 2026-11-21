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
