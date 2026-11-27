# SR Model Viewer

View-only 3D viewer for vault models (ADR-066). One HTML page, no install.

- Make the model file: in `SRDrawingPDF/`, run `python -m vieweng.glb part.step part.glb` (add `--fine` for a smoother mesh).
- Open it: `index.html?src=<url of the .glb>`, or open the page and drop / pick a `.glb`.
- Mouse: left drag orbits, right or middle drag pans, wheel zooms. Click selects a part; double-click fits to it.
  Keys: `h` hide selected, `f` fit, `Esc` clear selection. Touch works on phones and tablets.
- Panel: explode slider, hide selected, isolate, show all, hide hardware, edges on/off, part tree with show/hide boxes.
- three.js loads from the jsDelivr CDN; a vault with no internet needs those files hosted next to the page.
