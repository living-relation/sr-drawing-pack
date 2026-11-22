# Editor slice (research spike)

The first thin clickable piece of the drawing editor. It is a spike, not the product.
It answers one question: how hard is the editor screen?

A small local Python server holds the drawing and asks the handbuilt-cad engine for view geometry.
A plain web page (SVG, no framework, no build step) shows the sheet and sends every action to the server.
It runs in any browser. A Fusion panel hosts a web page too, so the same page can go either way.
Nothing here touches Fusion.

## Run it

Use the Python of a handbuilt-cad clone (it has build123d). Nothing is installed.

```
set HBCAD_ROOT=<path to your handbuilt-cad clone>
<that clone's python> research/editor-slice/server.py
```

Then open `http://127.0.0.1:8791/`. In PowerShell the first line is `$env:HBCAD_ROOT='<path>'`.

Options: `--port 8791`, `--step <file.step>` (draw your own model instead of the test plate),
`--doc <file.json>`, `--out <folder>`. The saved drawing and the exported PDF / PNG go to
`research/_local/editor-slice/` (git-ignored) unless you say otherwise.

Tests, from this folder: `<that clone's python> -m unittest -v test_slice`
(16 tests. The rule tests need no CAD. The server tests are skipped when `HBCAD_ROOT` is not set.)

## Files

| File | What it is |
|---|---|
| `docmodel.py` | The drawing document and all its rules. Plain Python, no CAD. Used by the server and the tests. |
| `server.py` | Standard-library HTTP server on 127.0.0.1. Engine imported read-only through `HBCAD_ROOT`. |
| `static/index.html`, `static/editor.js` | The page. Draws the sheet, turns mouse actions into commands. |
| `test_slice.py` | unittest: rules, then every endpoint against a server started in the test. |

Endpoints: `GET /api/meta`, `GET /api/view?name=front` (or `?cam=x,y,z&up=x,y,z`), `GET /api/doc`,
`POST /api/doc` (save), `POST /api/op` (one command), `POST /api/undo`, `GET /api/export.pdf`.

## What works

Checked by clicking through it in a real browser on 2026-11-22, and by the tests.

- Drag a view from the left panel onto the sheet. It lands where dropped, at the sheet scale.
  Views: front, top, right, left, back, bottom, trimetric (the engine's `iso` camera).
- Drag a placed view to move it.
- Select a view and make a projected view to its left, right, top or bottom. Third-angle:
  right of front is the right view, above front is the top view.
  It works from any parent, not only front. A child of the top view is the model seen from that side,
  turned the way the top view is turned. Such a view has no standard name, so it is called `top/right`.
- Link rules as in the SPEC: children follow the parent; a left / right child slides only left-right;
  a top / bottom child only up-down; "Break link" frees a child; a freed child makes its own projected views.
  A thin dashed blue line shows a live link.
- Delete a view (button or Delete key). Its children stay as free views.
- Change the sheet scale (the engine's standard scales). Views resize, and linked children keep their gap.
- Add and remove sheets, switch between them. Sheet 1 cannot be removed.
- Undo (button or Ctrl+Z), 50 steps, every command.
- Save writes the drawing as JSON. The server loads it again at the next start.
- Export PDF: every sheet through the engine (`dwg.Sheet`, `dwg.frame`, `dwg.render`), 11x17 size B,
  every view at its position and scale. The PDF matched the screen layout.
- Visible edges only. No hidden lines anywhere. Tangent edges only in the trimetric.
- `--step` loads a STEP file in place of the plate (code path is there; only the plate was tested).

## What is faked or missing

- Every sheet uses the same frame. A continuation sheet should get the smaller block. Not done.
- The title block on screen is a grey box. The engine draws the real one only in the PDF.
  Its fields are fixed test text; REV, MATERIAL and DRAWN are blank on purpose.
- Each view has its own label. The house style wants one group label per row. Label text on screen is close
  to the PDF, not exact.
- One sheet size (B). One scale per sheet; the document can hold a per-view scale but the page has no control for it.
- A view cannot be moved to another sheet. No pan or zoom, no snapping, no multi-select, no keyboard nudge.
- Nothing stops a view from sitting on the title block or off the sheet.
- No centre marks, dimensions, sections, details, BOM, rev table or DXF (out of scope here).
- No saved Fusion orientations; the panel is the seven standard views.
- One user, one drawing, one model per server. No file dialogs.
- Not tested: inside a Fusion palette, on a real assembly, with a touch screen.

## What was hard, and what this tells us

1. The screen basics were not hard. Panel, drag, select, link rules, sheets, undo, save and PDF came to
   about 870 lines in one working session. SVG fits a drawing sheet well: millimetre units, exact lines.
2. Keep the rules in one place. The server owns the document; the page only sends commands and redraws.
   The page repeats one rule (the one-axis slide) so the drag looks right before the server answers.
   That split held up and made undo almost free.
3. The real problem is two drawing engines. The screen is SVG drawn by the page; the PDF is drawn by the
   engine. Views match because both use the same polylines. Everything else (title block, labels, later
   tables and dimensions) would have to be written twice and kept the same. The fix is to have the engine
   hand its sheet items (lines, text, hatches) to the page, so one list feeds both. Do this before
   building more screen.
4. Projected views need the view size to be placed, and a scale change must re-space linked views.
   So the rules need a small "how big is this view" hook into the CAD side. Done here as one function.
5. Fast clicks raced each other until commands were queued. Any real editor needs that from day one.
6. A Windows trap: two servers can share one port without an error, and the old one keeps answering.
   The server now refuses a busy port. Stopping the shell does not stop the Python process.
7. Hidden-line removal took well under a second per view on the plate and is cached per camera.
   A real assembly is untested, and so is sending tens of thousands of polylines to the page.

## Estimate for the full editor screen

Judgement, not measurement. Spike B rated the editor screen L (three weeks or more).

- Views and sheets screen done properly (pan, zoom, snap and align, multi-select, per-view scale, move
  between sheets, keep-out areas, group labels, continuation frame, saved orientations): about 1 to 2 weeks.
- One item list for screen and PDF (point 3), with title block, rev table and BOM shown on screen from
  `sheet2d`: about 1 to 2 weeks.
- Running inside a Fusion palette or as its own window, start and stop of the server, real assembly speed:
  about 1 week, with the most unknowns.

Total: about 3 to 5 weeks for the screen without annotations. So still L, but the low end, and the risk
has moved from "can we drag views" (yes) to "one renderer for screen and PDF". Placing and editing
dimensions and other annotations by hand is on top of this and is still the biggest item.
