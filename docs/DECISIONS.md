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
