"""Drawing package for the test assembly SRDP-T-100, made by the handbuilt-cad engine from the STEP.

Usage:  python make_package.py <out_dir>           (the folder build_assembly.py wrote the STEP into)
Needs:  HBCAD_ROOT = path to a handbuilt-cad clone (read-only, never edited), run with that clone's Python,
        and the requester's drawing initials set (DRAWING_INITIALS or ~/.drawing-initials).
Writes: SRDP-T-100.pdf, _sh1.png, _sh2.png, .dxf, .checks.json (engine), .package_check.json (this script),
        and REVLOG.md beside the STEP if there is none yet.

asm.make_assembly does sheet 1: views, trimetric and exploded views, balloons, BOM, rev table, notes,
overall reference dimensions, title block. Everything the engine has no spec field for is added here by
wrapping engine functions at run time (nothing in the engine is changed on disk). Each wrapper is marked GAP.
"""
import json, math, os, sys
import numpy as np

HB = os.environ.get("HBCAD_ROOT")
if not HB: raise SystemExit("Set HBCAD_ROOT to your handbuilt-cad clone")
sys.path.insert(0, os.path.join(HB, "drawing"))
import dwg, part, asm, revs, settings
from build123d import Compound, Keep, Plane, GeomType
from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.affinity import affine_transform
from shapely.ops import unary_union
from shapely.strtree import STRtree
import model_data as D, check_step_tree as T, dxf_out

OUT = sys.argv[1]
STEP = os.path.join(OUT, D.ASM_PN + ".step")
PDF, DXF, PNG = (os.path.join(OUT, D.ASM_PN + e) for e in (".pdf", ".dxf", ""))
YS = D.M5_XY[1][1]                       # section plane y = 25: through one screw of every kind
SEC_SCALE, DET_SCALE = 2.0, 3.0
HATCH = {D.BASE_PN: 45, D.COVER_PN: 135, D.HANDLE_PN: 45, D.STOP_PN: 135}     # neighbours hatched opposite ways

# ---- BOM rows from the STEP tree; description and material from the spec table (ADR-002) ----
root, _ = T.read_tree(STEP)
def bom_rows(node, prefix=""):
    seen = {}
    for k in node["children"]: seen.setdefault(k["name"], []).append(k)
    out = []
    for i, (name, ks) in enumerate(seen.items(), 1):
        no, meta, sub = f"{prefix}{i}", D.PARTS[name], bool(ks[0]["children"])
        # a sub-assembly row carries all its solids and is ballooned as one item; its children are ballooned
        # only on the build-order step that makes the sub-assembly (hide_in_asm keeps them off sheet 1)
        out.append(dict(item=no, qty=len(ks), pn=name, desc=meta["desc"], mat=meta["mat"], kind=meta["kind"],
                        shapes=[l["shape"] for k in ks for l in T.leaves(k)], primary=not prefix and meta["kind"] != "fastener",
                        hide_in_asm=bool(prefix)))
        if sub:
            assert len(ks) == 1, "a sub-assembly used more than once needs its child quantities multiplied"
            out += bom_rows(ks[0], no + ".")
    return out
ITEMS = bom_rows(root)
NO = {it["pn"]: it["item"] for it in ITEMS}
LEAF = [it for it in ITEMS if it["kind"] != "asm"]

revlog = os.path.join(OUT, revs.REVLOG_NAME)          # beside the STEP; the engine finds it by itself
if not os.path.exists(revlog): revs.add_release(revlog, "A", "Initial", settings.requester_initials(), title=D.ASM_PN)

# ---- GAP 1: DXF with real circles. The engine's Sheet / View are swapped for ones that remember circles. ----
Sheet, View = dxf_out.Sheet, dxf_out.View
asm.Sheet, asm.View = Sheet, View

# ---- section helpers (GAP 2: make_assembly has no section, detail, hole callout or centre mark) ----
C_, R_, U_ = dwg.basis(*dwg.VIEWDIR["front"])
uv = lambda p: np.array((np.asarray(p, float) @ R_, np.asarray(p, float) @ U_))

def cut(items):
    """Cut every solid at the section plane, keep the far side. Returns (solids, {pn: cut-face polygon in view uv})."""
    pl = Plane(origin=(0, YS, 0), z_dir=tuple(C_)); sols, polys = [], {}
    for it in items:
        for s in it["shapes"]:
            bb = s.bounding_box()
            if bb.max.Y <= YS + 1e-6: continue                     # in front of the plane: cut away
            if bb.min.Y >= YS - 1e-6: sols.append(s); continue     # behind the plane: seen whole
            half = s.split(pl, keep=Keep.BOTTOM); dwg._require_capped(half)   # capped sections only (DRAWING-RULES 23)
            sols += list(half.solids())
            for f in half.faces():
                if f.geom_type != GeomType.PLANE: continue
                n, c = np.array(tuple(f.normal_at())), np.array(tuple(f.center()))
                if abs(abs(n @ C_) - 1) > 1e-4 or abs((c - np.array((0, YS, 0))) @ C_) > 1e-3: continue
                vs, tris = f.tessellate(0.02, 0.2); p = [uv(tuple(v)) for v in vs]
                g = unary_union([Polygon([p[a], p[b], p[c]]).buffer(1e-4) for a, b, c in tris]).buffer(-1e-4)
                polys[it["pn"]] = polys[it["pn"]].union(g) if it["pn"] in polys else g
    return sols, polys

def hatch_lines(sh, poly, ang, sp=2.2):
    """45 degree section lining as thin lines clipped to poly (page mm). The engine's hatch has one direction only."""
    if poly.is_empty: return
    x0, y0, x1, y1 = poly.bounds; a = math.radians(ang); d = np.array((math.cos(a), math.sin(a))); n = np.array((-d[1], d[0]))
    t = np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) @ n; L = math.hypot(x1 - x0, y1 - y0) + 1
    c0 = d * (np.array(((x0 + x1) / 2, (y0 + y1) / 2)) @ d)
    for k in range(math.floor(t.min() / sp), math.ceil(t.max() / sp) + 1):
        g = LineString([n * k * sp + c0 - d * L, n * k * sp + c0 + d * L]).intersection(poly)
        for seg in ([g] if g.geom_type == "LineString" else getattr(g, "geoms", [])):
            if seg.geom_type == "LineString" and seg.length > 0.3: sh.pl(list(seg.coords), "thin")

def callout_texts():
    """Hole callout text per made part, from the engine's own part.hole_callouts (tap drill + thread, THRU, real depths).
    Which diameters are tapped is spec data: a STEP does not say. Returns {pn: [(text with count, [hole centres])]}."""
    out, flags = {}, []
    for it in LEAF:
        if it["kind"] != "made": continue
        sp = dict(threads={d: part.TAP[d] for d in D.TAP_DRILL.values()} if it["pn"] in (D.BASE_PN, D.HANDLE_PN) else {},
                  thread_depth={D.TAP_DRILL["M4"]: D.BLIND_THREAD_DEPTH} if it["pn"] == D.BASE_PN else {})
        groups, _, fl = part.hole_callouts(it["shapes"][0], "machined", sp); flags += fl
        for (ax, txt), inst in groups.items():
            ls = txt.split("\n"); n = len(inst)
            if ls[0].endswith("-6H THRU"):         # GAP 3: the engine leaves the tap drill off a through tapped hole
                ls.insert(1, f"⌀{dwg.fmt(2 * inst[0]['r'], 2)} THRU")
            txt = "\n".join(ls)
            out.setdefault(it["pn"], []).append(("\n".join([f"{n}X {ls[0]}"] + ls[1:]) if n > 1 else txt, [i["c"] for i in inst]))
    return out, flags

def text_for(calls, pn, x):
    for txt, cs in calls[pn]:
        if any(abs(c[0] - x) < 0.01 and abs(c[1] - YS) < 0.01 for c in cs): return txt
    raise KeyError((pn, x))

xh, x5, xs = D.HANDLE_XY[0][0], D.M5_XY[2][0], D.STOP_XY[0][0]
zb, zc0, zc1, zh0, zs1 = D.BASE[5], D.COVER[4], D.COVER[5], D.HANDLE[4], D.STOP[5]
rt4, rt5, rc4, rc5, rcb = D.TAP_DRILL["M4"] / 2, D.TAP_DRILL["M5"] / 2, D.CLEARANCE["M4"] / 2, D.CLEARANCE["M5"] / 2, D.CBORE_D / 2
# detail: label, centre, radius, screw item left out, [(part, hole x, leader tip, text to the right?)]
DETAILS = [
    dict(label="B", center=(xh, YS, 18.0), radius=10.0, omit=NO[D.M4X12], calls=[
        (D.HANDLE_PN, xh, (xh + rt4, YS, zh0 + 5.0), True),
        (D.COVER_PN, xh, (xh - rcb, YS, zc0 + D.CBORE_DEPTH / 2), False)]),
    dict(label="C", center=(x5, YS, 10.0), radius=11.0, omit=NO[D.M5X16], calls=[
        (D.COVER_PN, x5, (x5 - rc5, YS, (zc0 + zc1) / 2 + 1), False),
        (D.BASE_PN, x5, (x5 + rt5, YS, zb / 2 - 1), True)]),
    dict(label="D", center=(xs, YS, 14.0), radius=13.5, omit=NO[D.M4X16], calls=[
        (D.STOP_PN, xs, (xs + rcb, YS, zs1 - D.CBORE_DEPTH / 2), True),
        (D.BASE_PN, xs, (xs - rt4, YS, zb - D.BLIND_DRILL_DEPTH / 2), False)]),
]
AXES = [(D.M5_XY[1][0], -3, 28), (xh, 9, 39), (x5, -3, 28), (xs, -1, 29)]     # hole axes on the plane: x, z from, z to
STATS = dict(callouts=[], centre_marks=0)

def decorate_sheet1(sh):
    """Centre marks on every hole seen face-on, and the cutting-plane line A-A on the top view."""
    V = sh.anch["view"]
    for n in ("front", "top", "right"):
        for pc, rp, kind in dwg.circle_marks(V[n]._shape, V[n]):
            dwg.centermark(sh, pc, rp, arc=(kind == "arc")); STATS["centre_marks"] += 1
    tv = V["top"]; x0, _, x1, _ = tv.bbox(); y = tv.P((0, YS, 0))[1]; up = np.array((0.0, 1.0))   # section is seen looking +Y
    a, b = np.array((x0 - 7, y)), np.array((x1 + 7, y))
    sh.line(a, b, "cut")
    for p in (a, b):
        sh.line(p, p + up * 8, "thin"); sh.arrow(p + up * 8, p, L=3.5, W=1.4); sh.txt(*(p + up * 12.5), "A", h=4.5, bold=True)

def detail_sheet(info, no, n):
    sh = Sheet(); calls, flags = callout_texts(); STATS["hole_flags"] = flags
    made = [it for it in LEAF if it["kind"] == "made"]; screws = [it for it in LEAF if it["kind"] == "fastener"]
    sols, polys = cut(LEAF); sols_n, polys_n = cut(made)
    v = View(Compound(sols), "front", SEC_SCALE, name="section").place(170, 222)
    vn = dwg.View(Compound(sols_n), "front", SEC_SCALE, name="section, screws left out")     # parent of the details, not drawn itself
    vn.umin, vn.umax, vn.vmin, vn.vmax = v.umin, v.umax, v.vmin, v.vmax; vn.place(v.cx, v.cy)
    pg = lambda g: affine_transform(g, [v.scale, 0, 0, v.scale, v.cx - (v.umin + v.umax) / 2 * v.scale, v.cy - (v.vmin + v.vmax) / 2 * v.scale])
    # SECTION A-A: screws are cut but not hatched; each made part is hatched, neighbours opposite ways
    screw_area = unary_union([polys[it["pn"]] for it in screws if it["pn"] in polys]).buffer(0.01)
    for it in made: hatch_lines(sh, pg(polys[it["pn"]].difference(screw_area)), HATCH[it["pn"]])
    v.draw(sh); sh.rects.append(v.bbox())
    for x, z0, z1 in AXES: sh.line(v.P((x, YS, z0)), v.P((x, YS, z1)), "ctr")
    P = lambda x, z: v.P((x, YS, z)); bx0 = v.bbox()[0]; bx1 = v.bbox()[2]
    dwg.dim_lin(sh, P(D.BASE[0], D.BASE[4]), P(D.BASE[0], D.BASE[5]), "v", bx0 - 9, dwg.fmt(D.BASE[5] - D.BASE[4], 2))
    dwg.dim_lin(sh, P(D.COVER[0], zc0), P(D.COVER[0], zc1), "v", bx0 - 19, dwg.fmt(zc1 - zc0, 2))
    dwg.dim_lin(sh, P(D.HANDLE[0], zh0), P(D.HANDLE[0], D.HANDLE[5]), "v", P(D.HANDLE[0], 0)[0] - 16, dwg.fmt(D.HANDLE[5] - zh0, 2))
    dwg.dim_lin(sh, P(D.STOP[1], D.STOP[4]), P(D.STOP[1], zs1), "v", bx1 + 9, dwg.fmt(zs1 - D.STOP[4], 2))
    sh.txt(v.cx, v.bbox()[1] - 14, f"SECTION A-A  SCALE {dwg.scale_str(SEC_SCALE)}", h=3.5, bold=True, va="top")
    # details B, C, D: cut from the same section with the screws left out, so the hole shapes can be read
    pending = []
    for dt, (px, py) in zip(DETAILS, ((78, 116), (208, 116), (338, 131))):
        c = np.asarray(dt["center"], float); R = dt["radius"]; cu = vn.uv(c); cpg = v.P(c); Rp = R * v.scale
        Td = lambda q, cu=cu, px=px, py=py: np.array((px + (uv(q)[0] - cu[0]) * DET_SCALE, py + (uv(q)[1] - cu[1]) * DET_SCALE))
        sh.circle(cpg, Rp, "detail")
        G = part._obstacles(sh); tree = STRtree(G); best = None          # letter beside the parent circle, on the clearest spot
        for ang in np.linspace(0, 2 * np.pi, 24, endpoint=False):
            q = cpg + np.array((np.cos(ang), np.sin(ang))) * (Rp + 3.4); bx = sbox(q[0] - 2.4, q[1] - 2.9, q[0] + 2.4, q[1] + 2.9)
            sc = sum(G[k].intersects(bx) for k in tree.query(bx)) * 100 - np.sin(ang)
            if best is None or sc < best[0]: best = (sc, q)
        sh.txt(*best[1], dt["label"], h=4.5, bold=True)
        circ = Point(cu).buffer(R, 64)
        for it in made:                                                  # hatch first, linework on top
            g = polys_n[it["pn"]].intersection(circ)
            hatch_lines(sh, affine_transform(g, [DET_SCALE, 0, 0, DET_SCALE, px - cu[0] * DET_SCALE, py - cu[1] * DET_SCALE]), HATCH[it["pn"]])
        part._detail_body(sh, vn, dict(label=dt["label"], center=dt["center"], radius=R, scale=DET_SCALE), px, py)   # engine: clipped linework, circle, label
        Rd = R * DET_SCALE
        sh.txt(px, py - Rd - 15.5, f"ITEM {dt['omit']} (SCREW) NOT SHOWN", h=2.6, va="top")
        for x, z0, z1 in AXES:                                           # hole centre lines inside the detail
            g = LineString([Td((x, YS, z0)), Td((x, YS, z1))]).intersection(Point(px, py).buffer(Rd - 1.5))
            if g.geom_type == "LineString" and g.length > 1: sh.pl(list(g.coords), "ctr")
        sh.rects.append((px - Rd, py - Rd - 20, px + Rd, py + Rd))
        for pn, x, tip, right in dt["calls"]:
            t = text_for(calls, pn, x); pending.append((vn, Td(tip), t, right, None))
            STATS["callouts"].append(dict(detail=dt["label"], item=NO[pn], part=pn, text=t))
    occ = part.Occ(); occ.rects = sh.rects
    part.place_leaders(sh, occ, pending)                                 # engine: leader text on a free spot
    dwg.frame(sh, dict(info, scale=dwg.scale_str(SEC_SCALE)), no, n)
    return sh

# ---- GAP 2 hook: one more sheet, added where the engine adds its build-order sheets ----
_count, _add, _render = asm.stage_sheet_count, asm.add_stage_sheets, asm.render
def add_stage_sheets(sheets, items, groups, ctx, info, nsheets, log, **k):
    _add(sheets, items, groups, ctx, info, nsheets, log, **k)
    decorate_sheet1(sheets[0]); sheets.append(detail_sheet(info, len(sheets) + 1, nsheets))
def render(sheets, pdf, dxf=None, png=None):
    _render(sheets, pdf, None, png); dxf_out.write_dxf(sheets, DXF)
    STATS["sheets"] = len(sheets)
    STATS["hidden_line_items"] = sum(1 for s in sheets for it in s.items if it[0] == "pl" and it[2] == "hid")
    STATS["balloons"] = sorted({str(k) for s in sheets for k in s.anch["balloon"]})
    STATS["balloons_sheet1"] = sorted(str(k) for k in sheets[0].anch["balloon"])
    STATS["scale"] = dwg.scale_str(sheets[0].anch["view"]["front"].scale)
asm.stage_sheet_count = lambda groups: _count(groups) + 1
asm.add_stage_sheets, asm.render = add_stage_sheets, render

up = lambda *pairs: [(NO[pn], (0, 0, dz)) for pn, dz in pairs]
spec = dict(
    file=STEP, pn=D.ASM_PN, title="TEST ASSEMBLY: BASE, COVER AND STOP", project="SR DRAWING PACK - ASSEMBLY TEST",
    source=os.path.basename(STEP), items=ITEMS, bom_cols=(10, 9, 40, 50, 36),
    # build order (engine stage sheets): each step is an exploded trimetric with balloons on the parts that go on
    stage_sheets=[[
        dict(no=1, title=f"BUILD SUB-ASSEMBLY {D.SUB_PN} (ITEM {NO[D.SUB_PN]}), SCREWS FROM BELOW", base=[NO[D.COVER_PN]],
             move=up((D.HANDLE_PN, 28), (D.M4X12, -30))),
        dict(no=2, title="FIT THE SUB-ASSEMBLY TO THE BASE PLATE", base=[NO[D.BASE_PN]], move=up((D.SUB_PN, 30), (D.M5X16, 62))),
        dict(no=3, title="FIT THE STOP BLOCK", base=[NO[D.BASE_PN], NO[D.SUB_PN], NO[D.M5X16]], balloon_base=[],
             move=up((D.STOP_PN, 24), (D.M4X16, 54))),
    ]],
    notes=["TEST ASSEMBLY FOR THE SR DRAWING PACK. NOT FOR MANUFACTURE. PART NUMBERS SRDP-T-1XX AND MATERIALS MARKED (TEST) ARE MADE UP.",
           "DIMENSIONS IN PARENTHESES ARE REFERENCE.",
           "BUILD ORDER: SHEET 2. HOLE AND THREAD CALLOUTS: SECTION A-A AND DETAILS B, C, D ON SHEET 3.",
           "GENERATED FROM THE STEP NAMED IN SOURCE (build123d). CHANGE THE MODEL AND REGENERATE; DO NOT EDIT THIS SHEET BY HAND."])
checks = asm.make_assembly(spec, PDF, PNG)

# ---- self-check by count, not by eye ----
def flat(tree, out):
    for name, qty, kids in tree: out.append((name, qty)); flat(kids, out)
    return out
bom = [(it["pn"], it["qty"]) for it in ITEMS]
res = dict(
    scale=STATS["scale"], sheets=STATS["sheets"], engine_checks_ok=checks["ok"], not_ballooned=checks.get("not_ballooned"),
    bom_rows=len(bom), bom_matches_expected_tree=bom == flat(D.EXPECTED_TREE[2], []), bom_matches_step_tree=bom == flat(T.bom(root), []),
    bom_leaf_quantity=sum(it["qty"] for it in LEAF), step_leaf_solids=len(T.leaves(root)),
    balloons=STATS["balloons"], balloons_sheet1=STATS["balloons_sheet1"],
    balloons_match_bom_rows=STATS["balloons"] == sorted(it["item"] for it in ITEMS),
    hidden_line_items=STATS["hidden_line_items"], centre_marks_sheet1=STATS["centre_marks"],
    callouts=STATS["callouts"], hole_flags=STATS.get("hole_flags"), dxf=dxf_out.entity_counts(DXF))
res["ok"] = bool(res["engine_checks_ok"] and res["bom_matches_expected_tree"] and res["bom_matches_step_tree"]
                 and res["bom_leaf_quantity"] == res["step_leaf_solids"] and res["balloons_match_bom_rows"]
                 and res["hidden_line_items"] == 0 and not res["hole_flags"]
                 and any(k.startswith("CIRCLE on VISIBLE") for k in res["dxf"]))
json.dump(res, open(PNG + ".package_check.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1))
sys.exit(0 if res["ok"] else 1)
