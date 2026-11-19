# External references (read-only)

Nothing in these repos is modified. Code may be copied into this repo and changed here, subject to
each license. Local clones of the third-party repos live in `research/_local/refs/` (git-ignored).

## Daniel's own repos (read-only sources)

| Repo | Use here |
|---|---|
| https://github.com/living-relation/handbuilt-cad | Drawing engine (`drawing/`), rev letters, drawing rules, render tools. The output style to match. |
| https://github.com/living-relation/sr-bom | Fusion BOM add-in: component counting, part number / description / material fields |
| https://github.com/living-relation/sr-drawing-pdf | Fusion add-in: four-view PDF |
| https://github.com/living-relation/sr-export | Fusion add-in: STEP, F3D, STL, 3MF, IGES, SAT, DXF export |
| https://github.com/living-relation/sr-fastener | Fusion add-in: fasteners with BOM fields |
| https://github.com/living-relation/sr-cadlib | Agent helper library for Fusion scripting |
| https://github.com/living-relation/autodesk-fusion-mcp | Fusion MCP add-in (fork of frankhommers). Test harness. |
| https://github.com/living-relation/workstation | Agent skills: state-init, coordinator-kit, session-start, safe-repo-preflight |

## Third-party repos

Dates are last commit as checked on 2026-11-19.

| Repo | License | Last commit | Why it matters |
|---|---|---|---|
| https://github.com/nvsdef/fusion360-mcp | MIT | 2026-09-18 | `create_drawing` via Fusion's preview drawing API. Tested. |
| https://github.com/nofuturekid/fusion-export | GPL-3.0 | 2026-11-01 | Batch export incl. drawing PDF/DWG. Tested. GPL: do not copy code unless this repo goes GPL. |
| https://github.com/thecuriousrohan/Exporter-X | MIT stated in README, no license file | 2025-11-30 | Batch 2D export DXF/DWG/PDF. Tested. |
| https://github.com/matteoimmorlano/fusion360-drawing-generator | MIT | 2026-10-31 | Add-in + external engine pattern; auto dims, balloons. macOS only. Not tested. |
| https://github.com/jokeri2222/Fusion-Drawing-Generator | Custom, not OSI | 2026-10-17 | Tolerances, callouts. Reference only. Not tested. |
| https://github.com/Danecca-Ltd/GhostForge | None stated | 2026-10-30 | AutoCAD-command injection into Fusion drawings. Tested: edits did not persist. No license: do not copy. |
| https://github.com/Antslabeu/Fusion-DWG-Exporter | MIT | 2026-06-11 | README only. Code is in the repo below. |
| https://github.com/Antslabeu/extract_fusion_dwg | None stated | 2026-06-11 | Pulls DWG out of cached .f2d files. Tested. No license: do not copy. |
| https://github.com/schneik80/PowerTools-Document-Tools | GPL-3.0 | 2026-06-23 | Drawing numbering. Not tested. |
| https://github.com/schneik80/PowerTools-Exports | not checked | not checked | Cloned, not reviewed. |
| https://github.com/schiffer-soft/F360toSVG | GPL-3.0 | 2026-08-21 | SVG export of model views. Not tested. |
| https://github.com/bivyworks/fusion-anodize-spec-sheet | MIT | 2026-10-08 | Views + balloons to PDF. Not tested. |
| https://github.com/krdarrah/Fusion_Drawing_Generator | MIT | 2026-09-14 | PCB fab drawings from .brd. Not tested. |
| https://github.com/LibreDWG/libredwg | GPL-3.0 | n/a | Used as a tool to verify DWG output. |

Fusion drawing API docs (preview): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/drawing_DrawingManager.htm
