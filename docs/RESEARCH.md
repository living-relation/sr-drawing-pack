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
- On the test sheet the API exposed only `drawingSymbols` and `customTables` collections. No way was
  found to build a revision table or a styled BOM through it.
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
