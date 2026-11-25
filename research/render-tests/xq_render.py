"""XQ render mode: exact B-rep edges, visibility from a GPU depth buffer (research, 2026-11-24).

Why: exact HLR (HLRBRep_Algo, the UHQ mode) tests every edge against every face on one CPU core, so its time grows
with the square of the model and it timed out on 3 of 16 models. CAD viewers and "draft quality" drawing modes do it
another way: draw the shaded model into a depth buffer on the GPU, then keep each line only where it is not behind
that buffer (Cole & Finkelstein 2009/2010 call this the most common approach). XQ keeps the exact B-rep edges (true
lines, arcs, curves), so line quality is UHQ-like, and takes only *visibility* from the depth buffer. Cost is linear in
model size, and each step uses the hardware that suits it:
  mesh (OCC, all CPU cores) -> depth buffer (VTK/OpenGL, GPU) -> edge sampling (all CPU cores, worker processes)
  -> visibility per point (numpy) -> join + fit true arcs (numpy).
Silhouettes of curved faces are not B-rep edges; they come from the mesh, traced inside each triangle where the
smoothed normal turns edge-on (Hertzmann & Zorin 2000), then fitted back to arcs where they are circular.

Usage:  python xq_render.py <model.step | out_dir with cache.brep> <out_dir> [--res 8192] [--workers 10] [--title NAME]
Needs:  OCP, VTK, numpy, matplotlib. HBCAD_ROOT (optional): the handbuilt-cad view directions and sheet scales,
        so the views match render_modes.py; without it a built-in set is used.
Writes: lines/XQ_<view>.npz (same format as render_modes.py), xq.json (timings), XQ.png (four views).
"""
import os, sys, json, time, argparse, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
VIEWS = ("front", "top", "right", "iso")
PAPER_PX = 0.02            # mm on paper per depth-buffer pixel (target)
PAPER_DEFL = 0.02          # mm on paper, mesh and edge sampling
SMOOTH_DEG = 30.0          # a vertex whose triangles are within this of their mean normal is smooth
def tic(): return time.perf_counter()
def _cast(mod, name): return getattr(mod, name + "_s", None) or getattr(mod, name)


# ================================================================ views
def basis(name):
    if os.environ.get("HBCAD_ROOT"):
        from render_modes import basis as b
        c, r, u = (np.asarray(v, float) for v in b(name))
    else:
        D = {"front": ((0, -1, 0), (0, 0, 1)), "top": ((0, 0, 1), (0, 1, 0)), "right": ((1, 0, 0), (0, 0, 1)),
             "iso": ((1, -1, 1), (0, 0, 1))}
        c = np.array(D[name][0], float); c /= np.linalg.norm(c); up = np.array(D[name][1], float)
        r = np.cross(up, c); r /= np.linalg.norm(r)
    u = np.cross(c, r)                      # 2-D y axis, the same as the HLR projector gp_Ax2(0, c, r)
    return c, r, u

def pick_scale(smax):
    if os.environ.get("HBCAD_ROOT"):
        from render_modes import occ
        return occ().pick_scale(smax)
    for s in (5, 4, 2, 1, 0.5, 0.25, 0.2, 0.1, 0.05, 0.02, 0.01):
        if s <= smax: return s
    return 0.005


# ================================================================ model
STEP_T = {}
def load(src, out):
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape
    cache = os.path.join(src if os.path.isdir(src) else out, "cache.brep"); t = tic()
    if os.path.isfile(cache):
        s = TopoDS_Shape(); BinTools.Read_s(s, cache); return s, cache, round(tic() - t, 2), False
    from OCP.STEPControl import STEPControl_Reader
    rd = STEPControl_Reader(); rd.ReadFile(src); STEP_T["parse_s"] = round(tic() - t, 2); t1 = tic()
    rd.TransferRoots(); s = rd.OneShape(); STEP_T["transfer_s"] = round(tic() - t1, 2); t1 = tic()
    BinTools.Write_s(s, cache); STEP_T["cache_write_s"] = round(tic() - t1, 2); return s, cache, round(tic() - t, 2), True

def bbox(s):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, True); p, q = b.CornerMin(), b.CornerMax()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])

def sheet_scale(lo, hi):
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    ext = {}
    for v in VIEWS:
        c, r, u = basis(v); ext[v] = (np.ptp(corners @ r), np.ptp(corners @ u))
    smax = min((262 - 28) / (ext["front"][0] + ext["right"][0]), (172 - 24) / (ext["front"][1] + ext["top"][1]))
    return pick_scale(smax)

def triangles(s, tmp):
    """All mesh triangles as an (n, 3, 3) float32 array, through a binary STL (much faster than a Python loop)."""
    from OCP.StlAPI import StlAPI_Writer
    w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(s, tmp)
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    with open(tmp, "rb") as f:
        f.seek(80); n = int(np.frombuffer(f.read(4), "<u4")[0]); rec = np.frombuffer(f.read(n * 50), dt)
    os.remove(tmp); return np.ascontiguousarray(rec["v"])

def weld(T):
    """Vertex ids for a triangle soup (vertices equal to float32 precision become one)."""
    V = T.reshape(-1, 3); key = np.ascontiguousarray(V).view(np.dtype((np.void, 12))).ravel()
    _, first, inv = np.unique(key, return_index=True, return_inverse=True)
    return V[first], inv.reshape(-1, 3)

def corner_normals(F, Nraw, nv):
    """Smoothed normal per triangle corner (Hertzmann & Zorin 2000 smooth silhouettes): the area-weighted mean of the
    normals of the triangles at that vertex that lie within SMOOTH_DEG of this triangle. So a cylinder strip (every
    vertex on a sharp cap edge) is still smooth around its axis, and creases make no false silhouettes."""
    Nu = Nraw / (np.linalg.norm(Nraw, axis=1, keepdims=True) + 1e-30)
    cv = F.ravel(); ct = np.repeat(np.arange(len(F)), 3); o = np.argsort(cv, kind="stable"); cv, ct = cv[o], ct[o]
    st = np.r_[0, np.nonzero(cv[1:] != cv[:-1])[0] + 1]; deg = np.diff(np.r_[st, len(cv)])
    out = np.zeros((len(cv), 3)); cosT = np.cos(np.radians(SMOOTH_DEG))
    for d in np.unique(deg):
        gs = st[deg == d]
        for c0 in range(0, len(gs), max(1, 2_000_000 // (d * d))):
            g = gs[c0:c0 + max(1, 2_000_000 // (d * d))]
            idx = g[:, None] + np.arange(d)[None, :]                  # (n, d) corner slots
            Nn, Nw = Nu[ct[idx]], Nraw[ct[idx]]                       # unit and area-weighted normals
            near = np.einsum("nik,njk->nij", Nn, Nn) > cosT           # (n, d, d)
            out[idx] = np.einsum("nij,njk->nik", near.astype(float), Nw)
    out /= np.linalg.norm(out, axis=1, keepdims=True) + 1e-30
    CN = np.zeros((len(F), 3, 3)); k = np.tile(np.arange(3), len(F))[o]
    CN[ct, k] = out
    return CN

def smooth_silhouettes(V, F, CN, c):
    """Silhouette segments inside triangles: where the interpolated normal . c crosses zero. Returns (n, 2, 3)."""
    g = CN @ c                                              # (t, 3) per corner
    g = np.where(np.abs(g) < 1e-5, 1e-12, g)               # on the silhouette (or float noise on an edge-on flat face): front
    s = g > 0; cross = (s.any(1) & ~s.all(1)) & (np.abs(g).max(1) > 5e-4)   # edge-on flat faces: float32 noise only
    Ft, gt = F[cross], g[cross]; out = []
    pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ga, gb = gt[:, a], gt[:, b]; ok = (ga > 0) != (gb > 0)
        va, vb = Ft[:, a], Ft[:, b]; swap = va > vb                     # same order on both triangles of an edge
        lo_v = np.where(swap, vb, va); hi_v = np.where(swap, va, vb); glo = np.where(swap, gb, ga); ghi = np.where(swap, ga, gb)
        t = glo / np.where(ok, glo - ghi, 1.0)
        P = V[lo_v].astype(float) + t[:, None] * (V[hi_v].astype(float) - V[lo_v].astype(float))
        pts.append((ok, P))
    (o0, P0), (o1, P1), (o2, P2) = pts
    A = np.where(o0[:, None], P0, P1); B = np.where(o0[:, None] & o1[:, None], P1, P2)
    S = np.stack([A, B], axis=1)
    S = S[np.linalg.norm(A - B, axis=1) > 1e-9]              # drop zero-length bits at such vertices
    if not len(S): return S
    k = np.round(S / 1e-7).astype(np.int64).reshape(len(S), 6)    # drop duplicates (either direction)
    a, b = k[:, :3], k[:, 3:]
    flip = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & ((a[:, 1] > b[:, 1]) | ((a[:, 1] == b[:, 1]) & (a[:, 2] > b[:, 2]))))
    kk = np.where(flip[:, None], np.c_[b, a], np.c_[a, b]); _, first = np.unique(kk, axis=0, return_index=True)
    return S[np.sort(first)]


# ================================================================ exact edges, sampled in 3-D (worker processes)
def sample_edges(args):
    """Worker: sample unique edges [i0, i1) of the cached shape. Returns (points, counts, tangent flags)."""
    cache, i0, i1, defl, step = args
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.BRep import BRep_Tool
    from OCP.BRepLib import BRepLib
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.GeomAbs import GeomAbs_G1, GeomAbs_Line
    s = TopoDS_Shape(); BinTools.Read_s(s, cache)
    m = TopTools_IndexedDataMapOfShapeListOfShape(); TopExp.MapShapesAndAncestors_s(s, TopAbs_EDGE, TopAbs_FACE, m)
    pts, cnt, tan = [], [], []
    for i in range(i0 + 1, min(i1, m.Extent()) + 1):
        e = _cast(TopoDS, "Edge")(m.FindKey(i))
        if BRep_Tool.Degenerated_s(e): continue
        faces = [_cast(TopoDS, "Face")(f) for f in m.FindFromIndex(i)]
        if len(faces) == 1 and BRep_Tool.IsClosed_s(e, faces[0]): continue        # seam of a closed face: not a line
        t = False
        if len(faces) >= 2:
            f0, f1 = faces[0], faces[1]
            if f0.IsSame(f1) and BRep_Tool.IsClosed_s(e, f0): continue          # seam listed twice
            try:
                BRepLib.EncodeRegularity_s(e, f0, f1, 0.01)                  # tangent within ~0.6 deg
                t = int(BRep_Tool.Continuity_s(e, f0, f1)) >= int(GeomAbs_G1)
            except Exception: t = False
        try:
            ad = BRepAdaptor_Curve(e)
            if ad.GetType() == GeomAbs_Line:
                p, q = ad.Value(ad.FirstParameter()), ad.Value(ad.LastParameter())
                P = np.array([[p.X(), p.Y(), p.Z()], [q.X(), q.Y(), q.Z()]])
            else:
                g = GCPnts_QuasiUniformDeflection(ad, defl)
                if not g.IsDone() or g.NbPoints() < 2: continue
                P = np.array([[g.Value(j).X(), g.Value(j).Y(), g.Value(j).Z()] for j in range(1, g.NbPoints() + 1)])
        except Exception:
            continue
        P = densify(P, step)
        pts.append(P.astype(np.float64)); cnt.append(len(P)); tan.append(t)
    if not pts: return np.zeros((0, 3)), np.zeros(0, int), np.zeros(0, bool)
    return np.concatenate(pts), np.array(cnt), np.array(tan)

def densify(P, step):
    """Insert points so no gap is longer than step (visibility is tested at every point). Vectorised."""
    d = np.linalg.norm(np.diff(P, axis=0), axis=1); n = np.maximum(1, np.ceil(d / step).astype(int))
    if n.max() == 1: return P
    i = np.repeat(np.arange(len(n)), n); k = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + 1
    return np.vstack([P[:1], P[i] + (P[i + 1] - P[i]) * (k / n[i])[:, None]])

def edge_count(s):
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as TopTools_IndexedDataMapOfShapeListOfShape
    m = TopTools_IndexedDataMapOfShapeListOfShape(); TopExp.MapShapesAndAncestors_s(s, TopAbs_EDGE, TopAbs_FACE, m); return m.Extent()


# ================================================================ depth buffer (GPU through VTK)
class DepthRenderer:
    def __init__(self, V, F):
        import vtk
        from vtk.util import numpy_support as ns
        self.vtk = vtk
        pts = vtk.vtkPoints(); pts.SetData(ns.numpy_to_vtk(V.astype(np.float32), deep=True))
        cells = vtk.vtkCellArray()
        off = np.arange(0, 3 * len(F) + 1, 3, dtype=np.int64)
        cells.SetData(ns.numpy_to_vtkIdTypeArray(off, deep=True), ns.numpy_to_vtkIdTypeArray(F.astype(np.int64).ravel(), deep=True))
        pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
        mp = vtk.vtkPolyDataMapper(); mp.SetInputData(pd); mp.ScalarVisibilityOff()
        act = vtk.vtkActor(); act.SetMapper(mp); act.GetProperty().LightingOff()
        self.ren = vtk.vtkRenderer(); self.ren.AddActor(act)
        self.win = vtk.vtkRenderWindow(); self.win.SetOffScreenRendering(1); self.win.AddRenderer(self.ren)
        self.center = (V.min(0) + V.max(0)) / 2; self.radius = np.linalg.norm(V.max(0) - V.min(0)) / 2 + 1e-6

    def render(self, c, r, u, ext_r, ext_u, res):
        """Depth image for view direction c (towards the viewer). Returns (zbuf [H, W] in 0..1, world->window fn)."""
        vtk = self.vtk
        pad = 1.04; W = max(16, int(res * min(1.0, ext_r / max(ext_r, ext_u)))); H = max(16, int(res * min(1.0, ext_u / max(ext_r, ext_u))))
        self.win.SetSize(W, H)
        cam = self.ren.GetActiveCamera(); cam.ParallelProjectionOn()
        cam.SetFocalPoint(*self.center); cam.SetPosition(*(self.center + c * 4 * self.radius)); cam.SetViewUp(*u)
        cam.SetParallelScale(max(ext_u, ext_r * H / W) / 2 * pad)
        cam.SetClippingRange(2 * self.radius, 6 * self.radius)
        self.win.Render()
        z = vtk.vtkFloatArray(); self.win.GetZbufferData(0, 0, W - 1, H - 1, z)
        from vtk.util import numpy_support as ns
        zb = ns.vtk_to_numpy(z).reshape(H, W).copy()
        M = np.array([[cam.GetCompositeProjectionTransformMatrix(W / H, -1, 1).GetElement(i, j) for j in range(4)] for i in range(4)])
        def to_win(P):
            h = np.c_[P, np.ones(len(P))] @ M.T; ndc = h[:, :3] / h[:, 3:4]
            return (ndc[:, 0] + 1) / 2 * W - 0.5, (ndc[:, 1] + 1) / 2 * H - 0.5, (ndc[:, 2] + 1) / 2
        dz_per_mm = 1.0 / (4 * self.radius)          # window depth per model mm (range 2R..6R)
        px_mm = 2 * cam.GetParallelScale() / H       # model mm per pixel
        return zb, to_win, dz_per_mm, px_mm


def visible(P, zb, to_win, tol_z):
    """True where a point is not behind the depth buffer. The 3x3 farthest depth keeps lines on their own faces."""
    H, W = zb.shape; x, y, z = to_win(P)
    xi = np.clip(np.rint(x).astype(int), 0, W - 1); yi = np.clip(np.rint(y).astype(int), 0, H - 1)
    best = np.zeros(len(P))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            best = np.maximum(best, zb[np.clip(yi + dy, 0, H - 1), np.clip(xi + dx, 0, W - 1)])
    return z <= best + tol_z

def runs(P2, keep, counts, gap=3, short=4):
    """Split polylines (2-D points, counts) into the runs where keep is True, all edges at once. Hidden gaps of up
    to `gap` samples inside an edge are filled; visible bits under `short` samples are dropped unless they are the
    whole edge."""
    if not len(counts): return []
    eid = np.repeat(np.arange(len(counts)), counts); keep = keep.copy()
    for stage in (0, 1):
        ch = np.r_[True, (keep[1:] != keep[:-1]) | (eid[1:] != eid[:-1])]; st = np.nonzero(ch)[0]
        en = np.r_[st[1:], len(keep)]; ln = en - st; val = keep[st]; re = eid[st]
        if stage == 0:                       # fill short hidden gaps between two visible runs of the same edge
            prev_ok = np.r_[False, val[:-1] & (re[:-1] == re[1:])]; next_ok = np.r_[val[1:] & (re[1:] == re[:-1]), False]
            fill = ~val & (ln <= gap) & prev_ok & next_ok
            for a, b in zip(st[fill], en[fill]): keep[a:b] = True
        else:
            whole = ln == counts[re]
            good = val & (ln >= 2) & ((ln >= short) | whole)
            return [P2[a:b] for a, b in zip(st[good], en[good])]

def chain_snap(segs, r, segs3=None):
    """Join 2-D segments (n, 2, 2) into polylines; ends closer than r are one point (union of near pairs). With
    segs3 (n, 2, 3), returns the matching 3-D polylines instead."""
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    if not len(segs): return []
    P0 = segs.reshape(-1, 2)
    _, first, cell = np.unique(np.floor(P0 / (r / 4)).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    P = P0[first]; cell = cell.ravel()                       # merge coincident points first (no pair explosion)
    pr = cKDTree(P).query_pairs(r, output_type="ndarray"); n = len(P)
    g = coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(n, n)) if len(pr) else coo_matrix((n, n))
    _, lab = connected_components(g, directed=False); lab = lab[cell]; P = P0 if segs3 is None else segs3.reshape(-1, 3)
    a, b = lab[0::2], lab[1::2]; keep = a != b
    a, b, segs = a[keep], b[keep], segs[keep]
    cen = np.zeros((lab.max() + 1, P.shape[1])); cnt = np.zeros(lab.max() + 1); np.add.at(cen, lab, P); np.add.at(cnt, lab, 1)
    cen /= np.maximum(cnt, 1)[:, None]
    adj = {}
    for i, (x, y) in enumerate(zip(a, b)): adj.setdefault(x, []).append((i, y)); adj.setdefault(y, []).append((i, x))
    used = np.zeros(len(a), bool); out = []
    def walk(start, i, nxt):
        line = [start, nxt]; used[i] = True; cur = nxt
        while len(adj[cur]) == 2:
            cand = [(j, w) for j, w in adj[cur] if not used[j]]
            if not cand: break
            j, w = cand[0]; used[j] = True; line.append(w); cur = w
        return cen[line]
    for node, lst in adj.items():
        if len(lst) != 2:
            for i, w in lst:
                if not used[i]: out.append(walk(node, i, w))
    for i in range(len(a)):
        if not used[i]: out.append(walk(a[i], i, b[i]))
    return out

def simplify(p, eps=1e-4):
    """Drop interior points on a straight run; keep points where the line turns back (a circle seen edge-on)."""
    if len(p) < 3: return p
    a, b, c = p[:-2], p[1:-1], p[2:]
    cr = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    back = ((b - a) * (c - b)).sum(1) <= 0
    keep = np.r_[True, (cr / (np.hypot(*(c - a).T) + 1e-12) > eps) | back, True]
    return p[keep]

def drop_specks(pl, min_len):
    return [p for p in pl if np.hypot(*np.diff(p, axis=0).T).sum() >= min_len]


# ================================================================ main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--res", type=int, default=0, help="depth-buffer pixels on the long side (0 = from sheet scale)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2)); ap.add_argument("--title", default="")
    ap.add_argument("--no-fit", action="store_true")
    a = ap.parse_args(); os.makedirs(os.path.join(a.out, "lines"), exist_ok=True)
    T = {}; t0 = tic()
    s, cache, T["load_s"], from_step = load(a.src, a.out); T["from_step"] = from_step; T.update(STEP_T)
    lo, hi = bbox(s); scale = sheet_scale(lo, hi); size = float(np.linalg.norm(hi - lo))
    defl = PAPER_DEFL / scale
    # ---- mesh (all cores) and triangles
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    t = tic(); BRepMesh_IncrementalMesh(s, defl, False, 0.25, True); T["mesh_s"] = round(tic() - t, 2)
    t = tic(); tri = triangles(s, os.path.join(tempfile.gettempdir(), f"xq_{os.getpid()}.stl")); T["tris"] = len(tri)
    V, F = weld(tri); Nraw = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]).astype(np.float64)
    CN = corner_normals(F, Nraw, len(V))
    T["tri_s"] = round(tic() - t, 2)
    # ---- exact edges, sampled once in 3-D (all cores), while the GPU draws
    paper_long = max(np.ptp(np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) @ basis(v)[1]) for v in VIEWS) * scale
    res = a.res or int(np.clip(paper_long / PAPER_PX, 2048, 16384))
    step = 0.7 * size / res                         # about 0.7 px between visibility samples
    ne = edge_count(s); nw = max(1, min(a.workers, ne // 200 + 1)); bounds = np.linspace(0, ne, nw + 1).astype(int)
    jobs = [(cache, int(bounds[i]), int(bounds[i + 1]), defl, step) for i in range(nw)]
    t = tic()
    if nw > 1:
        from concurrent.futures import ProcessPoolExecutor
        ex = ProcessPoolExecutor(nw); fut = ex.map(sample_edges, jobs)
    else:
        fut = map(sample_edges, jobs)
    dr = DepthRenderer(V, F); T["gpu_upload_s"] = round(tic() - t, 2)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    depth = {}
    for v in VIEWS:
        c, r, u = basis(v); tv = tic()
        depth[v] = dr.render(c, r, u, np.ptp(corners @ r), np.ptp(corners @ u), res) + (round(tic() - tv, 2),)
    parts = list(fut)
    if nw > 1: ex.shutdown()
    EP = np.concatenate([p[0] for p in parts]); EC = np.concatenate([p[1] for p in parts]).astype(int)
    ET = np.concatenate([p[2] for p in parts]).astype(bool)
    T["edges"] = int(len(EC)); T["edge_pts"] = int(len(EP)); T["edges_gpu_s"] = round(tic() - t, 2); T["workers"] = nw
    T["res"] = res; T["scale"] = scale; T["views"] = {}
    from render_modes import to_prims, save_lines
    eo = np.r_[0, np.cumsum(EC)]
    for v in VIEWS:
        c, r, u = basis(v); zb, to_win, dz, px, t_gpu = depth[v]; tv = tic()
        tol = dz * (2.5 * px + defl)
        keep = visible(EP, zb, to_win, tol); P2 = np.c_[EP @ r, EP @ u]
        vis, tan = [], []
        for flag, dest in ((False, vis), (True, tan)):
            idx = np.nonzero(np.repeat(ET == flag, EC))[0]
            dest += runs(P2[idx], keep[idx], EC[ET == flag])
        t_edges = tic() - tv
        # silhouettes of curved faces, traced inside the triangles
        tv = tic(); SG = smooth_silhouettes(V, F, CN, c)
        if len(SG):                                  # pieces seen end-on are points on paper: drop them
            SG = SG[np.linalg.norm((SG[:, 1] - SG[:, 0]) @ np.c_[r, u], axis=1) > 0.5 * px]
        if len(SG):                                  # join first (few pieces), then split by visibility
            pl3 = chain_snap(np.stack([SG @ r, SG @ u], axis=-1), 0.3 * px, SG)
            dense = [densify(p, step) for p in pl3]; cnt = np.array([len(p) for p in dense])
            SP = np.concatenate(dense); sk = visible(SP, zb, to_win, tol)
            vis += drop_specks(runs(np.c_[SP @ r, SP @ u], sk, cnt), 3 * px)
        E = SG
        t_sil = tic() - tv
        tv = tic()
        if a.no_fit:
            save_lines(os.path.join(a.out, "lines", f"XQ_{v}.npz"), vis, tan)
        else:
            vis, tan = [simplify(p) for p in vis], [simplify(p) for p in tan]     # straight runs: end points only
            prims = {"vis": [to_prims(p) for p in vis], "tan": [to_prims(p) for p in tan]}
            save_lines(os.path.join(a.out, "lines", f"XQ_{v}.npz"), vis, tan, prims)
        T["views"][v] = dict(gpu_s=t_gpu, edges_s=round(t_edges, 2), sil_s=round(t_sil, 2), fit_s=round(tic() - tv, 2),
                             vis=len(vis), tan=len(tan), sil_edges=int(len(E)))
    T["total_s"] = round(tic() - t0, 2)
    json.dump(T, open(os.path.join(a.out, "xq.json"), "w"), indent=1); print(json.dumps(T))
    draw_png(a.out, a.title or os.path.basename(os.path.normpath(a.out)), T)

def draw_png(out, title, T):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from render_modes import load_lines, prim_pts
    fig, axs = plt.subplots(1, 4, figsize=(20, 5.6))
    for ax, v in zip(axs, VIEWS):
        L = load_lines(os.path.join(out, "lines", f"XQ_{v}.npz")); items = []
        for key in ("vis", "tan"):
            pl, arcs, circ = L[key]; items += [(p, key) for p in pl]
            items += [(prim_pts(("A",) + tuple(x)), key) for x in arcs] + [(prim_pts(("C",) + tuple(x)), key) for x in circ]
        for key, lw, col in (("vis", 0.5, "k"), ("tan", 0.3, "0.45")):
            ax.add_collection(LineCollection([p for p, k in items if k == key], linewidths=lw, colors=col))
        ax.autoscale(); ax.set_aspect("equal"); ax.axis("off"); tv = T["views"][v]
        ax.set_title(f"XQ {v.upper()}: {tv['vis'] + tv['tan']} lines", fontsize=9)
    fig.suptitle(f"XQ on {title}: total {T['total_s']} s (load {T['load_s']} s, {T['tris']:,} triangles, {T['edges']:,} edges, "
                 f"depth {T['res']} px, {T['workers']} workers)", fontsize=10)
    fig.savefig(os.path.join(out, "XQ.png"), dpi=110); plt.close(fig)

if __name__ == "__main__":
    main()
