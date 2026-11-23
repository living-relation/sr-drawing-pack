"""Where the faces are: face count per top-level row of an assembly STEP, and hidden-line time without the heavy rows.

Usage:  python face_budget.py <assembly.step> <out.json> [max_faces_per_part]
Needs:  HBCAD_ROOT and that clone's Python. Rows with more faces than the limit (default 1500) are left out of the
timed views, to show what a "simplified" drawing view of the same assembly costs.
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.environ["HBCAD_ROOT"], "drawing"))
import dwg
from build123d import Compound, import_step

STEP, OUTJ = sys.argv[1], sys.argv[2]; LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
t = time.perf_counter(); shape = import_step(STEP); res = dict(import_s=round(time.perf_counter() - t, 1))
rows = {}
for c in shape.children:
    r = rows.setdefault(c.label, dict(qty=0, faces=len(c.faces()), solids=len(c.solids()))); r["qty"] += 1
res["rows"] = dict(sorted(rows.items(), key=lambda kv: -kv[1]["faces"] * kv[1]["qty"]))
res["total_faces"] = sum(r["faces"] * r["qty"] for r in rows.values())
light = [c for c in shape.children if rows[c.label]["faces"] <= LIMIT]
res["light"] = dict(limit=LIMIT, parts=len(light), faces=sum(rows[c.label]["faces"] for c in light), left_out=sorted(k for k, r in rows.items() if r["faces"] > LIMIT))
json.dump(res, open(OUTJ, "w"), indent=1)
comp = Compound([s for c in light for s in c.solids()]); res["views_light"] = {}
for name in ("front", "top", "right", "iso"):
    cam, up = dwg.VIEWDIR[name]; c, r, u = dwg.basis(cam, up); t = time.perf_counter()
    v, h = comp.project_to_viewport(tuple(c * 5000), tuple(u), (0, 0, 0))
    res["views_light"][name] = dict(hlr_s=round(time.perf_counter() - t, 1), visible=len(v), hidden=len(h))
    json.dump(res, open(OUTJ, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
