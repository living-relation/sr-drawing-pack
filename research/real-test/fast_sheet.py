"""Fast-view draft package of a real assembly (ADR-030): views by polygonal hidden-line removal, BOM from sr-export's
bom.json (ADR-029), F3D thumbnails per top-level BOM row.

Usage:  python fast_sheet.py <assembly.step> <out_dir>
Needs:  HBCAD_ROOT (handbuilt-cad clone, read-only) and that clone's Python; <assembly>.bom.json from sr-export next to
        the STEP; F3D_EXE for thumbnails (skipped when unset). Draft only: no dimensions, balloons or rev table yet.
Sheet 1: front, top, right and trimetric views. Sheet 2: the top-level BOM. Results and timings in fast_sheet.json.
"""
import os, sys, json, time, subprocess
import numpy as np
sys.path.insert(0, os.path.join(os.environ["HBCAD_ROOT"], "drawing"))
import dwg, asm
from build123d import Compound, import_step, export_step
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve

STEP, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
BOM = json.load(open(os.path.splitext(STEP)[0] + ".bom.json", encoding="utf-8"))
F3D = os.environ.get("F3D_EXE", ""); res = {}; JS = os.path.join(OUT, "fast_sheet.json")
def save(): json.dump(res, open(JS, "w"), indent=1)
def tic(): return time.perf_counter()

t = tic(); shp = import_step(STEP); res["import_s"] = round(tic() - t, 1)
t = tic(); BRepMesh_IncrementalMesh(shp.wrapped, 0.2, False, 0.5, True); res["mesh_s"] = round(tic() - t, 1); save()

def fast_view(name):
    """Visible sharp edges and outlines; smooth (tangent) edges only in the pictorial view (DRAWING-RULES 16a)."""
    cam, up = dwg.VIEWDIR[name]; c, r, u = dwg.basis(cam, up)
    algo = HLRBRep_PolyAlgo(); algo.Load(shp.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*c), gp_Dir(*r)))); algo.Update()
    h = HLRBRep_PolyHLRToShape(); h.Update(algo)
    sets = [("vis", h.VCompound()), ("vis", h.OutLineVCompound())] + ([("tan", h.Rg1LineVCompound())] if name == "iso" else [])
    out = {"vis": [], "tan": []}
    for sty, comp in sets:
        if comp is None or comp.IsNull(): continue
        ex = TopExp_Explorer(comp, TopAbs_EDGE)
        while ex.More():
            a = BRepAdaptor_Curve(TopoDS.Edge(ex.Current()))
            p0, p1 = a.Value(a.FirstParameter()), a.Value(a.LastParameter())
            out[sty].append(np.array([[p0.X(), p0.Y()], [p1.X(), p1.Y()]])); ex.Next()
    return out["vis"], out["tan"], (c, r, u)

V = {}; res["views"] = {}
for name in ("front", "top", "right", "iso"):
    t = tic(); vis, tan, basis = fast_view(name)
    V[name] = dwg.View(None, name, 1.0, polys=(vis, [], basis, tan), name=name)
    res["views"][name] = dict(seconds=round(tic() - t, 1), lines=len(vis), tangent=len(tan)); save()

# ---- sheet 1: views, third-angle, no view labels (ADR-026) ----
gx, gy = 28, 24
smax = min((262 - gx) / (V["front"].w + V["right"].w), (172 - gy) / (V["front"].h + V["top"].h)); s = dwg.pick_scale(smax)
for v in V.values(): v.scale = s; v.w = (v.umax - v.umin) * s; v.h = (v.vmax - v.vmin) * s
f, tp, rt, iso = V["front"], V["top"], V["right"], V["iso"]
x0, y0 = 24, 86
f.place(x0 + f.w / 2, y0 + f.h / 2); tp.place(f.cx, y0 + f.h + gy + tp.h / 2); rt.place(x0 + f.w + gx + rt.w / 2, f.cy)
k = dwg.pick_scale(s * min(1.0, 118 / iso.w, 120 / iso.h)) / s                   # standard scales only
iso.scale = s * k; iso.w *= k; iso.h *= k; iso.place(352, 168)
sh1 = dwg.Sheet()
for v in V.values(): v.draw(sh1)
if abs(iso.scale - s) > 1e-9: sh1.txt(iso.cx, iso.cy - iso.h / 2 - 4, f"SCALE {dwg.scale_str(iso.scale)}", h=3.0, va="top")
src = BOM["source"]
ROOT_PN = os.environ.get("ROOT_PN", "")          # bom.json lists the parts, not the top assembly's own part number
info = dict(title=src["design_name"].split(" v")[0].upper()[:60], pn=ROOT_PN or "-",
            rev="-", material="SEE BOM", scale=dwg.scale_str(s), source=os.path.basename(STEP), drawn="-",
            project="FAST-VIEW TEST - NOT A RELEASED DRAWING")
dwg.frame(sh1, info, 1, 2)

# ---- sheet 2: top-level BOM from sr-export (Fusion's material shown as is) ----
rows = []
for cpt in BOM["components"]:
    top = [o for o in cpt["occurrences"] if "+" not in o]
    if top: rows.append(dict(item=len(rows) + 1, qty=len(top), pn=cpt["part_number"], desc=cpt["description"].split("|")[0].strip().upper()[:70],
                             mat=(cpt["material"] or "").upper(), shapes=True, shown=True))
sh2 = dwg.Sheet(); asm.bom_table(sh2, rows, dwg.PW - 12, dwg.PH - 14, colw=(10, 9, 52, 120, 42), h=1.9); dwg.frame(sh2, info, 2, 2)
res["bom_rows"] = len(rows); res["bom_qty"] = sum(r["qty"] for r in rows)
t = tic(); dwg.render([sh1, sh2], os.path.join(OUT, "fast_sheet.pdf"), os.path.join(OUT, "fast_sheet.dxf"), os.path.join(OUT, "fast_sheet"))
res["render_s"] = round(tic() - t, 1); res["scale"] = dwg.scale_str(s); save()

# ---- thumbnails: one per top-level row, F3D ----
if os.path.isfile(F3D):
    td = os.path.join(OUT, "thumbs"); os.makedirs(td, exist_ok=True); seen = set(); times = []; fails = []
    for ch in shp.children:
        if ch.label in seen: continue
        seen.add(ch.label); png = os.path.join(td, ch.label + ".png"); part = os.path.join(td, "_part.step"); t = tic()
        try:
            inv = ch.location.inverse(); export_step(Compound([x.moved(inv) for x in ch.solids()]), part)
            r = subprocess.run([F3D, part, "--output", png, "--resolution=300,300", "--no-background", "--grid=false", "--axis=false", "--filename=false",
                                "--edges", "--up=+Z", "--camera-direction=-1,1.55,-1.15", "--camera-orthographic"],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=180)
            if r.returncode or not os.path.isfile(png): raise RuntimeError(r.stderr[-120:])
        except Exception as e: fails.append(f"{ch.label}: {type(e).__name__}: {str(e)[:80]}")
        times.append(tic() - t)
    res["thumbnails"] = dict(rows=len(seen), failed=len(fails), failures=fails[:5], median_s=round(float(np.median(times)), 2),
                             max_s=round(max(times), 1), total_s=round(sum(times), 1))
save(); print(json.dumps(res, indent=1))
