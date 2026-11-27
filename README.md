# SR Drawing Pack

**Research stage: not ready for use. Milestones and done criteria are in `docs/SPEC.md`.**

Goal: a drawing editor for Autodesk Fusion designs in the handbuilt-cad sheet style (title block, revision
table, the drawing's own BOM). The app drafts most of the drawing from the model; the engineer has full
control in an editor window opened from Fusion. Output: PDF; DXF is still open (ADR-032). Views are made from
a STEP plus sr-export's `bom.json`, in four render modes (ADR-028, ADR-029, ADR-040).

- Milestones and requirements: [docs/SPEC.md](docs/SPEC.md)
- Decisions: [docs/DECISIONS.md](docs/DECISIONS.md)
- Agent rules: [AGENTS.md](AGENTS.md)
- Drawing style rules: [.claude/rules/drawing-style.md](.claude/rules/drawing-style.md)
- Research and test results: [docs/RESEARCH.md](docs/RESEARCH.md)
- External repos referenced (read-only): [docs/REFERENCES.md](docs/REFERENCES.md)

## Drawing engine and Fusion add-in
The engine and editor (joined from sr-drawing-pdf, ADR-065) live in [`SRDrawingPDF/`](SRDrawingPDF). Install by a
junction named `SRDrawingPDF` in Fusion's AddIns folder pointing at the `SRDrawingPDF` folder of this clone; update
with `pull.cmd`, then restart the add-in. Full steps: [docs/engine/ADDIN-README.md](docs/engine/ADDIN-README.md).
Tests: `python -m pytest`; repo check: `python tools/check.py`.

License: MIT. See [LICENSE](LICENSE).
