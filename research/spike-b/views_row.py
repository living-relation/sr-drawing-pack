"""Spike B, views row: STEP -> hidden-line views with the handbuilt-cad engine, out of process.

Usage:  python views_row.py <out_dir> [extra.step ...]
Needs:  HBCAD_ROOT = path to a handbuilt-cad clone (read-only, never edited), run with that clone's Python.
Makes the spike A test plate (80 x 50 x 10 mm, four 6 mm through holes, 20 x 20 x 4 mm pocket in the
bottom face), writes it to STEP, reads it back, and draws base + projected + iso + section + detail
views with visible and hidden edges kept apart. Extra STEP files are only timed.
"""
import os, sys, json, time
import numpy as np

HB = os.environ.get("HBCAD_ROOT")
if not HB: raise SystemExit("Set HBCAD_ROOT to your handbuilt-cad clone")
sys.path.insert(0, os.path.join(HB, "drawing"))
import dwg                                   # the engine, imported read-only
from build123d import Box, Cylinder, Pos, export_step, import_step
from shapely.geometry import LineString, Point

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
res = {"views": {}, "timing_s": {}, "extra": {}}

def plate():
    p = Box(80, 50, 10)
    for x in (-30, 30):
        for y in (-15, 15):
            p -= Pos(x, y, 0) * Cylinder(3, 10)
    return p - Pos(0, 0, -3) * Box(20, 20, 4)

def raw(shape, view):
    """OCCT hidden-line removal. Returns (visible, hidden) polylines in view coordinates, and seconds."""
    cam, up = dwg.VIEWDIR[view]; c, r, u = dwg.basis(cam, up)
    t = time.perf_counter()
    v, h = shape.project_to_viewport(tuple(c * 5000), tuple(u), (0, 0, 0))
    return [dwg.edge_pts(e) for e in v], [dwg.edge_pts(e) for e in h], time.perf_counter() - t

step = os.path.join(OUT, "spike_b_plate.step")
export_step(plate(), step)
t = time.perf_counter(); solid = import_step(step).solids()[0]; res["timing_s"]["step_import"] = round(time.perf_counter() - t, 3)

sh = dwg.Sheet()
try: dwg.frame(sh, dict(title="SPIKE B VIEWS ROW", pn="SRDP-SPIKE-B", rev="", material="", drawn=""), 1, 1); res["frame"] = "engine title block"
except Exception as e: res["frame"] = f"skipped: {type(e).__name__}: {e}"

# third-angle layout: top above front, right beside front. Children share one coordinate with the parent.
POS = {"front": (110, 150), "top": (110, 215), "right": (190, 150), "iso": (290, 205)}
V = {}
for name, (cx, cy) in POS.items():
    vis, hid, dt = raw(solid, name)
    v = dwg.View(solid, name, 1.0, name=name).place(cx, cy)     # engine view: visible edges, soft edges filtered
    for p in hid: sh.pl([v.uv2pg(q) for q in p], "hid")         # the engine drops these; here they are drawn dashed
    v.draw(sh, label=name.upper()); V[name] = v
    res["views"][name] = dict(visible=len(vis), hidden=len(hid), total=len(vis) + len(hid), engine_visible=len(v.vis))
    res["timing_s"][f"hlr_{name}"] = round(dt, 3)

# section: engine call, cut plane through the two front holes
t = time.perf_counter()
sec = dwg.section_view(solid, "front", (0, -15, 0), 1.0, "section").place(110, 85)
sec.draw(sh, label="SECTION A-A"); res["timing_s"]["section"] = round(time.perf_counter() - t, 3)
res["views"]["section"] = dict(visible=len(sec.vis), hatch_regions=len(sec.hatches))
a, b = V["top"].P((-46, -15, 0)), V["top"].P((46, -15, 0)); sh.line(a, b, "cut")

# detail: clip the top view to a circle around one hole, redraw at 3:1
top = V["top"]; c_uv = top.uv((30, 15, 0)); R, K, ctr = 8.0, 3.0, np.array((290.0, 110.0))
clip = Point(c_uv).buffer(R, 64); n = 0
vis, hid, _ = raw(solid, "top")
for lines, sty in ((vis, "vis"), (hid, "hid")):
    for p in lines:
        g = LineString(p).intersection(clip)
        for part in getattr(g, "geoms", [g]):
            if part.is_empty or part.geom_type != "LineString": continue
            sh.pl([ctr + (np.array(q) - c_uv) * K for q in part.coords], sty); n += 1
sh.circle(ctr, R * K, "detail"); sh.circle(top.uv2pg(c_uv), R, "detail")
sh.txt(ctr[0], ctr[1] - R * K - 6, "DETAIL B\nSCALE 3:1", h=3.5, va="top", bold=True)
res["views"]["detail"] = dict(pieces=n)

pdf, dxf = os.path.join(OUT, "spike_b_views.pdf"), os.path.join(OUT, "spike_b_views.dxf")
t = time.perf_counter(); dwg.render([sh], pdf, dxf, os.path.join(OUT, "spike_b_views")); res["timing_s"]["render_pdf_dxf_png"] = round(time.perf_counter() - t, 3)

import ezdxf
layers = {}
doc = ezdxf.readfile(dxf)
for e in doc.modelspace(): layers[e.dxf.layer] = layers.get(e.dxf.layer, 0) + 1
res["dxf"] = dict(insunits=doc.header.get("$INSUNITS"), layers=layers)

for path in sys.argv[2:]:      # timing only, on real files
    t = time.perf_counter(); shp = import_step(path); t_imp = time.perf_counter() - t
    row = dict(solids=len(shp.solids()), faces=len(shp.faces()), import_s=round(t_imp, 2))
    for name in ("front", "iso"):
        vis, hid, dt = raw(shp, name); row[name] = dict(visible=len(vis), hidden=len(hid), hlr_s=round(dt, 2))
    res["extra"][os.path.basename(path)] = row

# Fusion's own counts for the same plate (spike A, View.viewCurves, visible + hidden mixed)
res["fusion_viewcurves_total"] = dict(top=12, front=11, iso=40)
json.dump(res, open(os.path.join(OUT, "spike_b_views.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
