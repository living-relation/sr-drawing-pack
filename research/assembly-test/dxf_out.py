"""DXF writer with real CIRCLE / ARC entities. Copied from research/spike-b/styled_sheet.py
(the engine's own DXF writer, dwg.render, only writes polylines). Import after HBCAD_ROOT/drawing is on sys.path.
"""
import math
import numpy as np
import dwg
import ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Circle

VIEWS = []

class Sheet(dwg.Sheet):                       # remember which polylines are really circles
    def __init__(s): super().__init__(); s.circs = {}
    def circle(s, c, r, sty="thin", n=72):
        super().circle(c, r, sty, n); s.circs[id(s.items[-1])] = (np.asarray(c, float), float(r))

class View(dwg.View):                         # remember the solid behind each view
    def __init__(s, shape, *a, **k): super().__init__(shape, *a, **k); s._shape = shape; VIEWS.append(s)

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
    circles = [cr for v in VIEWS if not dwg.is_pictorial(v.view) and (v.cx or v.cy) for cr in exact_circles(v)]
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
    """The engine's DXF writer (dwg.render), copied, with real CIRCLE / ARC entities for circular edges.
    Sheets sit side by side in model space, one sheet width plus 50 mm apart."""
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
                for a_, b_ in (("⌀", "%%c"), ("°", "%%d"), ("±", "%%p"), ("↧", " DP "), ("⌴", "CBORE "), ("⌵", "CSK ")): t = t.replace(a_, b_)
                al = f"{ {'center': 'MIDDLE', 'bottom': 'BOTTOM', 'top': 'TOP'}.get(va, 'MIDDLE') }_{ha.upper()}"
                lines = t.split("\n"); n = len(lines)
                for j, ln in enumerate(lines):
                    dy = (n - 1 - j) * hh * 1.6 if va == "bottom" else (-j * hh * 1.6 if va == "top" else ((n - 1) / 2 - j) * hh * 1.6)
                    e = msp.add_text(ln, dxfattribs={"height": hh * 0.85, "layer": "TEXT", "rotation": rot})
                    e.set_placement((x + ox - math.sin(math.radians(rot)) * dy, y + math.cos(math.radians(rot)) * dy), align=AL[al])
    doc.saveas(path)

def entity_counts(path):
    ent = {}
    for e in ezdxf.readfile(path).modelspace(): ent[(e.dxftype(), e.dxf.layer)] = ent.get((e.dxftype(), e.dxf.layer), 0) + 1
    return {f"{t} on {l}": n for (t, l), n in sorted(ent.items())}
