> **Superseded (ADR-032, 2026-11-23):** the data card is the PDM's job, not this app's. This file is kept
> only as reference for the PDM project; nothing in this repo writes it.

# SR data card (`<part number> <description>.sr.json`), draft 2

Status: **draft, scope under review** (ADR-014, Proposed). Nothing uses it yet. The release package is
not final. The PDM owns approval, states and history (ADR-012); this draft only covers what the
drawing app would write.

## What the app writes (proposed minimum)

```json
{
  "schema": "sr-data-card/1",
  "part_number": "SR-10042",
  "description": "Motor Plate",
  "material": "Aluminum 6061",
  "kind": "part",
  "rev": "",
  "created_by": "DG",
  "created_date": "2026-11-19",
  "source": {
    "f3d_name": "SR-10042 Motor Plate",
    "f3d_version_id": "<Fusion DataFile version id>",
    "component_id": "<Fusion Component.id, trace only>"
  },
  "files": {
    "step": {"name": "SR-10042 Motor Plate.step", "sha256": "..."},
    "pdf":  {"name": "SR-10042 Motor Plate.pdf",  "sha256": "..."}
  }
}
```

- Field names match sr-bom's keys (`part_number`, `description`, `material`), read from the same Fusion
  component properties, so neither tool needs a translation step.
- `rev` is blank on a draft. The PDM fills it at approval (ADR-011).
- `files` lists every file in the package by extension. More types (DXF, sliced file, G-code) are added
  the same way.
- `source` records which f3d version produced the STEP.

## What the PDM adds later (not built by this app)

- Document history: one entry per state change (Initial, Awaiting approval, Rejected, Production,
  Under change), with who, when and the change description.
- Approved by / approved date, and the rev given at approval.
- If tamper evidence is wanted: each history entry stores the hash of the entry before it, and the PDM
  keeps its own copy of the newest hash. A plain JSON file cannot stop edits by itself; PDM
  permissions do that.

## Settled (see DECISIONS.md)

- Identity is the part number (ADR-022). `component_id` is a trace only.
- The PDM issues part numbers (ADR-019) and handles the other package files (STEP, sliced files, G-code).
- At approval the PDM calls the app to re-export with the rev filled in (ADR-022).
