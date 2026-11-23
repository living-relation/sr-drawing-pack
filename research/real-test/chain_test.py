"""Whole-chain test on a real Fusion design: STEP + data file -> BOM check, views, a draft sheet, thumbnails.

Usage:  python chain_test.py <assembly.step> <data.json> <out_dir> [max_faces_per_part]
        With a face limit, top-level rows with more faces than that are left out of the views (they stay in the BOM
        and the thumbnails). Exact hidden-line removal on a whole real assembly can take many minutes per view.
Needs:  HBCAD_ROOT (handbuilt-cad clone, read-only) and that clone's Python; F3D_EXE (f3d.exe) for thumbnails.
The STEP and data file come from Fusion (research/fusion-data/export_real_design.py). Nothing here is committed
output: results go to <out_dir>, progress to <out_dir>/chain_test.log. Each stage is timed and may fail alone.
"""
import os, sys, json, time, re, subprocess, traceback
import numpy as np

HB = os.environ.get("HBCAD_ROOT")
if not HB: raise SystemExit("Set HBCAD_ROOT to your handbuilt-cad clone")
sys.path.insert(0, os.path.join(HB, "drawing"))
import dwg
from build123d import Compound, import_step, export_step

STEP, DATA, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; os.makedirs(OUT, exist_ok=True)
F3D = os.environ.get("F3D_EXE", ""); LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 0
res = {}; LOG = open(os.path.join(OUT, "chain_test.log"), "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n"); LOG.flush()
def save(): json.dump(res, open(os.path.join(OUT, "chain_test.json"), "w"), indent=1)
def stage(name):
    def deco(fn):
        t = time.perf_counter()
        try: res[name] = fn() or {}
        except Exception as e: res[name] = dict(error=f"{type(e).__name__}: {e}"); log(traceback.format_exc())
        res[name]["seconds"] = round(time.perf_counter() - t, 2); log(name, json.dumps(res[name])[:900]); save()
    return deco
mangle = lambda n: re.sub(r"[^A-Za-z0-9\-]", "_", n)

data = json.load(open(DATA, encoding="utf-8")); shape = None

@stage("import_step")
def _():
    global shape
    shape = import_step(STEP)
    return dict(mb=round(os.path.getsize(STEP) / 1e6, 1), solids=len(shape.solids()), faces=len(shape.faces()), top_children=len(shape.children))

@stage("bom_step_vs_fusion")
def _():
    """Top-level rows: quantity per name in the STEP tree against the Fusion data file."""
    step = {}
    for c in shape.children: step[c.label] = step.get(c.label, 0) + 1
    fus = {mangle(r["name"]): r["qty"] for r in data["bom"]}
    missing = sorted(set(fus) - set(step)); extra = sorted(set(step) - set(fus))
    wrong = {k: (step[k], fus[k]) for k in fus if k in step and step[k] != fus[k]}
    def rows(rs): return sum(1 + rows(r["children"]) for r in rs)
    blank = lambda k: sum(1 for r in data["bom"] if not r[k])
    return dict(fusion_top_rows=len(fus), step_top_names=len(step), fusion_all_rows=rows(data["bom"]), fusion_top_qty=sum(fus.values()), step_top_qty=sum(step.values()),
                missing_in_step=missing[:8], extra_in_step=extra[:8], qty_mismatch=dict(list(wrong.items())[:8]),
                top_rows_without=dict(part_number=blank("part_number"), description=blank("description"), material=blank("material")),
                linked_top_rows=sum(1 for r in data["bom"] if r.get("linked")), threads_in_data=len(data.get("threads", [])), holes_in_data=len(data.get("holes", [])))

polys = {}
@stage("views")
def _():
    out = {}; target = shape
    if LIMIT:
        faces = {}
        for k in shape.children:
            if k.label not in faces: faces[k.label] = len(k.faces())
        keep = [k for k in shape.children if faces[k.label] <= LIMIT]; target = Compound([s for k in keep for s in k.solids()])
        out["limit"] = dict(max_faces=LIMIT, parts_drawn=len(keep), parts_left_out=len(shape.children) - len(keep), left_out=sorted(k for k, n in faces.items() if n > LIMIT))
    for name in ("front", "top", "right", "iso"):
        cam, up = dwg.VIEWDIR[name]; c, r, u = dwg.basis(cam, up); t = time.perf_counter()
        v, h = target.project_to_viewport(tuple(c * 5000), tuple(u), (0, 0, 0)); t1 = time.perf_counter() - t
        vis = [p for p in (dwg.edge_pts(e, 0.05) for e in v) if len(p) > 1]; polys[name] = (vis, [], (c, r, u))
        out[name] = dict(hlr_s=round(t1, 2), sample_s=round(time.perf_counter() - t - t1, 2), visible=len(vis), hidden_not_drawn=len(h), points=int(sum(len(p) for p in vis)))
    return out

@stage("draft_sheet")
def _():
    """Engine frame + three flat views + pictorial, visible edges only, no view labels (ADR-026). No dimensions."""
    V = {n: dwg.View(None, n, 1.0, polys=polys[n], name=n) for n in polys if n in ("front", "top", "right", "iso")}
    gx, gy = 30, 26; smax = min((270 - gx) / (V["front"].w + V["right"].w), (170 - gy) / (V["front"].h + V["top"].h)); s = dwg.pick_scale(smax)
    for v in V.values(): v.scale = s; v.w = (v.umax - v.umin) * s; v.h = (v.vmax - v.vmin) * s
    f, t, r, iso = V["front"], V["top"], V["right"], V["iso"]
    x0, y0 = 30, 80; f.place(x0 + f.w / 2, y0 + f.h / 2); t.place(f.cx, y0 + f.h + gy + t.h / 2); r.place(x0 + f.w + gx + r.w / 2, f.cy)
    k = min(1.0, 105 / iso.w, 95 / iso.h); iso.scale = s * k; iso.w *= k; iso.h *= k; iso.place(360, 190)
    sh = dwg.Sheet()
    for v in V.values(): v.draw(sh)
    root = data["root"]
    dwg.frame(sh, dict(title=root["description"].split("(")[0].strip().upper()[:60], pn=root["part_number"], rev="-", material="SEE BOM", scale=dwg.scale_str(s),
                       source=os.path.basename(STEP), drawn="-", project="CHAIN TEST - NOT A RELEASED DRAWING"), 1, 1)
    t0 = time.perf_counter(); pdf = os.path.join(OUT, "real_asm_draft.pdf"); dwg.render([sh], pdf, None, os.path.join(OUT, "real_asm_draft"))
    return dict(scale=dwg.scale_str(s), items=len(sh.items), render_s=round(time.perf_counter() - t0, 2), pdf_mb=round(os.path.getsize(pdf) / 1e6, 2))

@stage("thumbnails")
def _():
    if not os.path.isfile(F3D): return dict(skipped="F3D_EXE not set")
    td = os.path.join(OUT, "thumbs"); os.makedirs(td, exist_ok=True); seen = {}; times = []; fails = []; coloured = 0
    for c in shape.children:
        if c.label in seen: continue
        seen[c.label] = 1; png = os.path.join(td, c.label + ".png"); part = os.path.join(td, "_part.step"); t = time.perf_counter()
        try:
            inv = c.location.inverse(); export_step(Compound([s.moved(inv) for s in c.solids()]), part)
            r = subprocess.run([F3D, part, "--output", png, "--resolution=420,420", "--no-background", "--grid=false", "--axis=false", "--filename=false",
                                "--edges", "--up=+Z", "--camera-direction=-1,1.55,-1.15", "--camera-orthographic"], capture_output=True, encoding="utf-8", errors="replace", timeout=120)
            if r.returncode or not os.path.isfile(png): raise RuntimeError(r.stderr[-120:])
            import matplotlib.pyplot as plt
            a = plt.imread(png)[..., :3]; coloured += int((a.max(axis=2) - a.min(axis=2)).max() > 0.08)
        except Exception as e: fails.append(f"{c.label}: {type(e).__name__}: {str(e)[:80]}")
        times.append(round(time.perf_counter() - t, 2))
    if os.path.isfile(part): os.remove(part)
    return dict(rows=len(seen), failed=len(fails), failures=fails[:5], coloured=coloured, min_s=min(times), max_s=max(times), median_s=float(np.median(times)), total_s=round(sum(times), 1))

log("DONE"); save()
