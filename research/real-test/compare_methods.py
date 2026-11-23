"""Example sheet: the same part drawn by each view method, for any model type (ADR-039).

Usage:  python compare_methods.py <assembly.step> <part label> <out_dir>
Needs:  HBCAD_ROOT and that clone's Python (build123d, OCP, trimesh, matplotlib).

Rows (front view and trimetric each):
  1 exact     B-rep hidden-line removal (HLRBRep_Algo), the engine's current method
  2 fast      polygonal hidden-line removal on a 0.2 mm mesh of the B-rep, raw 2-point pieces
  3 fast+     the same lines joined into continuous polylines
  4 mesh, raw the part saved as STL and read back as a mesh body (one face per triangle), polygonal method:
              every triangle edge shows (the failure case)
  5 mesh, fix the same mesh body drawn from its creases (faces meeting at more than 25 deg) and silhouettes,
              visibility from a z-buffer, joined into polylines
Each cell is labelled with time and line count. Output: compare_methods.pdf / .png and compare_methods.json.
"""
import os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.environ["HBCAD_ROOT"], "drawing"))
import dwg
from build123d import import_step, export_stl, Compound
import trimesh
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS, TopoDS_Shape
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.StlAPI import StlAPI_Reader
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

STEP, LABEL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; os.makedirs(OUT, exist_ok=True)
VIEWS = ("front", "iso"); res = {}
def tic(): return time.perf_counter()

asm = import_step(STEP)
node = next(c for c in asm.children if c.label == LABEL)
part = Compound([s.moved(node.location.inverse()) for s in node.solids()])
res["part"] = dict(label=LABEL, solids=len(part.solids()), faces=len(part.faces()))

def basis(name): cam, up = dwg.VIEWDIR[name]; return dwg.basis(cam, up)

def poly_hlr(shape, name):
    c, r, u = basis(name)
    a = HLRBRep_PolyAlgo(); a.Load(shape); a.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*c), gp_Dir(*r)))); a.Update()
    h = HLRBRep_PolyHLRToShape(); h.Update(a); segs = []
    for comp in (h.VCompound(), h.OutLineVCompound()) + ((h.Rg1LineVCompound(),) if name == "iso" else ()):
        if comp is None or comp.IsNull(): continue
        ex = TopExp_Explorer(comp, TopAbs_EDGE)
        while ex.More():
            e = BRepAdaptor_Curve(TopoDS.Edge(ex.Current())); p, q = e.Value(e.FirstParameter()), e.Value(e.LastParameter())
            segs.append(np.array([[p.X(), p.Y()], [q.X(), q.Y()]])); ex.Next()
    return segs

def chain(segs, tol=1e-3):
    """Join 2-point pieces into continuous polylines through every point where exactly two pieces meet."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    adj = {}; pts = {}
    for i, s in enumerate(segs):
        for j in (0, 1):
            k = key(s[j]); adj.setdefault(k, []).append((i, j)); pts[k] = s[j]
    used = [False] * len(segs); out = []
    def walk(i, j):
        line = [segs[i][j], segs[i][1 - j]]; used[i] = True; k = key(segs[i][1 - j])
        while len(adj[k]) == 2:
            nxt = [(a, b) for a, b in adj[k] if not used[a]]
            if not nxt: break
            a, b = nxt[0]; used[a] = True; line.append(segs[a][1 - b]); k = key(segs[a][1 - b])
        return line
    for k, ends in adj.items():                       # start at chain ends first, then closed loops
        if len(ends) != 2:
            for i, j in ends:
                if not used[i]: out.append(np.array(walk(i, j)))
    for i in range(len(segs)):
        if not used[i]: out.append(np.array(walk(i, 0)))
    return out

def exact(name):
    c, r, u = basis(name); v, h = part.project_to_viewport(tuple(c * 5000), tuple(u), (0, 0, 0))
    return [p for p in (dwg.edge_pts(e, 0.02) for e in v) if len(p) > 1]

def zbuffer(tris, c, r, u, N=1600):
    U, V, D = tris @ r, tris @ u, tris @ c
    lo = np.array([U.min(), V.min()]); k = (N - 1) / max(U.max() - lo[0], V.max() - lo[1])
    zb = np.full((N, N), -np.inf); X, Y = (U - lo[0]) * k, (V - lo[1]) * k
    for i in range(len(tris)):
        x, y, d = X[i], Y[i], D[i]
        x0, x1 = int(max(0, np.floor(x.min()))), int(min(N - 1, np.ceil(x.max()))); y0, y1 = int(max(0, np.floor(y.min()))), int(min(N - 1, np.ceil(y.max())))
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if x1 < x0 or y1 < y0 or abs(den) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        a = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den; b = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
        m = (a >= -1e-6) & (b >= -1e-6) & (1 - a - b >= -1e-6)
        if m.any():
            sub = zb[y0:y1 + 1, x0:x1 + 1]; np.maximum(sub, np.where(m, a * d[0] + b * d[1] + (1 - a - b) * d[2], -np.inf), out=sub)
    return zb, lo, k

def mesh_feature_lines(m, name, crease_deg=25.0):
    """Creases, silhouettes and open boundaries of a triangle mesh, kept where a z-buffer says they are in front."""
    c, r, u = basis(name); fn = m.face_normals; facing = fn @ c
    ea = m.face_adjacency_edges; fa = m.face_adjacency; ang = np.degrees(m.face_adjacency_angles)
    keep = (ang > crease_deg) | (np.sign(facing[fa[:, 0]]) != np.sign(facing[fa[:, 1]]))
    edges = list(ea[keep]) + list(m.edges_sorted[trimesh.grouping.group_rows(m.edges_sorted, require_count=1)])
    zb, lo, k = zbuffer(m.triangles, c, r, u); N = zb.shape[0]; tol = 2.5 / k; segs = []
    for a, b in edges:
        P = np.linspace(m.vertices[a], m.vertices[b], max(2, int(np.linalg.norm(m.vertices[b] - m.vertices[a]) * k / 2) + 2))
        px = np.clip(((P @ r - lo[0]) * k).round().astype(int), 0, N - 1); py = np.clip(((P @ u - lo[1]) * k).round().astype(int), 0, N - 1)
        seen = (P @ c) >= zb[py, px] - tol; q = np.c_[P @ r, P @ u]; start = None
        for i, s in enumerate(np.append(seen, False)):
            if s and start is None: start = i
            elif not s and start is not None:
                if i - start > 1: segs.append(np.array([q[start], q[i - 1]]))
                start = None
    return segs

rows = []
def run(label, fn):
    cells = []
    for name in VIEWS:
        t = tic(); lines = fn(name); dt = tic() - t; cells.append((name, lines, dt))
    rows.append((label, cells)); res[label] = {n: dict(seconds=round(dt, 2), lines=len(l)) for n, l, dt in cells}
    json.dump(res, open(os.path.join(OUT, "compare_methods.json"), "w"), indent=1)

t = tic(); BRepMesh_IncrementalMesh(part.wrapped, 0.2, False, 0.5, True); res["mesh_brep_s"] = round(tic() - t, 2)
run("1  exact B-rep", exact)
run("2  fast, raw pieces", lambda n: poly_hlr(part.wrapped, n))
run("3  fast, joined", lambda n: chain(poly_hlr(part.wrapped, n)))
stl = os.path.join(OUT, "part_as_mesh.stl"); export_stl(part, stl, tolerance=0.2, angular_tolerance=0.3)
mb = TopoDS_Shape(); StlAPI_Reader().Read(mb, stl); BRepMesh_IncrementalMesh(mb, 0.2, False, 0.5, True)
tm = trimesh.load(stl, force="mesh"); res["mesh_triangles"] = int(len(tm.faces))
run("4  mesh body, fast (wrong)", lambda n: poly_hlr(mb, n))
run("5  mesh body, creases + silhouettes", lambda n: chain(mesh_feature_lines(tm, n)))

fig, axs = plt.subplots(len(rows), 2, figsize=(11, 17))
for (label, cells), axr in zip(rows, axs):
    for (name, lines, dt), ax in zip(cells, axr):
        ax.set_aspect("equal"); ax.axis("off")
        for p in lines:
            p = np.asarray(p)
            if len(p) > 1: ax.plot(p[:, 0], p[:, 1], "k-", lw=0.5, solid_joinstyle="round")
        ax.set_title(f"{label}  |  {'FRONT' if name == 'front' else 'TRIMETRIC'}\n{dt:.1f} s, {len(lines)} lines", fontsize=8, loc="left")
fig.suptitle(f"View methods compared on {LABEL} ({res['part']['faces']} faces; mesh {res['mesh_triangles']} triangles)", fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.98))
fig.savefig(os.path.join(OUT, "compare_methods.pdf")); fig.savefig(os.path.join(OUT, "compare_methods.png"), dpi=110); plt.close(fig)
# mode-picker thumbnails (ADR-040): the trimetric of each accepted mode, one small PNG each
MODES = {"1  exact B-rep": "UHQ", "3  fast, joined": "HQ", "2  fast, raw pieces": "DRAFT", "5  mesh body, creases + silhouettes": "FAST_DRAFT"}
for label, cells in rows:
    if label not in MODES: continue
    name, lines, dt = cells[1]
    fig = plt.figure(figsize=(2.4, 1.8)); ax = fig.add_axes([0.02, 0.12, 0.96, 0.86]); ax.set_aspect("equal"); ax.axis("off")
    for p in lines:
        p = np.asarray(p)
        if len(p) > 1: ax.plot(p[:, 0], p[:, 1], "k-", lw=0.35, solid_joinstyle="round")
    fig.text(0.5, 0.03, MODES[label].replace("_", " "), ha="center", fontsize=8, fontweight="bold")
    fig.savefig(os.path.join(OUT, f"mode_{MODES[label]}.png"), dpi=150); plt.close(fig)
print(json.dumps(res, indent=1))
