# Decisions

Append only. A change is a new entry that names the one it supersedes.
Entry format: ID, Status, Context, Decision, Rejected, Supersedes, Reopen if.

## ADR-001: Architecture (2026-11-19)
- Status: Under review (open question Q1, editing surface)
- Context: Drawings must match the handbuilt-cad sheet style and be editable after generation.
- Decision: Thin Fusion add-in plus the handbuilt-cad drawing engine outside Fusion.
- Rejected: none yet; spikes A (native Fusion drawing) and B (custom editor) run first (ADR-016).
- Supersedes: none
- Reopen if: a spike shows this cannot give drag-and-drop views, linked projected views or linked BOM copies.

## ADR-002: BOM source (2026-11-19)
- Status: Accepted
- Context: BOM fields can be wrong or missing in the Fusion model.
- Decision: Read both Fusion's component tree and a spec file. The spec file overrides Fusion.
- Rejected: Fusion only; spec file only.
- Supersedes: none
- Reopen if: the two sources disagree often enough to confuse users.

## ADR-003: Thumbnails (2026-11-19)
- Status: Accepted
- Context: BOMs and lists show a picture per row.
- Decision: Shaded isometric view. Clicking a thumbnail in a list or BOM expands it.
- Rejected: line-art thumbnails.
- Supersedes: none
- Reopen if: where "click to expand" happens (Q4) rules this out.

## ADR-004: Export formats (2026-11-19)
- Status: Accepted, format list open (see ADR-013)
- Context: Each drawing has a purpose (review, cutting, records) and may need more than one file type.
- Decision: PDF, DXF and DWG as check boxes, any combination.
- Rejected: one fixed format.
- Supersedes: none
- Reopen if: DWG needs a paid or restrictive converter.

## ADR-005: Name (2026-11-19)
- Status: Accepted
- Context: The project needed a name.
- Decision: SR Drawing Pack.
- Rejected: none recorded.
- Supersedes: none
- Reopen if: handed to Spark Robotic under another name.

## ADR-006: Dimensions (2026-11-19)
- Status: Accepted
- Context: Assemblies and parts need different dimension sets.
- Decision: Assemblies get overall sizes as reference dimensions (in parentheses). Parts always get full manufacturing dimensions. The user can add any dimension type by hand on any drawing.
- Rejected: full dimensions on assemblies.
- Supersedes: none
- Reopen if: a drawing type needs a different default.

## ADR-007: Output style (2026-11-19)
- Status: Accepted
- Context: Existing drawings set the house style.
- Decision: Match the existing handbuilt-cad drawings in the models folder.
- Rejected: Fusion's default templates.
- Supersedes: none
- Reopen if: Spark Robotic adopts a different template.

## ADR-008: Source files (2026-11-19)
- Status: Accepted
- Context: f3d skips a conversion step; STEP is the fallback.
- Decision: Generate from f3d when possible, STEP if needed. A STEP used this way is saved with the drawing as a non-editable reference.
- Rejected: STEP only.
- Supersedes: none
- Reopen if: f3d cannot be read outside Fusion for the chosen architecture.

## ADR-009: handbuilt-cad is read-only (2026-11-19)
- Status: Accepted
- Context: handbuilt-cad is a separate working toolkit.
- Decision: Never change it. Copy and modify its tools into this repo instead.
- Rejected: editing it in place; importing it as a dependency.
- Supersedes: none
- Reopen if: Daniel asks for a shared library.

## ADR-010: Target Fusion account (2026-11-19)
- Status: Accepted
- Context: The tool is for Spark Robotic engineers.
- Decision: Target the Spark Robotic team account on the work PC. Access is granted later. Personal repo now, handed to Spark Robotic later.
- Rejected: none.
- Supersedes: none
- Reopen if: the hand-over plan changes.

## ADR-011: Revision format (2026-11-19)
- Status: Accepted
- Context: Three sources listed three different skip sets. Daniel chose the one sr-drawing-pdf and handbuilt-cad already use.
- Decision: Full revs A, B, C ... Z, AA, AB ..., skipping I, L, O and Q. A clerical rev adds a two-digit decimal (A.01, A.02 ...): "clerically revised this many times at this letter". The decimal resets when the letter goes up (C.02 becomes D). Clerical revs are never in the rev log table. A draft has no rev at all: the rev stays blank until the moment of approval in the PDM. The app formats and checks revs and refuses bad ones; it never assigns one.
- Rejected: Fusion's skip set (I, O, Q, S, X, Z); decimals as pre-release markers.
- Supersedes: none
- Reopen if: the Spark Robotic engineering data rules (which list I, L, O) are confirmed as different on purpose.

## ADR-012: Scope boundary with the PDM (2026-11-19)
- Status: Accepted
- Context: Daniel's PDM handles file states (Initial, Awaiting approval, Rejected, Production, Under change), approval, visibility, check-in/out and document history. Fusion's cloud is what is being worked around.
- Decision: This app only makes drawings that follow the drawing rules and template, gives the editing features, and exports the needed file types. It does not approve, assign revs, track states, hide files or lock them.
- Rejected: building PDM features into the drawing app.
- Supersedes: none
- Reopen if: Daniel asks the app to take over a PDM job.

## ADR-013: Outputs open without Fusion (2026-11-19)
- Status: Accepted
- Context: Users without a Fusion seat must download and view drawings.
- Decision: Every released output is a standard file that opens without Fusion. A Fusion-only drawing file (.f2d) is never the deliverable. Which formats each drawing purpose needs is still open.
- Rejected: Fusion-native drawings as the released file.
- Supersedes: none
- Reopen if: none.

## ADR-014: Release package and data card (2026-11-19)
- Status: Proposed. Package contents not final (Daniel, 2026-11-19).
- Context: Data is lost on f3d export, and the PDM viewer needs a data card.
- Decision: Working shape: locked STEP + drawing + `<PN> <Desc>.sr.json` data card, all sharing one number and description, told apart by extension. Some items (CNC, 3D printed) will carry up to 4 file types, including controlled sliced files and G-code. Card fields match sr-bom's keys (part_number, description, material). Draft: `docs/DATA-CARD.md`.
- Rejected: none yet.
- Supersedes: none
- Reopen if: the package is finalised.

## ADR-015: Users and profile (2026-11-19)
- Status: Accepted
- Context: 5 to 6 engineers install the app. Title block and rev log need a name and initials.
- Decision: No sign-in. The app keeps a local profile with preferred name and initials. Google sign-in is optional later (everyone has a Google enterprise account).
- Rejected: a required login.
- Supersedes: none
- Reopen if: the PDM needs a verified identity from the app.

## ADR-016: Decide the editing surface by spikes (2026-11-19)
- Status: Accepted
- Context: Model views are the hardest part for every approach.
- Decision: Run spike A (native Fusion drawing) and spike B (custom editor) before choosing. Each gets a "views" row: base + projected + iso, plus section and detail. Re-test Fusion's preview revision table and title block API in a scratch document first.
- Rejected: choosing now without evidence.
- Supersedes: none
- Reopen if: none.

## ADR-017: One agent rules file (2026-11-19)
- Status: Accepted
- Context: Sibling repos use AGENTS.md only.
- Decision: `AGENTS.md` is the only agent rules file. No CLAUDE.md.
- Rejected: per-tool rules files.
- Supersedes: none
- Reopen if: none.

## ADR-018: No DWG export (2026-11-19)
- Status: Accepted
- Context: DWG from our own engine would need an outside converter with its own license. Daniel does not need DWG.
- Decision: The app exports PDF and DXF. DWG is dropped. Other formats may be added per drawing purpose; that list is still open.
- Rejected: DWG through a converter.
- Supersedes: the DWG part of ADR-004
- Reopen if: a customer or shop requires DWG.

## ADR-019: The PDM issues part and assembly numbers (2026-11-19)
- Status: Accepted
- Context: Numbers must be unique and simple, and serve as both drawing number and model number. Two PCs each generating the "next" number could hand out the same one.
- Decision: The PDM hands out every part and assembly number from its single counter. The app never generates a number; it uses the one it is given.
- Rejected: the app generating numbers; a shared counter file; hand-typed numbers.
- Supersedes: none
- Reopen if: the app must work before the PDM can issue numbers.

## ADR-020: Repo scope and split with sr-drawing-pdf (2026-11-19)
- Status: Accepted
- Context: Planning had started to reach into PDM work, and two repos were at risk of doing the same spike.
- Decision: This repo is only the drawing generator. Vault, numbering, approval workflow, check-in/out, rev stamping and fab-floor viewing belong to the separate sparkCAD / PDM app; this repo only exposes clean hooks for it. This repo owns requirements, rules, decisions and the plan. sr-drawing-pdf proves out the editor core (sheet engine, template, title block, BOM table, subset-font PDF output); its results are evidence and that spike is not repeated here.
- Rejected: PDM features here; a second editor-core spike.
- Supersedes: narrows ADR-012 and the spike B wording of ADR-016
- Reopen if: Daniel changes the split.

## ADR-021: Views come from saved model orientations (2026-11-19)
- Status: Accepted. How a view becomes 2D geometry is open.
- Context: Views must be picked, not rotated by hand on the sheet.
- Decision: A side panel lists the home view, standard views (front, top, side, back, bottom, iso), variations (trimetric and so on) and the user's saved custom-named orientations. The user drags them onto the sheet, SolidWorks-style. The 3D model is never rotated inside the 2D drawing. Saved orientations are read through Fusion's API: Autodesk's reference documents `Design.namedViews`, a `NamedViews` collection with `itemByName` and `add(camera, name)`, and `NamedView.camera` (introduced September 2023). Verified against the docs only, not yet run in Fusion. The docs list four built-in views (TOP, FRONT, RIGHT, HOME), so back, bottom, iso and the variations must be computed by the app. If a live test shows named views cannot be read, a small "save drawing orientation" tool ships inside this package, not as a separate add-in.
- Rejected: rotating the model in the drawing; a separate orientation add-in.
- Supersedes: none
- Reopen if: the live test fails. Open: 2D hidden-line geometry from (a) Fusion's native drawing engine on a saved cloud design, then extracting lines, or (b) out-of-process projection from exported STEP with the handbuilt-cad build123d engine. Both are being tested in sr-drawing-pdf; do not commit yet.

## ADR-022: Identity, data card and the rev hook (2026-11-19)
- Status: Accepted
- Context: Answers to the open data card questions.
- Decision: The part number is the identity; Fusion's hidden component ID is kept only as a trace. The app writes the trimmed data card in `docs/DATA-CARD.md`. At approval the PDM calls the app to re-export with the rev filled in. STEP, sliced files and G-code are package files the PDM handles.
- Rejected: a hidden ID as identity; a hash-chained history in the app; the PDM stamping files itself.
- Supersedes: the Proposed parts of ADR-014
- Reopen if: the PDM app needs a different hand-off.

## ADR-023: License, skills, thumbnail expand (2026-11-19)
- Status: Accepted
- Context: Plan questions Q2, Q3 and Q4.
- Decision: MIT license. Skills are declared in `AGENTS.md`, not committed. "Click a thumbnail to expand" happens in the editor.
- Rejected: committed skill copies; expand in a Fusion palette or in the PDF.
- Supersedes: none
- Reopen if: Spark Robotic needs a different license at hand-over.

## ADR-024: Editing surface is a custom editor, worked as a hybrid (2026-11-22)
- Status: Accepted. Where the editor runs and how views are made are open.
- Context: Spike A showed a native Fusion drawing cannot carry the house style through the API. Spike B showed the handbuilt-cad engine can make the views and sheet from STEP (docs/RESEARCH.md). Daniel chose a custom editor on 2026-11-20 and set how it works on 2026-11-22.
- Decision: Build our own editor, using Fusion's API as a toolbox where it helps. At creation the user picks the style, sheets, sheet size, default views and an auto-dimension scheme, and the app generates most of the drawing: default views placed, automatic dimensions and automatic annotation. The engineer then has full control over everything already on the sheet, and adds sheets and detail views as needed. The editor has built-in agent help or automation for when the engineer wants help while editing.
- Rejected: a native Fusion drawing as the editing surface; fully automatic output with no editing.
- Supersedes: the "Under review" status of ADR-001. Closes spikes A and B of ADR-016; spike C has not been run.
- Reopen if: the editor slice shows the editor screen cannot be built at a reasonable cost. Open: a panel inside Fusion or a separate window; views from STEP with the engine (spike B evidence) or another route.

## ADR-025: Visible edges only (2026-11-22)
- Status: Accepted. A per-view switch is open.
- Context: The first spike B sheet drew hidden lines dashed. Daniel's review asked for visible edges only.
- Decision: Views show visible edges only: no hidden lines in any view, including the pictorial. A hidden feature is shown with a section or a detail.
- Rejected: hidden lines on by default.
- Supersedes: none
- Reopen if: Daniel asks for hidden lines on a view. Open: whether the editor offers a per-view "show hidden" switch that is off by default.

## ADR-026: View labels and scale (2026-11-22)
- Status: Accepted. Section view labels to confirm.
- Context: The test sheets put a label, a scale or a group label under the views. Daniel set the rule.
- Decision: The drawing template sets one scale for the sheet, shown in the title block. A view at the sheet scale gets no scale label. Default views (front, top, right, left, back, bottom, trimetric, isometric and the like) get no view label. A view gets a subtitle only when it is placed at a different scale or the user wants it labelled. Detail views are labelled with their letter and scale.
- Rejected: a label under every view; one group label per row of views; a `TRIMETRIC VIEW` label by default.
- Supersedes: none in this file. It replaces the group-label and pictorial-label lines of the 2026-11-22 style note.
- Reopen if: none. Open: section views are assumed to keep their letter label (`SECTION A-A`), like details.

## ADR-027: Tolerances on dimensions and holes (2026-11-22)
- Status: Accepted. Per-hole overrides are open.
- Context: The title block carries one general tolerance block. Holes usually need a tighter or different tolerance, depending on their purpose.
- Decision: The title block tolerance applies unless a dimension says otherwise. The engineer can set a separate tolerance for hole positions and hole sizes; it applies to all holes in the file and is called out in the hole annotation. Every dimension the user adds has a tolerance option.
- Rejected: one tolerance for everything; hole tolerances fixed by the app.
- Supersedes: none
- Reopen if: none. Open: whether one hole or one group of holes can carry its own tolerance, different from the file-wide hole tolerance.

## ADR-028: STEP plus a Fusion data file, exported together (2026-11-22)
- Status: Accepted
- Context: A STEP gives the engine exact geometry and the component tree, but not the BOM description or material, and not which holes are tapped or how deep the thread is. Engineers who make drawings always have Fusion. An `.f3d` cannot be read outside Autodesk software.
- Decision: When a drawing is made, the add-in exports the STEP and a data file from the open Fusion design in the same step. The engine draws views from the STEP and takes BOM fields and hole / thread definitions from the data file. The `.f3d` is never read by the engine. Views come from the STEP with the engine (spike B), which settles the open point of ADR-021.
- Rejected: STEP alone (BOM and thread data missing); reading the `.f3d` directly (no open reader); Fusion's drawing engine for views (spike A).
- Supersedes: the open point of ADR-021 (how a view becomes 2D geometry). Works with ADR-002 (the spec file still overrides Fusion).
- Reopen if: a real hub design shows data the export cannot reach. Evidence: docs/RESEARCH.md, "Fusion data file with the STEP".

## ADR-029: sr-export's data file, and the drawing's own BOM (2026-11-23)
- Status: Accepted
- Context: sr-export already writes `<name>.bom.json` next to every STEP (schema `sr-bom-sidecar` v1): BOM rows with occurrence paths, linked source and version, holes, threads, tap drills, mass and thumbnails. Our own export script repeated part of it.
- Decision: The engine reads sr-export's `bom.json` as its data file (the "data file" of ADR-028). `research/fusion-data/export_step_and_data.py` is retired as a research script. The drawing still carries its own BOM: it can be moved around the sheets, and every row links to the actual part in every view, so balloons and other annotations can be placed on that part. Part visibility is added to sr-export's file so each view can have its own hide list (sr-export change).
- Rejected: our own export script; a BOM that is only an external file.
- Supersedes: the "data file" source in ADR-028. Works with ADR-002 (the spec file still overrides Fusion fields).
- Reopen if: sr-export's schema changes in a breaking way.

## ADR-030: View quality, fast by default (2026-11-23)
- Status: Accepted
- Context: On a real 147-part assembly the exact hidden-line removal did not finish a view in 7 minutes; the polygonal ("fast") method took 2.5 to 7.3 s per view (docs/RESEARCH.md). SolidWorks, FreeCAD and Creo offer the same choice.
- Decision: Views are made with the fast method by default. Exact edges are snapped in where dimensions, hole callouts and DXF need true circles and arcs. A full-fast option (no snapping) is offered. The engineer can switch any single view between the methods in the drawing.
- Rejected: exact only (too slow on real assemblies).
- Supersedes: none
- Reopen if: the fast method misses edges that matter on real drawings.

## ADR-031: Real test design (2026-11-23)
- Status: Accepted
- Context: Tuning needs a real, typical assembly.
- Decision: `custom-pdm-enclosure-v2c-F1` (custom-pdm project, 147 parts, linked parts, a sub-assembly, PCBs) is the reference assembly for speed and quality tests.
- Rejected: only small test assemblies.
- Supersedes: none
- Reopen if: Daniel names another reference design.
