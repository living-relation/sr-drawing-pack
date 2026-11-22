# Assembly test model and drawing package (2026-11-22)

A small test assembly, built in code, and its 11x17 drawing package from the handbuilt-cad engine.
It tests what the spike B plate could not: a BOM with a sub-assembly, balloons tied to BOM rows,
tapped and counterbored hole callouts, an assembly section, and whether a STEP keeps the component tree.

Test data only. The `SRDP-T-1xx` part numbers and the materials marked `(TEST)` are made up. Not for manufacture.

## The model (`SRDP-T-100`, 12 solids, 120 x 80 x 36 mm)

| Item | Qty | Part number | Description | Holes |
|---|---|---|---|---|
| 1 | 1 | SRDP-T-101 | Base plate | 4 M5 tapped through, 2 M4 tapped blind (drill 10 deep, thread 8 deep) |
| 2 | 1 | SRDP-T-110 | Cover sub-assembly | installs as one item |
| 2.1 | 1 | SRDP-T-111 | Cover plate | 4 clearance 5.5, 2 clearance 4.5 with a counterbore underneath |
| 2.2 | 1 | SRDP-T-112 | Handle | 2 M4 tapped through |
| 2.3 | 2 | SSH-M4-0.7 x 12 ALLOY-BO | Socket head screw | |
| 3 | 1 | SRDP-T-103 | Stop block | 2 clearance 4.5 with a counterbore on top |
| 4 | 4 | SSH-M5-0.8 x 16 ALLOY-BO | Socket head screw | |
| 5 | 2 | SSH-M4-0.7 x 16 ALLOY-BO | Socket head screw | |

Tapped holes are modelled at tap-drill diameter. No thread form is modelled.
Built with plain build123d. sr-cadlib was not used: it only runs inside Fusion (it needs the `adsk` modules).

## How to run

Use the Python of a handbuilt-cad clone (it has build123d, ezdxf, matplotlib, shapely). Run from this folder.

| Variable | Needed | Meaning |
|---|---|---|
| `HBCAD_ROOT` | yes | path to a handbuilt-cad clone (read-only) |
| `SRFASTENER_ROOT` | no | path to an sr-fastener clone; turns on the screw data check |
| `DRAWING_INITIALS` | if `~/.drawing-initials` is not set | the requester's initials for the rev log |

```
python build_assembly.py  ../_local/out/assembly-test     # writes SRDP-T-100.step
python check_step_tree.py ../_local/out/assembly-test     # prints JSON, writes step_tree_check.json
python make_package.py    ../_local/out/assembly-test     # PDF, PNG per sheet, DXF, checks
```

Output is git-ignored. Files: `SRDP-T-100.pdf`, `_sh1.png` to `_sh3.png`, `.dxf`, `.checks.json` (engine),
`.package_check.json` (this script), `REVLOG.md`, `step_tree_check.json`.

Sheets: 1 assembly views, BOM, rev table, notes. 2 build order (three steps). 3 section A-A and details B, C, D.

## Results

| Item | Result | Evidence |
|---|---|---|
| BOM rows and quantities | PASS | 8 rows. Rows and quantities equal the STEP tree and the hand-written expected tree. Leaf quantities add up to 12 = solids in the STEP. |
| Sub-assembly handling | PASS, with a spec trick | Row 2 is the sub-assembly, rows 2.1 to 2.3 its parts. Ballooned as item 2 where it installs as one item; its parts are ballooned on the step that builds it. The engine has no sub-assembly idea (gap 6). |
| Balloons | PASS | Every BOM row has a balloon somewhere (counted). Sheet 1 balloons the top-level items 1, 2, 3. Engine check: 0 overlaps, 0 crowded, nothing left unballooned. |
| Tapped through callout | PASS, with a wrapper | `4X M5x0.8-6H THRU` + `⌀4.2 THRU` and `2X M4x0.7-6H THRU` + `⌀3.3 THRU`. The thread line is the engine's; the tap-drill line is added (gap 5). |
| Tapped blind callout | PASS | `2X M4x0.7-6H ↧8` + `⌀3.3 ↧10`, from the engine. Drill depth is measured from the model. Thread depth is spec data (not in a STEP). |
| Counterbore callout | PASS | `2X ⌀4.5 THRU` + `⌴ ⌀8 ↧4.6`, from the engine, on the cover (underside) and the stop block (top). |
| Section / detail | PASS, with wrappers | Section A-A through one screw of every kind, capped, parts hatched opposite ways, screws not hatched. Details B, C, D at 3:1 carry the callouts. The engine has no assembly section (gaps 1 to 4, 7). |
| Overall reference dimensions | PASS | (120), (80), (36) in parentheses, from the engine. |
| Title block | PASS | Project, title, number, rev A, `SEE BOM`, scale, sheet n of 3, date, drawn, source all filled. |
| Rev table | PASS | From `REVLOG.md` beside the STEP. Rev A = `Initial`. Title block rev matches. |
| Notes | PASS | Four notes. No edge-break, torque or threadlocker note. |
| Visible edges only | PASS | 0 hidden-line items on all sheets. |
| Centre marks | PASS, with a wrapper | 8 marks on the top view (gap 2). Centre lines on the hole axes in the section and details. |
| DXF circles | PASS for circles | 10 CIRCLE entities on the VISIBLE layer (all the round edges of the top view). Pictorial views stay polylines (ellipses). |
| Engine rule check | PASS | `SRDP-T-100.checks.json` says `ok: true`. |
| STEP tree survival | PASS, one catch | Tree, quantities and positions come back exactly (position error 0 mm). 9 products, 13 placements, 7 solid shapes: repeated screws are stored once. Catch: build123d's importer changes spaces and dots in names to underscores (`SSH-M5-0_8_x_16_ALLOY-BO`). The real names are in the STEP text; the script reads them from there. |
| BOM from the STEP alone | PARTLY | Rows, quantities and part numbers: yes. Description and material: no, the STEP has one name per component. They come from the spec table (as ADR-002 expects). |
| Hidden-line time | PASS | Whole assembly: front 0.21 s, top 0.14 s, right 0.16 s, trimetric 0.16 s. |
| Sheet 1 scale | PASS, note | The engine picked 1:1.5. Its layout favours a large trimetric view over 1:1 flat views (gap 11). |
| Hole positions | NOT DONE | Where the holes sit in each plate is not dimensioned anywhere. The assembly flow has no plan view per part and no hole table (gap 12). |

## Engine gaps (each one is a run-time wrapper or a workaround in `make_package.py`)

1. `make_assembly` has no section view. The script cuts every solid itself and adds a sheet through the build-order hook.
2. No centre marks on assembly views. Added with the engine's `circle_marks`.
3. No cutting-plane line on assembly views. Drawn by the script (line, arrows, letters).
4. Section hatching: one direction only, one solid only, no way to leave fasteners unhatched. The script draws its own hatch lines.
5. A through tapped hole gets the thread only (`M5x0.8-6H THRU`). The style rule wants the tap drill too. Added by the script.
6. No sub-assembly idea: the BOM is flat. Indented item numbers (2.1) and "balloon as one item" are done by putting the solids on the sub-assembly row and hiding the child rows on sheet 1. The balloon circle is a tight fit for `2.1`.
7. No detail views on assembly sheets, no way to place a detail, and no way to leave parts out of one. The script calls the engine's `_detail_body` with its own position and a second cut without screws.
8. The DXF writer has no CIRCLE or ARC (known from spike B). `dxf_out.py` is the spike B writer, copied.
9. No continuation title block. Sheets 2 and 3 carry the full block (the SPEC wants a smaller one).
10. BOM text width is underestimated for upper-case text. Long descriptions overflow unless the column widths are tuned by hand.
11. No spec field for a minimum flat-view scale or a layout choice on sheet 1.
12. No hole-position dimensions in the assembly flow (ordinates exist only in `make_part`).
13. Not an engine fault: a STEP does not say which holes are tapped or how deep the thread is. Both are spec data here.

## Sources

| Value | Source |
|---|---|
| Screw head diameter, head height, socket size and depth (M4: 7.0, 4.0, 3.0, 2.0; M5: 8.5, 5.0, 4.0, 2.5) | ISO 4762:2004 Table 1, as stored in the sr-fastener catalog (`SRFastener/data/catalog.json`, family SSH-M, source keys `iso4762`, `hk_m_shcs`). Checked by `build_assembly.py` when `SRFASTENER_ROOT` is set (5 rows matched). |
| Screw lengths 12 and 16 | Listed lengths in the same catalog rows. |
| Screw part numbers, descriptions, material | sr-fastener `bom_fields()` (family SSH-M, finish ALLOY-BO). Same check. |
| Screw shape | Same simple shape sr-fastener builds: head, shank at nominal diameter, hex socket. No thread form, no chamfers. |
| Tap drills 3.3 (M4x0.7) and 4.2 (M5x0.8) | The engine's own table, `drawing/part.py` `TAP`. |
| Clearance holes 4.5 (M4) and 5.5 (M5) | Albany County Fasteners clearance hole chart, "Metric Series Clearance Holes (ISO 273)", normal fit: https://www.albanycountyfasteners.com/media/6b/b8/g0/1764944339/clearance-hole-chart.pdf |

## TBD (not confirmed, not guessed)

- Clearance holes against ISO 273 itself. Only a supplier chart that cites it was read.
- Counterbore 8.0 x 4.6 deep. A design value for this test: it clears the sourced M4 head (7.0 x 4.0). Not taken from a counterbore standard.
- Thread depth 8 and drill depth 10 of the blind holes, plate sizes, hole positions, materials: design values for this test.
- STEP schema: build123d wrote AP214 (`AUTOMOTIVE_DESIGN`). handbuilt-cad's model rule asks for AP242.
- A Fusion round trip of this STEP (import, component names, re-export) was not run.
