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

## ADR-032: Data card and output formats (2026-11-23, Daniel's answers of 2026-11-20)
- Status: Accepted. DXF is open.
- Context: Daniel's 2026-11-20 answers were not recorded (workstation-core coordinator-kit: record every answer in its home the same turn).
- Decision: The data card is not the app's job: the PDM makes and keeps it, pulls most data from the imported files, and the user fills in the rest; its history is the PDM's too. File control and locking are the PDM's. The app's lane is the STEP and the drawing, ready for a PDM, with a hand-off modelled on Fusion Manage and SOLIDWORKS PDM. Output: PDF for sure, no DWG. DXF is undecided; Daniel expects it for CNC laser and router cutting.
- Rejected: the app writing the data card (ADR-014, ADR-022).
- Supersedes: the data-card parts of ADR-014 and ADR-022; the "PDF and DXF" export of ADR-018 becomes "PDF; DXF open".
- Reopen if: the PDM needs the app to write a card.

## ADR-033: Hidden lines never drawn, no per-view switch (2026-11-23)
- Status: Accepted
- Context: Question H4. handbuilt-cad DRAWING-RULES 14 and its AGENTS.md rule 5 say never show hidden lines; ADR-007 makes that house style the target.
- Decision: No view ever shows hidden lines. There is no per-view "show hidden" switch; a hidden feature is shown with a section or detail.
- Rejected: a per-view switch, off by default.
- Supersedes: the open point of ADR-025.
- Reopen if: Daniel asks for hidden lines on a view.

## ADR-034: Sub-assemblies, hole positions, tapped holes (2026-11-23)
- Status: Accepted
- Context: Questions H15, H16, H17. handbuilt-cad skill cad-drawing and DRAWING-RULES 21a and 40; Daniel's 2026-11-22 drawing instruction.
- Decision: A finished sub-assembly is one installation item (one balloon) in its parent package; its own parts are ballooned on the step that builds it, or in its own package. Hole positions and other fabrication-critical sizes go in dimensioned assembly sections and details, never on separate part sheets. Tapped holes are called out with thread and tap drill; through holes (plain or tapped) are THRU with no depth; blind holes show the real thread depth and the drill depth when it is deeper.
- Rejected: ballooning every child on sheet 1; separate part sheets for hole positions; thread-only callouts.
- Supersedes: none
- Reopen if: a hole table is wanted as well as the sections and details.

## ADR-035: Sheet scale and section labels (2026-11-23)
- Status: Accepted
- Context: Questions H18, H20. Daniel's 2026-11-22 instruction to follow the drawing style note (scale that fills the sheet; sections lettered and labelled). ADR-026 dropped labels only for default views.
- Decision: The sheet scale is the largest standard scale that fits the views with room for dimensions. Section views keep their label (`SECTION A-A`) and letters, like detail views; the label adds a scale only when it differs from the sheet.
- Rejected: a fixed 1:1; unlabelled sections.
- Supersedes: none
- Reopen if: none.

## ADR-036: Thumbnails may live outside the drawing (2026-11-23, Daniel's answer of 2026-11-22)
- Status: Accepted. Thumbnail source is open (H25).
- Context: Daniel: thumbnails can live in a separate external BOM file; they are not required on the drawing sheet.
- Decision: BOM thumbnails go in an external BOM file; the drawing's own BOM (ADR-029) does not need them. F3D tested at 45 of 45 parts, about 0.5 s each, on the reference assembly.
- Rejected: thumbnails required on the drawing sheet.
- Supersedes: the "on the drawing" reading of ADR-003.
- Reopen if: Daniel wants thumbnails on the sheet.

## ADR-037: Editor window, view moves, deletes (2026-11-23)
- Status: Accepted
- Context: Questions H3, H12, H13.
- Decision: The editor is a separate window opened from a button in Fusion. When the sheet scale changes, placed views keep their positions; if views overlap, the user moves them. Deleting a parent view leaves its projected children as free views.
- Rejected: a panel inside Fusion; keeping the parent-child gap on a scale change (what the editor slice built); deleting children with the parent.
- Supersedes: the "where the editor runs" open point of ADR-024.
- Reopen if: none.

## ADR-038: Tolerance by decimal places, per dimension (2026-11-23)
- Status: Accepted
- Context: Question H21. Builds on ADR-027.
- Decision: Any feature dimension can carry its own tolerance. The title block's tolerance block sets the tolerance for each number of decimal places, so the number of decimals shown on a dimension sets its tolerance. Each dimension shows the default number of decimals, or more or fewer as the user sets it. In a hole table the decimals can be set per row or for the whole table.
- Rejected: one fixed tolerance per file for holes.
- Supersedes: the open point of ADR-027.
- Reopen if: a dimension needs an explicit ± tolerance that no decimal count gives.

## ADR-039: Thumbnails from F3D; view lines must look like a drawing (2026-11-23)
- Status: Accepted. The view method per model type is being tested.
- Context: Questions H25 and H32 (DRAWING-RULES 16 against the fast method of ADR-030).
- Decision: BOM thumbnails come from F3D, bundled with the app. For views, the test is the result: every view shows smooth, continuous lines and never looks like a mesh, whatever the model is made of (solids, surfaces, B-rep bodies or mesh bodies). A drawing that shows thousands of triangle edges from a mesh body is a defect. The method that meets this per model type is chosen from example drawings.
- Rejected: Fusion screenshots for thumbnails; a method chosen by name rather than by how the drawing looks.
- Supersedes: refines ADR-030.
- Reopen if: the example drawings show no method meets the test for a model type.

## ADR-040: Render modes per view (2026-11-23)
- Status: Accepted. FAST DRAFT reading to confirm; more tests on simple and large models first (H34b).
- Context: Daniel reviewed the view-method example sheet (docs/RESEARCH.md, "View methods compared") and named the modes.
- Decision: Four render modes, chosen per view:
  - UHQ: exact B-rep hidden-line removal (row 1 of the example).
  - HQ: fast polygonal method with the pieces joined into continuous lines (row 3).
  - DRAFT: fast polygonal method, raw pieces (row 2).
  - FAST DRAFT: mesh creases and silhouettes (row 5), optional, for very large files with many parts or sheets.
  Lower modes can be used while editing, so the drawing loads, saves and redraws quickly. At the final save the user
  chooses HQ or UHQ and the views are converted then. The mode picker shows a thumbnail of each mode (first set from
  the example sheet). Any placed view can be switched to another mode from its right-click menu ("Change render mode").
  All three of UHQ, HQ and DRAFT are acceptable on screen.
  Tangent edges have their own three settings per view, to speed up rendering or improve the look: hidden, drawn,
  or partial (what "partial" draws is to be confirmed). Default: drawn, in every view (Daniel, 2026-11-23). This
  differs from handbuilt-cad DRAWING-RULES 16, which drops tangent edges from orthographic views; for this app
  Daniel's default wins.
- Rejected: one fixed method for all views; a mesh body drawn from its triangles.
- Supersedes: refines ADR-030 and ADR-039.
- Reopen if: tests on simple and large models show a mode that looks wrong.

## ADR-041: ADR-028 supersedes ADR-008 (2026-11-23)
- Status: Accepted
- Context: ADR-028 dropped reading the .f3d, but did not name ADR-008 ("generate from f3d when possible"), so the two read as a conflict (drift watcher, 2026-11-23).
- Decision: Views and data come from the STEP plus sr-export's `<name>.bom.json` (ADR-028, ADR-029). The app never reads the .f3d. This entry only records the lineage; no new choice.
- Rejected: editing ADR-008 or ADR-028 in place (DECISIONS is append-only).
- Supersedes: ADR-008.
- Reopen if: ADR-028 is reopened.

## ADR-042: Render-test inputs, Fusion host, tangent "partial", anti-aliasing (2026-11-23, Daniel)
- Status: Accepted
- Context: Render tests (ADR-040) needed models, a Fusion host, and the meaning of "partial" tangent edges (H35-H38, H40).
- Decision: Test models come from Daniel's Spark hub: filament cabinet, RTR, AOI, PDM, fuse boxes and the fuel hanger (H35c). Tests and exports run in local desktop Fusion, the way engineers will use the app (H36a). "Partial" tangent edges hide the start and end segments of each tangent edge, as SOLIDWORKS "Hide ends" does (H37, from SOLIDWORKS help "Tangent Edge Display Overview"). FAST DRAFT is row 5: mesh creases plus silhouettes (H38a). The render tests include the anti-aliasing fixes: mesh made finer as the view scale grows, true arcs and circles, and supersampled PNG and thumbnail output (H40a).
- Rejected: Fusion Compute for tests (the workstation root guide prefers it in general; this repo's use is desktop); a thin phantom-font style as "partial" (that is SOLIDWORKS "Use font").
- Supersedes: refines ADR-040 (what "partial" draws).
- Reopen if: engineers use the app with no window, or "Hide ends" looks wrong in tests.

## ADR-043: Keep the data card draft as reference (2026-11-23, Daniel, H39)
- Status: Accepted
- Context: ADR-032 moved the data card to the PDM, so this repo no longer uses `docs/DATA-CARD.md`. Where it should go was open (H39).
- Decision: Keep `docs/DATA-CARD.md` in this repo with its superseded banner, as reference for any repo that wants it. Nothing in this repo writes or reads it.
- Rejected: deleting it; moving it to another repo now.
- Supersedes: none; refines ADR-032.
- Reopen if: another repo takes ownership of the data card.

## ADR-044: Line endings: LF everywhere, Windows scripts CRLF (2026-11-23, Daniel, H42)
- Status: Accepted
- Context: Windows `core.autocrlf` rewrote copied gate scripts, so `.github/registry-check.py` on disk no longer matched the workstation copy. Daniel answered this in another session as "answer T" (relayed in PR #31 by Grok Bot); it is numbered H42 here on the one question counter.
- Decision: A root `.gitattributes` (PR #31) sets `* text=auto eol=lf`, CRLF for `.bat/.cmd/.ps1/.psd1/.vbs`, and marks images, PDF, zip, xlsx and CAD files (STEP, STL, 3MF, f3d) binary. Same base rules as workstation and handbuilt-cad. `.gitattributes` is the enforcer.
- Rejected: per-clone `core.autocrlf` settings.
- Supersedes: none.
- Reopen if: a tool needs CRLF files.

## ADR-045: Render mode chosen from results, per model (2026-11-24, Daniel, H46)
- Status: Accepted. No fixed default yet.
- Context: The render tests (docs/RESEARCH.md, "Render tests on real models", PR #34) recommended HQ by default, UHQ in the background, and asked whether DRAFT stays its own mode (H46).
- Decision: No default mode is set yet. Every render test shows Daniel the results of all four modes side by side (compare sheet, mode picker, times, sizes), and he picks the mode for that model. All four modes stay until the results settle a default.
- Rejected: fixing HQ as the default now; dropping DRAFT now.
- Supersedes: none; refines ADR-040.
- Reopen if: Daniel's picks over the H43 models point to one default.

## ADR-046: More render-test models (2026-11-24, Daniel, H43)
- Status: Accepted
- Context: ADR-042 named the test models; the RTR file was not found, and the AOI and PDM picks were open (H43).
- Decision: Test all three AOI designs ("Assembly Fixture, AOI XY", "AOI v3", "AOI Assembly, Prototype Fixture, DRG") and all three PDM designs (custom-pdm-enclosure-v2c-F1, CPDM-ENC-109, CPDM-HAR-203). For RTR, look for big models in Daniel's OneDrive models folder and his Fusion hubs. Hub folder "RTR v2" (SparkleBots / Dan) is empty, so RTR is replaced by the biggest STEP models found there until Daniel names the RTR file.
- Rejected: one pick per family.
- Supersedes: none; refines ADR-042 (test models).
- Reopen if: Daniel names the RTR file.

## ADR-047: Test models from the OneDrive models folder only, for now (2026-11-24, Daniel, H48)
- Status: Accepted
- Context: Hub files are being moved and work is still happening on the PDM; a live open of the PDM assembly froze Fusion (BACKLOG 2026-11-24).
- Decision: Until Daniel says otherwise, render tests use STEP files from his OneDrive models folder only. No hub files and no opens in Fusion.
- Rejected: opening hub designs by file id; using STEP files from other folders.
- Supersedes: the hub-file parts of ADR-042 and ADR-046 (models), for now.
- Reopen if: Daniel says the hub and PDM work have settled.

## ADR-048: Two render modes, named by what they give (2026-11-24, Daniel, H52)
- Status: Accepted. Which two, and their names, open (H55).
- Context: The four mode names (UHQ, HQ, DRAFT, FAST DRAFT) do not match the results (docs/RESEARCH.md, "All render tests compared").
- Decision: Keep two modes: one very fast that may give up line quality, one with accurate, high-quality lines that may take longer. Pick them from the compiled results and rename them by what they actually give.
- Rejected: four modes; the current names.
- Supersedes: the four-mode list of ADR-040 and the per-model pick of ADR-045.
- Reopen if: none.
## ADR-049: Every method must make working views before the pick (2026-11-24, Daniel, H56)
- Status: Accepted
- Context: UHQ and FAST lost outlines on the CC-500 pendant; HQ bowed the AOI yoke slots. Daniel will not pick two modes (ADR-048, H55) until every method has had the chance to make working views.
- Decision: Each method is fixed until it makes complete, correct views on every test model, then all models are re-run with the fixed code. A method that cannot be made to work is out of the running. Fixes so far (`research/render-tests/render_modes.py`): HQ arc fitting checks the arc between points (no bowed lines); UHQ adds the polygonal outlines that exact tracing drops on free-form faces; FAST uses a per-edge depth tolerance (face depth span, capped at 20 px) so silhouettes are not hidden. UHQ timeout raised to 600 s per view for the re-run.
- Rejected: picking from results where a method failed for a fixable reason.
- Supersedes: none; works with ADR-048.
- Reopen if: none.
## ADR-050: PDM shell STEP skipped for now (2026-11-24, Daniel, H53)
- Status: Accepted
- Context: The PDM STEP in the models folder (`custom-pdm-enclosure-revF`) holds only the assembly tree; its parts are external references to `Parts/*.stp`, which render_modes.py does not read.
- Decision: Skip the PDM model in the render tests for now (H53b). The renderer is not changed to load external references.
- Rejected: teaching the renderer to load external references now (H53a).
- Supersedes: the PDM part of ADR-046.
- Reopen if: the PDM work settles (ADR-047) or the drawing app must read STEP files with external references.
## ADR-051: A drawing that takes over 2 minutes fails (2026-11-24, Daniel)
- Status: Accepted
- Context: UHQ timed out or ran 6-20 minutes on large assemblies (docs/RESEARCH.md, "All render tests compared"). Daniel: any size model must become an engineering drawing; size is never the reason, the method or the code is.
- Decision: Any render mode that takes longer than 2 minutes from the STEP file to finished views on any test model is an automatic fail. Speed work uses the whole PC (all CPU cores, the GPU), not one core. The XQ method (exact B-rep edges, visibility from a GPU depth buffer, `research/render-tests/xq_render.py`) is the first method that meets this on all 16 models.
- Rejected: per-view timeouts that leave views empty; judging speed with the STEP read left out.
- Supersedes: the 600 s per-view UHQ timeout of ADR-049, as a pass mark.
- Reopen if: none.
## ADR-052: Two render modes: Exact Lines and Quick Look (2026-11-25, Daniel, B1a)
- Status: Accepted
- Context: The fix2 and XQ runs (docs/RESEARCH.md) left one method that is both the fastest and the most exact: XQ, exact
  B-rep edges with visibility from the GPU depth buffer. UHQ and FAST fail ADR-051; HQ and DRAFT are mesh-based.
- Decision: Two modes, named by what they give. **Exact Lines**: XQ at full depth-buffer resolution with true arcs; used
  for released files. **Quick Look**: XQ at a 2048 px depth buffer with no arc fitting; for previews while editing.
  Code: `research/render-tests/xq_render.py --mode exact|quick`.
- Rejected: XQ with HQ as the fast mode (B1b); XQ only (B1c).
- Supersedes: the four modes of ADR-040 and the per-model pick of ADR-045; settles ADR-048.
- Reopen if: a model shows a defect Exact Lines cannot fix, or Quick Look is not much faster on large models.
## ADR-053: STEP read cached by file hash (2026-11-25, Daniel, B5a)
- Status: Accepted
- Context: The STEP read was 48 % of the worst XQ time (CC-000: 42 s of 88 s), on one core; open-source OCCT has no
  parallel STEP reader.
- Decision: A STEP is read once. Its shape is kept as `<cache>/<sha256 of the file>.brep` (cache folder: `SRDP_CACHE`,
  else `~/.cache/sr-drawing-pack`). The file content, not its name or date, decides a cache hit. The file is written
  under a temporary name and renamed, so a stopped run never leaves a half-written cache.
- Rejected: parallel STEP read in worker processes (B5b, kept as a later option); no cache (B5c).
- Supersedes: none.
- Reopen if: the cache folder grows too large (no clean-up yet; BACKLOG).
## ADR-054: Fusion Desktop app lock is back (2026-11-25, Daniel, B3a)
- Status: Accepted
- Context: AGENTS.md said the Fusion lock was retired (2026-11-22), but the workstation session hook now adds a
  `fusion-desktop` app lock, separate from the harness.design lock.
- Decision: Use the workstation `fusion-desktop` lock before a script run in the Fusion app or driving the app
  (acquire, check in every 10 min, release). Fusion Compute and Fusion Data MCP need no lock.
- Rejected: keeping the lock retired in this repo (B3b).
- Supersedes: the 2026-11-22 "Fusion lock retired" line in AGENTS.md.
- Reopen if: the workstation drops the lock.
## ADR-055: Act on the one real choice (2026-11-25, Daniel)
- Status: Accepted
- Context: Daniel: no reason to ask everything.
- Decision: When only one choice really moves the project forward, the agent takes its recommendation and reports it.
  Questions are asked only for real trade-offs, listed by ID only (never numbered).
- Rejected: asking every decision.
- Supersedes: none; works with the question-ID rule in AGENTS.md.
- Reopen if: none.

## ADR-056: Drawings and maker files (2026-11-25, Daniel)
- Status: Accepted
- Context: Spark Robotic cuts DXF on CNC laser, plasma and router tables, runs .nc files (CNC machine G-code) and prints from sliced G-code files. ADR-032 left DXF open.
- Decision:
  - Every item we make gets a drawing by default, for reference and to check the made part against.
  - "Maker files" are any files used to make or fabricate a part: DXF, .nc, G-code, sliced files, and so on.
  - Not every item needs every file: the user picks the outputs for each item when generating.
  - DXF is an output (closes ADR-032's open DXF point).
  - Only drawings are editable. Maker files made by other software (sliced G-code, most .nc) are brought into sparkCAD paired with their item and controlled the same as drawings, because they make parts. An ID or fingerprint binds each maker file to its item and rev, so they always match and always change together.
  - A drawing can be reopened and edited after export; the user never has to remake it from scratch (Daniel's main concern; how is open, C7).
- Rejected: maker files kept outside the vault; every item forced to carry every file type.
- Supersedes: the open DXF point of ADR-032.
- Reopen if: none.

## ADR-057: Assemblies link their parts in the vault (2026-11-25, Daniel)
- Status: Accepted
- Context: Daniel wants to find every part inside an assembly, and every assembly a part is used in.
- Decision:
  - The hand-over JSON carries the assembly's BOM items, so every custom part and sub-assembly we make is linked to each assembly that uses it.
  - Every custom part and sub-assembly in an assembly, and the custom parts inside those sub-assemblies, has its own drawing and paired maker files in the vault.
  - The vault answers two queries: "contains" (what is in this assembly) and "where used" (which assemblies use this part).
- Rejected: links kept only on the drawing's parts list.
- Supersedes: none; works with ADR-029 (BOM from sr-export's bom.json) and ADR-032 (the vault keeps the record).
- Reopen if: none.

## ADR-058: Part numbers from the vault counter, written into Fusion first (2026-11-25, Daniel, D1a, C8a)
- Status: Accepted
- Context: The title block and BOM must carry the vault's number from the start; Fusion is where the BOM is made.
- Decision: A Fusion add-in button "Get part numbers" takes the next numbers, by kind, from the vault counter for every custom component with a blank part number and writes them into the Fusion components. The drawing title block and the BOM read them from Fusion; nobody types a number on a drawing. The vault accepts only numbers it issued. Vault unreachable: the drawing stays DRAFT with no number and cannot be uploaded. Format: PRT / SUB / ASY / CBL / WIR-####, plus MFR (purchased) and CUS (customer).
- Rejected: engineers type numbers by a rule; the vault numbers at upload.
- Supersedes: refines ADR-019 (the vault's single counter still hands out every number).
- Reopen if: none.

## ADR-059: Editable drawing file (2026-11-25, Daniel, C7a)
- Status: Accepted
- Context: A PDF cannot be edited; drawings must be reopened and edited later (ADR-056).
- Decision: The editor saves its own drawing file (sheets, view positions, dimensions, notes, parts-list placement, the STEP fingerprint). PDF and DXF are exports of it. It is stored in the vault beside the PDF. Editing later: check out, open in the editor with Fusion on the model, edit, check in.
- Rejected: regenerating from scratch.
- Supersedes: none.
- Reopen if: none.

## ADR-060: Maker-file pairing and binding (2026-11-25, Daniel, C9a, C4a)
- Status: Accepted
- Context: Maker files must always match their item's rev (ADR-056).
- Decision: Outside maker files are paired in the drawing tool's "Save to vault" window or later in the vault, same rules. Every drawing and maker file records the sha256 fingerprint of the STEP it was made from; G-code and .nc get a stamp comment line (number, rev, fingerprint), DXF a text note.
- Rejected: fingerprint in the JSON only; vault-only pairing.
- Supersedes: none.
- Reopen if: a machine controller rejects the stamp line.

## ADR-061: Child revs and the release check (2026-11-25, Daniel, C5a, C6a)
- Status: Accepted
- Context: Assemblies must not release with stale or missing child documents (ADR-057).
- Decision: A new child rev flags each parent "review needed", never an automatic parent rev. An assembly cannot release until every custom child, all the way down, has its drawing and needed maker files with matching fingerprints.
- Rejected: parent follows the latest child; warn only.
- Supersedes: none.
- Reopen if: none.

## ADR-062: Build order (2026-11-25, Daniel, D2a, D3b, B9a, C3a, C2a)
- Status: Accepted
- Context: Many open steps; Daniel's usage is near its limit.
- Decision: Write and approve the full steps 1-9 lifecycle section in SPEC before building more features (D2a). One work stream at a time until Daniel's usage resets, then parallel agents (D3b, for now). First features: more sheets, first angle, detail views, wireframe (B9a). First BOM style on the sheet: indented (C3a). Exploded views: exploded positions added to the data file the Fusion export writes (C2a; an sr-export change).
- Rejected: features before the lifecycle plan; parallel streams now.
- Supersedes: none.
- Reopen if: usage resets (switch to parallel streams).

## ADR-063: The vault plan lives in the EasyPDM fork (2026-11-25, Daniel, D4a)
- Status: Accepted
- Context: The sparkCAD agent must build this plan, not fall back to something else.
- Decision: The vault side is written into the EasyPDM fork (research655/EasyPDM) on the workstation-core template: its docs/DECISIONS.md V-001 to V-009 and docs/SPEC.md milestones V0 to V8 restate ADR-056 to ADR-061, with a rule that the SPEC is binding. Agents work there on branches and PRs. Open there: D5 rev format, D6 approval rule, D7 purchased parts.
- Rejected: only Daniel's sparkCAD sessions touch it.
- Supersedes: none.
- Reopen if: none.

## ADR-064: Vault answers D5a, D6a, D7 (2026-11-25, Daniel)
- Status: Accepted
- Context: Questions recorded in the EasyPDM fork (its V-010 to V-012).
- Decision: Vault revs follow ADR-011 (D5a). Anyone who did not make the change approves; admins and app owners may approve their own (D6a). Only controlled files go in the vault: bought (off-the-shelf) and customer parts get no vault item and no drawing and appear only as BOM rows with their maker or customer number; live Fusion models stay in the Fusion hub as "living" or "prototype" files (D7). So the drawing's BOM lists bought parts by maker number, and "Get part numbers" (ADR-058) numbers only made items (PRT, SUB, ASY, CBL, WIR).
- Rejected: plain A, B, C revs; admin-only approval; vault items for bought or customer parts.
- Supersedes: the MFR and CUS kinds in ADR-058.
- Reopen if: none. Open: D8, STEP files in the vault (EasyPDM fork SPEC).

## ADR-065: One repo; sr-drawing-pdf joined here; Claude owns the engine (2026-11-27, Daniel, E1a)
- Status: Accepted
- Context: Rules lived in sr-drawing-pack and code in sr-drawing-pdf, and the split kept drifting. Daniel handed both repos to Claude.
- Decision: sr-drawing-pdf is merged into this repo with its full git history (main at 780ea75): `SRDrawingPDF/`, `tests/`, `tools/`, `dev/`, `pull.cmd` at the root; its docs under `docs/engine/`; its agent rules folded into AGENTS.md and `.claude/rules/drawing-engine.md`. sr-drawing-pdf is archived, read-only. Claude owns engine and editor work (was Grok). The work-PC Fusion add-in junction is re-pointed at this repo's `SRDrawingPDF/` folder.
- Rejected: moving these docs into sr-drawing-pdf (E1b); keeping two repos (E1c).
- Supersedes: the "who owns what" split in ADR-020 (sr-drawing-pdf as evidence-only spike).
- Reopen if: none.

## ADR-066: 3D model viewer for vault items (2026-11-27, Daniel, E2a)
- Status: Accepted
- Context: Daniel wants an interactive 3D viewer for vault models: orbit like Fusion, explode, hide and show parts, no editing.
- Decision: This repo exports a GLB (compact web 3D file) beside the STEP, keeping the part tree and names, plus one stand-alone viewer page (three.js: orbit, explode, hide/show, part tree). The vault (EasyPDM fork, ADR-063) embeds the page; it does not build its own.
- Rejected: building it inside the EasyPDM fork (E2b); parking it (E2c).
- Supersedes: none.
- Reopen if: GLB export of the AOI assembly is too slow or too large to open in a browser.

## ADR-067: Viewer selects, explodes and drags parts (2026-11-27, Daniel)
- Status: Accepted
- Context: Daniel wants users to select one or many components and explode or drag just those.
- Decision: The model viewer (ADR-066) has multi-select (Ctrl/Shift click, tree rows, a Multi-select toggle for touch), an explode slider that acts on the selection (or the whole model when nothing is selected), and a Move mode that drags the selection in the screen plane. Moves and explodes are for looking only: they never change the GLB or STEP, and Reset positions undoes them.
- Rejected: none.
- Supersedes: "view-only, explode the whole model" in ADR-066.
- Reopen if: users need saved exploded views (would need a file format for them).
