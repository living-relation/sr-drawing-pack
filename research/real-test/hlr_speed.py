"""Faster hidden-line removal for big assemblies: three ways, timed on one view of a real assembly STEP.

Usage:  python hlr_speed.py <assembly.step> <out_dir> [view]
Needs:  HBCAD_ROOT and that clone's Python (build123d / OCP).

  A  poly    OCCT HLRBRep_PolyAlgo on a triangulated copy (what FreeCAD TechDraw calls a "coarse view",
             SolidWorks "draft quality"): polygon lines, much faster than the exact HLRBRep_Algo.
  B  hybrid  exact B-rep edges, each sampled along its length and kept where a z-buffer of the
             triangulated assembly says it is in front. Exact lines out, visibility from a raster.
  C  exact   the engine's current call (HLRBRep_Algo), only if asked with view=...:exact (slow).
Writes <view>_<method>.png for a look, and hlr_speed.json with the timings.
"""
import os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.environ["HBCAD_ROOT"], "drawing"))
import dwg
from build123d import import_step
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

STEP, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
VIEW = (sys.argv[3] if len(sys.argv) > 3 else "front").split(":")[0]; EXACT = sys.argv[3:4] and sys.argv[3].endswith(":exact")
res = {"view": VIEW}; JS = os.path.join(OUT, "hlr_speed.json")
def save(): json.dump(res, open(JS, "w"), indent=1)
def tic(): return time.perf_counter()

t = tic(); shp = import_step(STEP); res["import_s"] = round(tic() - t, 1)
occ = shp.wrapped; cam, up = dwg.VIEWDIR[VIEW]; c, r, u = dwg.basis(cam, up)
t = tic(); BRepMesh_IncrementalMesh(occ, 0.2, False, 0.5, True); res["mesh_s"] = round(tic() - t, 1); save()

def edges_of(s):
    out = []; ex = TopExp_Explorer(s, TopAbs_EDGE)
    while ex.More(): out.append(TopoDS.Edge(ex.Current())); ex.Next()
    return out

def plot(lines, name):
    fig = plt.figure(figsize=(10, 7)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect("equal"); ax.axis("off")
    for p in lines:
        if len(p) > 1: ax.plot(p[:, 0], p[:, 1], "k-", lw=0.4)
    fig.savefig(os.path.join(OUT, f"{VIEW}_{name}.png"), dpi=110); plt.close(fig)

# ---- A: polygonal HLR -------------------------------------------------------------------------------
t = tic()
algo = HLRBRep_PolyAlgo(); algo.Load(occ)
algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*c), gp_Dir(*r))))
algo.Update()
h2s = HLRBRep_PolyHLRToShape(); h2s.Update(algo)
vis = [h2s.VCompound(), h2s.OutLineVCompound(), h2s.Rg1LineVCompound()]
res["poly_s"] = round(tic() - t, 1); save()
from OCP.BRepAdaptor import BRepAdaptor_Curve
poly = []; res["poly_compounds"] = [bool(cp is not None and not cp.IsNull()) for cp in vis]
for comp in vis:
    if comp is None or comp.IsNull(): continue
    for e in edges_of(comp):
        a = BRepAdaptor_Curve(e); f, l = a.FirstParameter(), a.LastParameter()
        poly.append(np.array([[a.Value(x).X(), a.Value(x).Y()] for x in np.linspace(f, l, 2)]))
res["poly_lines"] = len(poly); save(); plot(poly, "poly")
if os.environ.get("POLY_ONLY"): print(json.dumps(res, indent=1)); sys.exit(0)

# ---- B: exact edges + z-buffer visibility -------------------------------------------------------------
t = tic()
tris = []; ex = TopExp_Explorer(occ, TopAbs_FACE)
while ex.More():
    fc = TopoDS.Face(ex.Current()); loc = TopLoc_Location(); tri = BRep_Tool.Triangulation_s(fc, loc)
    if tri is not None:
        tr = loc.Transformation()
        P = np.array([[tri.Node(i).Transformed(tr).X(), tri.Node(i).Transformed(tr).Y(), tri.Node(i).Transformed(tr).Z()] for i in range(1, tri.NbNodes() + 1)])
        T = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)]) - 1
        tris.append(P[T])
    ex.Next()
tris = np.concatenate(tris); res["triangles"] = int(len(tris)); res["collect_tris_s"] = round(tic() - t, 1); save()

N = 2400                                                    # z-buffer size (pixels on the long side)
t = tic()
U, V, D = tris @ r, tris @ u, tris @ c                     # screen x, y and depth (bigger D = nearer the viewer)
lo = np.array([U.min(), V.min()]); span = max(U.max() - lo[0], V.max() - lo[1]); k = (N - 1) / span
zb = np.full((N, N), -np.inf)
X, Y = (U - lo[0]) * k, (V - lo[1]) * k
for i in range(len(tris)):                                  # simple triangle rasteriser (numpy per triangle)
    x, y, d = X[i], Y[i], D[i]
    x0, x1 = int(max(0, np.floor(x.min()))), int(min(N - 1, np.ceil(x.max()))); y0, y1 = int(max(0, np.floor(y.min()))), int(min(N - 1, np.ceil(y.max())))
    if x1 < x0 or y1 < y0: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
    if abs(den) < 1e-12: continue
    a = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
    b = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
    g = 1 - a - b; m = (a >= -1e-6) & (b >= -1e-6) & (g >= -1e-6)
    if not m.any(): continue
    z = a * d[0] + b * d[1] + g * d[2]; sub = zb[y0:y1 + 1, x0:x1 + 1]
    np.maximum(sub, np.where(m, z, -np.inf), out=sub)
res["zbuffer_s"] = round(tic() - t, 1); save()

t = tic(); hyb = []; tol = 3.0 / k                           # depth tolerance: a few pixels' worth of model size
for e in edges_of(occ):
    p = dwg._edge_pts3d(e, 0.05)
    if p is None or len(p) < 2: continue
    px = np.clip(((p @ r - lo[0]) * k).round().astype(int), 0, N - 1); py = np.clip(((p @ u - lo[1]) * k).round().astype(int), 0, N - 1)
    seen = (p @ c) >= zb[py, px] - tol
    if not seen.any(): continue
    q = np.c_[p @ r, p @ u]; start = None                   # keep the visible runs of each edge
    for i, s_ in enumerate(np.append(seen, False)):
        if s_ and start is None: start = i
        elif not s_ and start is not None:
            if i - start > 1: hyb.append(q[start:i])
            start = None
res["hybrid_classify_s"] = round(tic() - t, 1); res["hybrid_lines"] = len(hyb); save(); plot(hyb, "hybrid")

if EXACT:
    t = tic(); v, h = shp.project_to_viewport(tuple(c * 5000), tuple(u), (0, 0, 0)); res["exact_s"] = round(tic() - t, 1); res["exact_visible"] = len(v)
save(); print(json.dumps(res, indent=1))
