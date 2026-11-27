# SR Model Viewer

3D viewer for vault models (ADR-066, ADR-067). One HTML page, no install. Nothing it does changes the model file.

- Make the model file: in `SRDrawingPDF/`, run `python -m vieweng.glb part.step part.glb` (add `--fine` for a smoother mesh).
- Open it: `index.html?src=<url of the .glb>`, or open the page and drop / pick a `.glb`.
- Mouse: left drag orbits, right or middle drag pans, wheel zooms. Click selects a part; Ctrl, Shift or Cmd click adds
  or removes parts; click empty space to clear. Double-click fits to a part. Tree rows select the same way (a
  sub-assembly row selects all its parts).
- Explode: with nothing selected the slider explodes the whole model; with parts selected it explodes only those.
- Move parts (`M`): drag a part to move it and everything selected with it, in the screen plane. Reset positions
  puts every part back.
- Keys: `h` hide selected, `f` fit, `m` move mode, `Ctrl+A` select all shown, `Esc` clear selection.
- Phones and tablets: turn on Multi-select to add parts by tapping.
- Panel: explode slider, move, multi-select, hide selected, isolate, show all, reset positions, hide hardware, edges
  on/off, part tree with show/hide boxes.
- three.js loads from the jsDelivr CDN; a vault with no internet needs those files hosted next to the page.
