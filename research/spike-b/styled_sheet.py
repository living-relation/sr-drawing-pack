"""Spike B, styled sheet: the test plate drawn to the house drawing rules with the handbuilt-cad engine.

Usage:  python styled_sheet.py <out_dir>
Needs:  HBCAD_ROOT = path to a handbuilt-cad clone (read-only, never edited), run with that clone's Python,
        and the requester's drawing initials set (DRAWING_INITIALS or ~/.drawing-initials).
The engine's part.make_part does the views, section, dimensions, hole callouts, centre marks, title block,
rev table and notes. This script only adds what the engine has no spec field for: a BOM on a part sheet,
a group view label, detail dimensions below a feature, and a DXF with real CIRCLE / ARC entities.
Nothing in the engine is changed on disk; its functions are wrapped at run time.
"""
import os, sys, math, json
import numpy as np

HB = os.environ.get("HBCAD_ROOT")
if not HB: raise SystemExit("Set HBCAD_ROOT to your handbuilt-cad clone")
sys.path.insert(0, os.path.join(HB, "drawing"))
import dwg, part, asm, revs, settings
import ezdxf
from build123d import Box, Cylinder, Pos, export_step
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Circle

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
PN, STEP = "SRDP-SPIKE-B", os.path.join(OUT, "spike_b_plate.step")
PDF, DXF = os.path.join(OUT, "spike_b_sheet.pdf"), os.path.join(OUT, "spike_b_sheet.dxf")
BOM_COLW = (9, 9, 30, 34, 30)
BOM = [dict(item=1, qty=1, pn=PN, desc="TEST PLATE", mat="6061-T6 AL (TEST)", shapes=True)]

def plate():
    p = Box(80, 50, 10)
    for x in (-30, 30):
        for y in (-15, 15):
            p -= Pos(x, y, 0) * Cylinder(3, 10)
    return p - Pos(0, 0, -3) * Box(20, 20, 4)

export_step(plate(), STEP)
revlog = os.path.join(OUT, "spike_b_plate." + revs.REVLOG_NAME)
if not os.path.exists(revlog): revs.add_release(revlog, "A", "Initial", settings.requester_initials(), title=PN)

# ---- run-time wrappers (the engine files are not touched) ----
class Sheet(dwg.Sheet):                       # remember which polylines are really circles
    def __init__(s): super().__init__(); s.circs = {}
    def circle(s, c, r, sty="thin", n=72):
        super().circle(c, r, sty, n); s.circs[id(s.items[-1])] = (np.asarray(c, float), float(r))

VIEWS = []
class View(dwg.View):                         # remember the solid behind each view
    def __init__(s, shape, *a, **k): super().__init__(shape, *a, **k); s._shape = shape; VIEWS.append(s)

RL = {}
def revlog_rect(rows, *a, **k):               # reserve room for the BOM under the rev table
    x0, y0, x1, y1 = dwg.revlog_rect(rows, *a, **k); RL["rect"] = (x0, y0, x1, y1)
    return (min(x0, x1 - sum(BOM_COLW)), y0 - 16, x1, y1)

_detail_body = part._detail_body
def detail_body(sh, pv, dt, px, py):          # dimension the detail: width below the opening, depth inside the pocket
    _detail_body(sh, pv, dt, px, py)
    if not isinstance(sh, Sheet) or (px == 0 and py == 0): return
    cu, sc = pv.uv(np.asarray(dt["center"], float)), dt["scale"]
    T = lambda p: np.array((px + (pv.uv(p)[0] - cu[0]) * sc, py + (pv.uv(p)[1] - cu[1]) * sc))
    a, b, top = T((-10, 0, 0)), T((10, 0, 0)), T((10, 0, 4))
    dwg.dim_lin(sh, a, b, "h", a[1] - 6, "□20")
    dwg.dim_lin(sh, b, top, "v", b[0] - 12, "4")

def exact_circles(v):
    """Page centre and radius of every true circle seen face-on in view v, straight from the B-rep."""
    out = {}
    for e in v._shape.edges():
        a = BRepAdaptor_Curve(e.wrapped)
        if a.GetType() != GeomAbs_Circle: continue
        ci = a.Circle(); d = ci.Axis().Direction()
        if abs(abs(np.array((d.X(), d.Y(), d.Z())) @ v.c) - 1) > 1e-6: continue
        l = ci.Location(); c = v.P(np.array((l.X(), l.Y(), l.Z()))); r = ci.Radius() * v.scale
        out[(round(c[0], 4), round(c[1], 4), round(r, 4))] = (c, r)
    return list(out.values())

def classify(sh):
    """id(item) -> ('CIRCLE', c, r) | ('ARC', c, r, a0, a1) | None (already covered by a CIRCLE)."""
    m = {k: ("CIRCLE", c, r) for k, (c, r) in sh.circs.items()}
    circles = [cr for v in VIEWS if not dwg.is_pictorial(v.view) for cr in exact_circles(v)]
    for c, r in circles:
        hits = []
        for it in sh.items:
            if it[0] != "pl" or it[2] != "vis" or len(it[1]) < 3 or id(it) in m: continue
            p = it[1]
            if np.abs(np.hypot(p[:, 0] - c[0], p[:, 1] - c[1]) - r).max() > 2e-3: continue
            ang = np.unwrap(np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0]))
            hits.append((it, ang[0], ang[-1]))
        if not hits: continue
        if sum(abs(a1 - a0) for _, a0, a1 in hits) >= math.radians(359.5):
            m[id(hits[0][0])] = ("CIRCLE", c, r)
            for it, _, _ in hits[1:]: m[id(it)] = None
        else:
            for it, a0, a1 in hits: m[id(it)] = ("ARC", c, r, math.degrees(min(a0, a1)), math.degrees(max(a0, a1)))
    return m

def write_dxf(sheets, path):
    """The engine's DXF writer (dwg.render), copied, with real CIRCLE / ARC entities for circular edges."""
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for sty, (nm, lt, col) in dwg.DXF_LAYER.items():
        if nm not in doc.layers: doc.layers.add(nm, color=col, linetype=lt if lt in doc.linetypes else "CONTINUOUS")
    doc.layers.add("TEXT", color=7); doc.layers.add("HATCH", color=8)
    msp = doc.modelspace(); AL = ezdxf.enums.TextEntityAlignment
    for i, sh in enumerate(sheets):
        ox = i * (dwg.PW + 50); m = classify(sh) if isinstance(sh, Sheet) else {}
        for it in sh.items:
            k = it[0]
            if k == "pl":
                _, p, sty, cl = it; lay = {"layer": dwg.DXF_LAYER[sty][0]}; g = m.get(id(it), "PL")
                if g is None: continue
                if g == "PL": msp.add_lwpolyline([(x + ox, y) for x, y in p], close=cl, dxfattribs=lay)
                elif g[0] == "CIRCLE": msp.add_circle((g[1][0] + ox, g[1][1]), g[2], dxfattribs=lay)
                else: msp.add_arc((g[1][0] + ox, g[1][1]), g[2], g[3], g[4], dxfattribs=lay)
            elif k == "tri": msp.add_solid([(x + ox, y) for x, y in it[1]], dxfattribs={"layer": "DIM"})
            elif k == "ha":
                h = msp.add_hatch(dxfattribs={"layer": "HATCH"}); h.set_pattern_fill("ANSI31", scale=0.6)
                for l in it[1]: h.paths.add_polyline_path([(x + ox, y) for x, y in l], is_closed=True)
            elif k == "tx":
                _, x, y, t, hh, ha, va, rot, b, bg, _l = it
                for a_, b_ in (("⌀", "%%c"), ("°", "%%d"), ("±", "%%p"), ("↧", " DP "), ("□", "SQ ")): t = t.replace(a_, b_)
                al = f"{ {'center': 'MIDDLE', 'bottom': 'BOTTOM', 'top': 'TOP'}.get(va, 'MIDDLE') }_{ha.upper()}"
                lines = t.split("\n"); n = len(lines)
                for j, ln in enumerate(lines):
                    dy = (n - 1 - j) * hh * 1.6 if va == "bottom" else (-j * hh * 1.6 if va == "top" else ((n - 1) / 2 - j) * hh * 1.6)
                    e = msp.add_text(ln, dxfattribs={"height": hh * 0.85, "layer": "TEXT", "rotation": rot})
                    e.set_placement((x + ox - math.sin(math.radians(rot)) * dy, y + math.cos(math.radians(rot)) * dy), align=AL[al])
    doc.saveas(path)

_render = dwg.render
def render(sheets, pdf, dxf=None, png=None):  # add the BOM, balloon and group label, then PDF / PNG and our DXF
    sh = sheets[0]; V = sh.anch["view"]; x0, y0, x1, y1 = RL["rect"]
    asm.bom_table(sh, BOM, x1, y0 - 2, colw=BOM_COLW)
    iso = V["iso"]; bx0, by0, bx1, by1 = iso.bbox()
    asm.balloon(sh, np.array((bx0 + 8, by1 + 1)), 1, iso.P((-12, 0, 10)))        # item 1, tip on the top face
    fv, rv, tv = V["front"], V["right"], V["top"]
    for i, it in enumerate(sh.items):                                           # section label clear of the detail circle and its letter
        if it[0] == "tx" and it[3].startswith("SECTION "): sh.items[i] = it[:2] + (fv.bbox()[1] - 22,) + it[3:]
    sh.txt(rv.cx, rv.bbox()[1] - 22, f"TOP / RIGHT VIEWS  SCALE {dwg.scale_str(rv.scale)}", h=3.5, bold=True, va="top")
    _render(sheets, pdf, None, png); write_dxf(sheets, DXF)
    stats["hidden_lines"] = sum(1 for s in sheets for it in s.items if it[0] == "pl" and it[2] == "hid")
    stats["centre_line_items"] = sum(1 for s in sheets for it in s.items if it[0] == "pl" and it[2] == "ctr")

stats = {}
part.Sheet, part.View, part.revlog_rect, part._detail_body, part.render = Sheet, View, revlog_rect, detail_body, render

spec = dict(
    file=STEP, pn=PN, title="SPIKE B TEST PLATE", material="6061-T6 AL (TEST)", process="machined",
    project="SR DRAWING PACK - M1 SPIKE B", source=os.path.basename(STEP), revlog=revlog, auto_align=False,
    section=dict(slot="front", origin=(0, 0, 5), label="A-A"),
    details=[dict(parent="front", label="B", center=(0, 0, 3), radius=12, scale=3)],
    overall=False,                            # overall sizes placed by hand so nothing runs through the detail circle
    dims=[("lin", "top", (-40, -25, 0), (40, -25, 0), "h", "below"), ("lin", "front", (-40, 0, 0), (-40, 0, 10), "v", "left"),
          ("lin", "right", (0, -25, 0), (0, 25, 0), "h", "below")],
    notes=["TEST PLATE FOR THE SR DRAWING PACK SPIKE B. NOT FOR MANUFACTURE.",
           "GENERATED FROM THE STEP NAMED IN SOURCE. CHANGE THE MODEL AND REGENERATE; DO NOT EDIT THIS SHEET BY HAND."])
scale = part.make_part(spec, PDF, None, os.path.join(OUT, "spike_b_sheet"))

ent = {}
for e in ezdxf.readfile(DXF).modelspace(): ent[(e.dxftype(), e.dxf.layer)] = ent.get((e.dxftype(), e.dxf.layer), 0) + 1
stats.update(scale=dwg.scale_str(scale), checks_ok=spec["_checks"]["ok"], hole_flags=spec.get("_hole_flags"),
             dxf={f"{t} on {l}": n for (t, l), n in sorted(ent.items())})
print(json.dumps(stats, indent=1))
