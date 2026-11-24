"""Render-mode tests on a real model (ADR-040, ADR-042, H34b): the four standard views in each render mode, each run
before and after the H40a anti-aliasing fixes.

Usage:  python render_modes.py <model.step> <out_dir> [--modes UHQ,HQ,DRAFT,FAST] [--uhq-timeout 120] [--title NAME]
Needs:  HBCAD_ROOT (handbuilt-cad clone, read-only) and that clone's Python (OCP, trimesh, matplotlib, PIL, ezdxf).
        F3D_EXE (optional): F3D 4.x for the thumbnail anti-aliasing test.
Modes (tangent edges drawn in every view, the ADR-040 default):
  UHQ    exact B-rep hidden-line removal (HLRBRep_Algo); one child process per view, killed after --uhq-timeout s
  HQ     polygonal hidden-line removal (HLRBRep_PolyAlgo) on a mesh of the B-rep, pieces joined into polylines
  DRAFT  the same polygonal pass, raw 2-point pieces
  FAST   FAST DRAFT: mesh creases (faces meeting at > 25 deg) and silhouettes, visibility from a z-buffer, joined
Anti-aliasing (H40a), "before" and "after":
  before  fixed 0.2 mm / 0.5 rad mesh; polylines as they come; PNG drawn straight at its final size
  after   mesh deflection 0.02 mm on paper / sheet scale (finer as the scale grows), 0.25 rad; polylines fitted back to
          true arcs and circles where every point is within 0.02 mm; PNG drawn 3x and downsampled (Lanczos)
Every child runs with a timeout and is killed when it runs over; no child is left running.
Writes into out_dir: cache.brep, lines/*.npz, <mode>_<aa>.dxf / .png, render_modes.json, compare.png (rows = modes),
picker.png (mode-picker strip), aa_zoom.png (before / after crop), f3d_*.png.
"""
import os, sys, json, time, subprocess, threading, argparse
import numpy as np

VIEWS = ("front", "top", "right", "iso")
MODES = ("UHQ", "HQ", "DRAFT", "FAST")
PAPER_DEFL, ARC_TOL, SS = 0.02, 0.02, 3            # mm on paper; mm on the model; supersampling factor
CHILD_TIMEOUT = 1800                                 # s, for the HQ/DRAFT and FAST children
UHQ_OUTLINE_DEFL = 0.05                              # mm, mesh for the UHQ outline pass (H56 fix)
def tic(): return time.perf_counter()


# ================================================================ geometry helpers (child side)
def occ():
    sys.path.insert(0, os.path.join(os.environ["HBCAD_ROOT"], "drawing"))
    import dwg
    return dwg

def basis(name):
    dwg = occ(); cam, up = dwg.VIEWDIR[name]; return dwg.basis(cam, up)

def projector(name):
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    c, r, u = basis(name)
    return HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*c), gp_Dir(*r)))

def load_cache(out):
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepTools import BRepTools
    s = TopoDS_Shape(); BinTools.Read_s(s, os.path.join(out, "cache.brep")); BRepTools.Clean_s(s); return s

def comp_edges(comp):
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    out = []
    if comp is None or comp.IsNull(): return out
    ex = TopExp_Explorer(comp, TopAbs_EDGE)
    while ex.More(): out.append(TopoDS.Edge(ex.Current())); ex.Next()
    return out

def chain(segs, tol=1e-3):
    """Join 2-point pieces into continuous polylines through every point where exactly two pieces meet."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    adj = {}
    for i, s in enumerate(segs):
        for j in (0, 1): adj.setdefault(key(s[j]), []).append((i, j))
    used = [False] * len(segs); out = []
    def walk(i, j):
        line = [segs[i][j], segs[i][1 - j]]; used[i] = True; k = key(segs[i][1 - j])
        while len(adj[k]) == 2:
            nxt = [(a, b) for a, b in adj[k] if not used[a]]
            if not nxt: break
            a, b = nxt[0]; used[a] = True; line.append(segs[a][1 - b]); k = key(segs[a][1 - b])
        return line
    for k, ends in adj.items():
        if len(ends) != 2:
            for i, j in ends:
                if not used[i]: out.append(np.array(walk(i, j)))
    for i in range(len(segs)):
        if not used[i]: out.append(np.array(walk(i, 0)))
    return [simplify(p) for p in out]

def simplify(p, eps=1e-4):
    """Drop interior points that lie on the straight line through their neighbours (exact collinear runs only)."""
    if len(p) < 3: return p
    a, b, c = p[:-2], p[1:-1], p[2:]
    cr = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    ln = np.hypot(*(c - a).T) + 1e-12
    keep = np.r_[True, cr / ln > eps, True]
    return p[keep]

# ---- arc fitting (H40a): a polyline becomes lines + true arcs / circles where every point is within ARC_TOL
def _circle(P):
    m = P.mean(0); Q = P - m
    A = np.c_[2 * Q, np.ones(len(Q))]; b = (Q ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]; cx, cy = sol[:2]; r = np.sqrt(max(sol[2] + cx * cx + cy * cy, 0))
    return cx + m[0], cy + m[1], r

def _fits(P, tol):
    ch = P[-1] - P[0]; L = np.hypot(*ch)
    if L > 1e-9:                                                    # a straight run stays a line
        d = np.abs(ch[0] * (P[:, 1] - P[0, 1]) - ch[1] * (P[:, 0] - P[0, 0])) / L
        if d.max() <= tol: return None
    cx, cy, r = _circle(P)
    if not (r > 1e-3 and r < 1e4): return None
    if np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r).max() > tol: return None
    a = np.unwrap(np.arctan2(P[:, 1] - cy, P[:, 0] - cx)); da = np.diff(a)
    if not (np.all(da > 0) or np.all(da < 0)) or np.abs(da).max() > 0.8: return None
    if (r * (1 - np.cos(np.abs(da) / 2))).max() > tol: return None   # H54 fix: the arc between two points must
    return cx, cy, r, a[0], a[-1]                                    # stay within tol of their chord (no bowed lines)

def to_prims(P, tol=ARC_TOL, min_pts=5):
    """[('L', pts) | ('A', cx, cy, r, a0, a1) | ('C', cx, cy, r)] for one polyline."""
    n = len(P)
    if n < min_pts: return [("L", P)]
    closed = np.hypot(*(P[0] - P[-1])) < 1e-6
    if closed:
        f = _fits(P[:-1], tol)
        if f and abs(f[4] - f[3]) > 2 * np.pi * (1 - 1.5 / n): return [("C", f[0], f[1], f[2])]
    v = np.diff(P, axis=0); cr = v[:-1, 0] * v[1:, 1] - v[:-1, 1] * v[1:, 0]
    turn = np.r_[0, cr / (np.hypot(*v[:-1].T) * np.hypot(*v[1:].T) + 1e-12), 0]
    out = []; i = 0; ls = 0
    while i <= n - min_pts:
        t = turn[i + 1:i + min_pts - 1]
        if np.all(np.abs(t) > 1e-4) and (np.all(t > 0) or np.all(t < 0)) and _fits(P[i:i + min_pts], tol):
            good, step = i + min_pts - 1, 1
            while good + step < n and _fits(P[i:good + step + 1], tol): good += step; step *= 2
            hi = min(n, good + step)                               # first end known to fail (or past the end)
            while hi - good > 1:
                mid = (good + hi) // 2
                if _fits(P[i:mid + 1], tol): good = mid
                else: hi = mid
            if i > ls: out.append(("L", P[ls:i + 1]))
            f = _fits(P[i:good + 1], tol); out.append(("A",) + f); i = ls = good
        else: i += 1
    if ls < n - 1: out.append(("L", P[ls:]))
    return out

def prim_pts(p, paper_scale=1.0):
    """Points to draw one primitive; arcs are sampled finely (0.01 mm sagitta on paper, at least every 2 deg)."""
    if p[0] == "L": return p[1]
    if p[0] == "C": cx, cy, r = p[1:]; a0, a1 = 0.0, 2 * np.pi
    else: cx, cy, r, a0, a1 = p[1:]
    step = min(np.radians(2), 2 * np.arccos(max(0.0, 1 - 0.01 / max(r * paper_scale, 1e-6))))
    t = np.linspace(a0, a1, max(3, int(abs(a1 - a0) / max(step, 1e-4)) + 2))
    return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]

# ---- hidden-line removal
def _pieces(comp):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    out = []
    for e in comp_edges(comp):
        a = BRepAdaptor_Curve(e); p, q = a.Value(a.FirstParameter()), a.Value(a.LastParameter())
        out.append(np.array([[p.X(), p.Y()], [q.X(), q.Y()]]))
    return out

def poly_hlr(shape, name):
    """Visible sharp edges + outlines ('vis') and visible tangent edges ('tan'), raw 2-point pieces."""
    from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
    a = HLRBRep_PolyAlgo(); a.Load(shape); a.Projector(projector(name)); a.Update()
    h = HLRBRep_PolyHLRToShape(); h.Update(a)
    return _pieces(h.VCompound()) + _pieces(h.OutLineVCompound()), _pieces(h.Rg1LineVCompound())

def exact_hlr(shape, name):
    """UHQ: exact B-rep hidden-line removal. Returns (vis, tan) as sampled curves and the count of true arcs."""
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.GeomAbs import GeomAbs_Circle
    from OCP.BRepLib import BRepLib
    t = tic(); a = HLRBRep_Algo(); a.Add(shape); a.Projector(projector(name)); a.Update(); print("UPDATE_DONE", round(tic() - t, 1), flush=True)
    a.Hide(); print("HIDE_DONE", round(tic() - t, 1), flush=True)
    h = HLRBRep_HLRToShape(a); res = []; arcs = 0
    for comp in ((h.VCompound(), h.OutLineVCompound()), (h.Rg1LineVCompound(),)):
        lines = []
        for cp in comp:
            for e in comp_edges(cp):
                try: BRepLib.BuildCurve3d_s(e)
                except Exception: pass
                ad = BRepAdaptor_Curve(e); arcs += ad.GetType() == GeomAbs_Circle
                g = GCPnts_QuasiUniformDeflection(ad, 0.005)
                if g.IsDone() and g.NbPoints() > 1:
                    lines.append(np.array([[g.Value(i).X(), g.Value(i).Y()] for i in range(1, g.NbPoints() + 1)]))
        res.append(lines)
    # H56 fix: exact outline tracing drops the silhouettes of free-form faces (CC-500 pendant). Add the outlines of
    # the polygonal pass (visible silhouettes only) so every curved body keeps its outline; sharp and tangent edges
    # stay exact.
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
    BRepMesh_IncrementalMesh(shape, UHQ_OUTLINE_DEFL, False, 0.25, True)
    pa = HLRBRep_PolyAlgo(); pa.Load(shape); pa.Projector(projector(name)); pa.Update()
    ph = HLRBRep_PolyHLRToShape(); ph.Update(pa)
    res[0] += _pieces(ph.OutLineVCompound()); print("OUTLINES_DONE", round(tic() - t, 1), flush=True)
    return res[0], res[1], arcs

# ---- FAST DRAFT: mesh creases + silhouettes, z-buffer visibility (vectorised)
def zbuffer(tris, c, r, u, N):
    U, V, D = tris @ r, tris @ u, tris @ c
    lo = np.array([U.min(), V.min()]); k = (N - 1) / max(U.max() - lo[0], V.max() - lo[1])
    X, Y = (U - lo[0]) * k, (V - lo[1]) * k; zb = np.full(N * N, -np.inf)
    span = np.maximum(X.max(1) - X.min(1), Y.max(1) - Y.min(1)); small = np.nonzero(span <= 8)[0]; big = np.nonzero(span > 8)[0]
    s = 10; ij = np.array([(i, j) for i in range(s + 1) for j in range(s + 1 - i)], float) / s
    W = np.c_[ij, 1 - ij.sum(1)]                                   # barycentric sample weights, spacing <= 0.8 px
    for c0 in range(0, len(small), 100000):
        ix = small[c0:c0 + 100000]
        px = np.clip(np.rint(X[ix] @ W.T), 0, N - 1).astype(np.int64); py = np.clip(np.rint(Y[ix] @ W.T), 0, N - 1).astype(np.int64)
        np.maximum.at(zb, (py * N + px).ravel(), (D[ix] @ W.T).ravel())
    zb = zb.reshape(N, N)
    for i in big:
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

def mesh_lines(m, name, N, nbhd, crease_deg=25.0):
    """Creases, silhouettes and open boundaries kept where the z-buffer says they are in front. nbhd: compare against
    the farthest depth in a 3x3 pixel neighbourhood (the after-fix for outlines breaking into dashes)."""
    c, r, u = basis(name); facing = m.face_normals @ c
    fa = m.face_adjacency; ang = np.degrees(m.face_adjacency_angles)
    keep = (ang > crease_deg) | (np.sign(facing[fa[:, 0]]) != np.sign(facing[fa[:, 1]]))
    import trimesh
    E = np.vstack([m.face_adjacency_edges[keep], m.edges_sorted[trimesh.grouping.group_rows(m.edges_sorted, require_count=1)]])
    zb, lo, k = zbuffer(m.triangles, c, r, u, N)
    if nbhd:
        z = np.where(np.isinf(zb), np.inf, zb); pad = np.pad(z, 1, constant_values=np.inf)
        zb = np.min([pad[1 + dy:N + 1 + dy, 1 + dx:N + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)], axis=0)
        zb[np.isinf(zb)] = -np.inf                                   # nothing drawn there: an edge point is in front
    # H56 fix: an edge where a face turns away (silhouette, or a face seen edge-on) shares its pixels with that face's
    # nearer points, so a fixed depth tolerance hides it. Tolerance per edge = depth span of its two faces + 2.5 px.
    span = np.ptp(m.triangles @ c, axis=1); fs = np.maximum(span[fa[keep][:, 0]], span[fa[keep][:, 1]])
    tol_e = np.r_[np.minimum(fs, 20 / k), np.zeros(len(E) - len(fs))] + 2.5 / k   # capped at 20 px: no see-through
    P0, P1 = m.vertices[E[:, 0]], m.vertices[E[:, 1]]
    n = np.maximum(2, (np.linalg.norm(P1 - P0, axis=1) * k / 1.5).astype(int) + 2)
    idx = np.repeat(np.arange(len(E)), n); off = np.r_[0, np.cumsum(n)[:-1]]
    t = (np.arange(n.sum()) - off[idx]) / (n[idx] - 1)
    P = P0[idx] + t[:, None] * (P1 - P0)[idx]
    px = np.clip(np.rint((P @ r - lo[0]) * k), 0, N - 1).astype(int); py = np.clip(np.rint((P @ u - lo[1]) * k), 0, N - 1).astype(int)
    seen = (P @ c) >= zb[py, px] - tol_e[idx]
    both = seen[:-1] & seen[1:] & (idx[:-1] == idx[1:]); q = np.c_[P @ r, P @ u]
    return list(np.stack([q[:-1][both], q[1:][both]], axis=1))

# ================================================================ line files
def save_lines(path, vis, tan, prims=None):
    """vis / tan: polylines. prims (after-fix): {'vis': [...], 'tan': [...]} of to_prims() output instead."""
    d = {}
    if prims is not None:
        for key in ("vis", "tan"):
            pl, arcs, circ = [], [], []
            for plist in prims[key]:
                for p in plist:
                    if p[0] == "L": pl.append(p[1])
                    elif p[0] == "A": arcs.append(p[1:])
                    else: circ.append(p[1:])
            d[key + "_arcs"] = np.array(arcs, float).reshape(-1, 5); d[key + "_circ"] = np.array(circ, float).reshape(-1, 3)
            if key == "vis": vis = pl
            else: tan = pl
    for key, pl in (("vis", vis), ("tan", tan)):
        pl = [np.asarray(p, float) for p in pl if len(p) > 1]
        d[key + "_pts"] = np.concatenate(pl) if pl else np.zeros((0, 2)); d[key + "_n"] = np.array([len(p) for p in pl], int)
    np.savez_compressed(path, **d)

def load_lines(path):
    """{'vis': (polylines, arcs, circles), 'tan': (...)}"""
    z = np.load(path); out = {}
    for key in ("vis", "tan"):
        pts, n = z[key + "_pts"], z[key + "_n"]; cut = np.cumsum(n)[:-1]
        pl = np.split(pts, cut) if len(n) else []
        out[key] = (pl, z[key + "_arcs"] if key + "_arcs" in z else np.zeros((0, 5)), z[key + "_circ"] if key + "_circ" in z else np.zeros((0, 3)))
    return out

def count(L):
    return sum(len(L[k][0]) + len(L[k][1]) + len(L[k][2]) for k in ("vis", "tan"))


# ================================================================ child tasks
def deflection(prep, aa):
    if aa == "before": return 0.2, 0.5
    return float(np.clip(PAPER_DEFL / prep["scale"], 0.01, 0.2)), 0.25

def child_prep(step, out):
    from OCP.STEPControl import STEPControl_Reader
    from OCP.BinTools import BinTools
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
    t = tic(); rd = STEPControl_Reader(); rd.ReadFile(step); rd.TransferRoots(); s = rd.OneShape(); res = {"import_s": round(tic() - t, 1)}
    t = tic(); BinTools.Write_s(s, os.path.join(out, "cache.brep")); res["cache_s"] = round(tic() - t, 1)
    for nm, ty in (("faces", TopAbs_FACE), ("solids", TopAbs_SOLID)):
        ex = TopExp_Explorer(s, ty); n = 0
        while ex.More(): n += 1; ex.Next()
        res[nm] = n
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, False); p0, p1 = b.CornerMin(), b.CornerMax()
    x0, y0, z0, x1, y1, z1 = p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z()
    corners = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    ext = {}
    for v in VIEWS:
        c, r, u = basis(v); ext[v] = [float(np.ptp(corners @ r)), float(np.ptp(corners @ u))]
    dwg = occ(); smax = min((262 - 28) / (ext["front"][0] + ext["right"][0]), (172 - 24) / (ext["front"][1] + ext["top"][1]))
    res.update(bbox=[round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 1)], extents=ext, scale=dwg.pick_scale(smax), smax=smax)
    json.dump(res, open(os.path.join(out, "prep.json"), "w"), indent=1)

def child_uhq(out, view):
    s = load_cache(out); print("HLR_START", flush=True)
    t = tic(); vis, tan, arcs = exact_hlr(s, view); dt = tic() - t
    save_lines(os.path.join(out, "lines", f"UHQ_{view}.npz"), vis, tan)
    json.dump(dict(seconds=round(dt, 2), vis=len(vis), tan=len(tan), true_arcs=int(arcs)), open(os.path.join(out, f"uhq_{view}.json"), "w"))

def child_poly(out, aa):
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    prep = json.load(open(os.path.join(out, "prep.json"))); lin, ang = deflection(prep, aa)
    s = load_cache(out); t = tic(); BRepMesh_IncrementalMesh(s, lin, False, ang, True); res = {"mesh_s": round(tic() - t, 1), "deflection": [lin, ang], "views": {}}
    for v in VIEWS:
        t = tic(); vis, tan = poly_hlr(s, v); t_hlr = tic() - t
        save_lines(os.path.join(out, "lines", f"DRAFT_{aa}_{v}.npz"), vis, tan)
        t = tic(); cv, ct = chain(vis), chain(tan); t_chain = tic() - t; prims = None; t_fit = 0.0
        if aa == "after": t = tic(); prims = {"vis": [to_prims(p) for p in cv], "tan": [to_prims(p) for p in ct]}; t_fit = tic() - t
        save_lines(os.path.join(out, "lines", f"HQ_{aa}_{v}.npz"), cv, ct, prims)
        res["views"][v] = dict(hlr_s=round(t_hlr, 2), chain_s=round(t_chain, 2), fit_s=round(t_fit, 2), pieces=len(vis) + len(tan))
        json.dump(res, open(os.path.join(out, f"poly_{aa}.json"), "w"), indent=1)

def child_fast(out, aa):
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    import trimesh
    prep = json.load(open(os.path.join(out, "prep.json"))); lin, ang = deflection(prep, aa)
    s = load_cache(out); t = tic(); BRepMesh_IncrementalMesh(s, lin, False, ang, True); res = {"mesh_s": round(tic() - t, 1), "deflection": [lin, ang], "views": {}}
    t = tic(); stl = os.path.join(out, f"mesh_{aa}.stl"); w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(s, stl)
    m = trimesh.load(stl, force="mesh"); os.remove(stl); res["stl_s"] = round(tic() - t, 1); res["triangles"] = int(len(m.faces))
    for v in VIEWS:
        t = tic(); segs = mesh_lines(m, v, 2400, nbhd=(aa == "after")); t_z = tic() - t
        t = tic(); cv = chain(segs); t_chain = tic() - t; prims = None; t_fit = 0.0
        if aa == "after": t = tic(); prims = {"vis": [to_prims(p) for p in cv], "tan": []}; t_fit = tic() - t
        save_lines(os.path.join(out, "lines", f"FAST_{aa}_{v}.npz"), cv, [], prims)
        res["views"][v] = dict(zbuf_s=round(t_z, 2), chain_s=round(t_chain, 2), fit_s=round(t_fit, 2), pieces=len(segs))
        json.dump(res, open(os.path.join(out, f"fast_{aa}.json"), "w"), indent=1)

# ================================================================ parent: run children with timeouts
def kill_tree(p):
    """Kill a child and everything under it (a venv python.exe on Windows is a launcher with its own child)."""
    if os.name == "nt": subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    p.kill(); p.wait()

def spawn(args, out, timeout, start_marker=None, load_timeout=900):
    """Run this script as a child. With start_marker, the timeout starts when the child prints it (after loading).
    Returns (status, seconds). The child is killed when it runs over; never left running."""
    cmd = [sys.executable, os.path.abspath(__file__), "--child"] + args + ["--out", out]
    log = open(os.path.join(out, "child_" + args[0] + ("" if args[0] == "prep" else "_" + args[1]) + ".log"), "w")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log, text=True, bufsize=1)
    started = threading.Event()
    def reader():
        for line in p.stdout:
            log.write(line); log.flush()
            if start_marker and start_marker in line: started.set()
    th = threading.Thread(target=reader, daemon=True); th.start(); t0 = tic(); status = "ok"
    try:
        if start_marker:
            while not started.is_set():
                if p.poll() is not None: break
                if tic() - t0 > load_timeout: raise subprocess.TimeoutExpired(cmd, load_timeout)
                time.sleep(0.2)
            t1 = tic(); p.wait(timeout=timeout); dt = tic() - t1
        else:
            p.wait(timeout=timeout); dt = tic() - t0
        if p.returncode: status = f"failed (exit {p.returncode})"
    except subprocess.TimeoutExpired:
        kill_tree(p); status = "timed out"; dt = timeout
    th.join(5); log.close()
    return status, round(dt, 1)


# ================================================================ parent: drawing the results
def to_draw(L, paper=1.0):
    """[(points, is_tangent)] for drawing: polylines plus sampled arcs and circles."""
    out = []
    for key in ("vis", "tan"):
        pl, arcs, circ = L[key]
        out += [(p, key == "tan") for p in pl]
        out += [(prim_pts(("A",) + tuple(a), paper), key == "tan") for a in arcs]
        out += [(prim_pts(("C",) + tuple(c), paper), key == "tan") for c in circ]
    return out

def draw(ax, items, xf=lambda p: p, lw=0.5, lwt=0.3):
    from matplotlib.collections import LineCollection
    for tanflag, w in ((False, lw), (True, lwt)):
        segs = [xf(p) for p, t in items if t == tanflag and len(p) > 1]
        if segs: ax.add_collection(LineCollection(segs, colors="k", linewidths=w, capstyle="round", joinstyle="round"))

def save_png(fig, path, dpi, aa):
    """before: drawn at the final size. after: drawn SS times larger, then Lanczos-downsampled to the final size."""
    import matplotlib.pyplot as plt
    from PIL import Image
    if aa == "before": fig.savefig(path, dpi=dpi)
    else:
        tmp = path + ".ss.png"; fig.savefig(tmp, dpi=dpi * SS); im = Image.open(tmp); w, h = im.size
        im.convert("RGB").resize((round(w / SS), round(h / SS)), Image.LANCZOS).save(path, optimize=True); im.close(); os.remove(tmp)
    plt.close(fig)

def row_time(T, m):
    cells = [T[f"{m}_after"][v] for v in VIEWS]; ok = [c for c in cells if c.get("status") == "ok"]
    txt = f"{sum(c['seconds'] for c in ok):.1f} s for {len(ok)} of 4 views"
    to = sum(c.get("status") == "timed out" for c in cells)
    return txt + (f"; {to} timed out" if to else "")

def bounds(items):
    P = np.concatenate([p for p, _ in items]) if items else np.zeros((1, 2)); return P.min(0), P.max(0)

def layout(b, s):
    """Third-angle placement on a B sheet (mm): front lower left, top above, right beside it, iso upper right.
    b: {view: (lo, hi)} model-space bounds of a reference mode, so every mode lands in the same place."""
    PW, PH, g = 431.8, 279.4, 20
    sz = {v: (b[v][1] - b[v][0]) * s for v in b}; fw, fh = sz.get("front", (0, 0))
    ctr = {"front": (24 + fw / 2, 30 + fh / 2)}
    if "top" in sz: ctr["top"] = (ctr["front"][0], 30 + fh + g + sz["top"][1] / 2)
    if "right" in sz: ctr["right"] = (24 + fw + g + sz["right"][0] / 2, ctr["front"][1])
    if "iso" in sz: ctr["iso"] = (PW - 20 - sz["iso"][0] / 2, PH - 20 - sz["iso"][1] / 2)
    return {v: (lambda p, v=v: (np.asarray(p) - (b[v][0] + b[v][1]) / 2) * s + ctr[v]) for v in b if v in ctr}

def write_dxf(path, view_items, xfs, raw):
    import ezdxf
    doc = ezdxf.new("R2010"); msp = doc.modelspace(); doc.layers.add("TANGENT")
    for v, L in raw.items():
        xf = xfs[v]; sc = xf(np.array([1.0, 0.0])) - xf(np.array([0.0, 0.0])); s = float(sc[0])
        for key in ("vis", "tan"):
            at = {"layer": "TANGENT"} if key == "tan" else {}
            pl, arcs, circ = L[key]
            for p in pl:
                q = xf(p)
                if len(q) == 2: msp.add_line(tuple(q[0]), tuple(q[1]), dxfattribs=at)
                else: msp.add_lwpolyline([tuple(x) for x in q], dxfattribs=at)
            for cx, cy, r, a0, a1 in arcs:
                cc = xf(np.array([cx, cy])); lo, hi = sorted((a0, a1))
                msp.add_arc(tuple(cc), r * s, np.degrees(lo), np.degrees(hi), dxfattribs=at)
            for cx, cy, r in circ: msp.add_circle(tuple(xf(np.array([cx, cy]))), r * s, dxfattribs=at)
    doc.saveas(path)

# ================================================================ parent: main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("step", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--modes", default=",".join(MODES)); ap.add_argument("--uhq-timeout", type=float, default=120)
    ap.add_argument("--title", default=""); ap.add_argument("--child", nargs="+"); ap.add_argument("--skip-run", action="store_true")
    a, _ = ap.parse_known_args()
    if a.child:
        out = sys.argv[sys.argv.index("--out") + 1]; task = a.child
        if task[0] == "prep": child_prep(task[1], out)
        elif task[0] == "uhq": child_uhq(out, task[1])
        elif task[0] == "poly": child_poly(out, task[1])
        elif task[0] == "fast": child_fast(out, task[1])
        return
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    out = a.out; os.makedirs(os.path.join(out, "lines"), exist_ok=True); modes = a.modes.split(",")
    title = a.title or os.path.splitext(os.path.basename(a.step))[0]; JS = os.path.join(out, "render_modes.json")
    res = json.load(open(JS)) if a.skip_run and os.path.isfile(JS) else {"model": title, "step_mb": round(os.path.getsize(a.step) / 1e6, 1), "runs": {}}
    def save(): json.dump(res, open(JS, "w"), indent=1)
    if not a.skip_run:
        res["runs"]["prep"] = spawn(["prep", a.step], out, 1800); res["prep"] = json.load(open(os.path.join(out, "prep.json"))); save()
        if "UHQ" in modes:
            for v in VIEWS:
                res["runs"][f"UHQ_{v}"] = spawn(["uhq", v], out, a.uhq_timeout, start_marker="HLR_START"); save()
        for aa in ("before", "after"):
            if "HQ" in modes or "DRAFT" in modes: res["runs"][f"poly_{aa}"] = spawn(["poly", aa], out, CHILD_TIMEOUT); save()
            if "FAST" in modes: res["runs"][f"fast_{aa}"] = spawn(["fast", aa], out, CHILD_TIMEOUT); save()
    prep = res["prep"]; s = prep["scale"]; dwg = occ()
    # ---- collect per mode / aa / view: seconds, lines, and the line data
    T = {}; data = {}
    for m in modes:
        for aa in ("before", "after"):
            row = {}; data[(m, aa)] = {}
            for v in VIEWS:
                f = os.path.join(out, "lines", f"UHQ_{v}.npz" if m == "UHQ" else f"{m}_{aa}_{v}.npz"); cell = {}
                if m == "UHQ":
                    st = res["runs"].get(f"UHQ_{v}", ["not run", 0]); cell["status"] = st[0]
                    j = os.path.join(out, f"uhq_{v}.json")
                    if st[0] == "ok" and os.path.isfile(j): cell.update(json.load(open(j)))
                    else: cell["seconds"] = st[1]
                else:
                    jn = os.path.join(out, ("fast_" if m == "FAST" else "poly_") + aa + ".json")
                    J = json.load(open(jn)) if os.path.isfile(jn) else {"views": {}}; jv = J["views"].get(v)
                    if jv is None: cell.update(status="missing", seconds=None)
                    else:
                        base = jv["zbuf_s"] if m == "FAST" else jv["hlr_s"]
                        cell.update(status="ok", seconds=round(base + (0 if m == "DRAFT" else jv["chain_s"] + jv["fit_s"]), 2))
                    cell["mesh_s"] = J.get("mesh_s"); cell["deflection"] = J.get("deflection"); cell["triangles"] = J.get("triangles")
                if os.path.isfile(f) and cell["status"] == "ok":
                    L = load_lines(f); data[(m, aa)][v] = L; cell["lines"] = count(L)
                    cell["arcs"] = int(sum(len(L[k][1]) for k in ("vis", "tan"))); cell["circles"] = int(sum(len(L[k][2]) for k in ("vis", "tan")))
                row[v] = cell
            T[f"{m}_{aa}"] = row
    res["table"] = T; save()

    # ---- per mode and aa: one B-size sheet PNG (150 dpi) and DXF of the four views at the sheet scale
    files = {}; ref = {}
    for key in (("HQ", "after"), ("DRAFT", "before"), ("FAST", "after"), ("UHQ", "after")):
        for v, L in data.get(key, {}).items(): ref.setdefault(v, bounds(to_draw(L, s)))
    XF = layout(ref, s)
    for (m, aa), views in data.items():
        if not views: continue
        items = {v: to_draw(L, s) for v, L in views.items()}; xfs = XF
        fig = plt.figure(figsize=(17, 11)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 431.8); ax.set_ylim(0, 279.4); ax.axis("off")
        ax.plot([8, 423.8, 423.8, 8, 8], [8, 8, 271.4, 271.4, 8], "k-", lw=0.7)
        for v, it in items.items():
            if v in xfs: draw(ax, it, xfs[v], lw=0.99, lwt=0.51)       # 0.35 mm visible, 0.18 mm tangent
        ax.text(14, 14, f"{title}  |  {m}  |  anti-aliasing {aa}  |  scale {dwg.scale_str(s)}  |  render test, not a drawing", fontsize=8)
        png = os.path.join(out, f"{m}_{aa}.png"); t = tic(); save_png(fig, png, 150, aa); t_png = tic() - t
        dxf = os.path.join(out, f"{m}_{aa}.dxf"); t = tic(); write_dxf(dxf, items, xfs, views); t_dxf = tic() - t
        files[f"{m}_{aa}"] = dict(png_kb=round(os.path.getsize(png) / 1024), dxf_kb=round(os.path.getsize(dxf) / 1024), png_s=round(t_png, 1), dxf_s=round(t_dxf, 1))
    res["files"] = files; save()

    # ---- compare.png: rows = modes (after-fix lines), columns = views, timings in each cell
    fig, axs = plt.subplots(len(modes), 4, figsize=(17, 4.0 * len(modes) + 0.8), squeeze=False)
    for i, m in enumerate(modes):
        for j, v in enumerate(VIEWS):
            ax = axs[i][j]; ax.set_aspect("equal"); ax.axis("off"); ca, cb = T[f"{m}_after"][v], T[f"{m}_before"][v]
            L = data[(m, "after")].get(v)
            if L is not None:
                it = to_draw(L, s); draw(ax, it, lw=0.45, lwt=0.25); lo, hi = bounds(it); pad = (hi - lo).max() * 0.03
                ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
                txt = f"{m} {v.upper()}: {ca['seconds']} s, {ca['lines']} lines"
                if m != "UHQ": txt += f"\n(before fix {cb.get('seconds')} s, {cb.get('lines')} lines)"
                else: txt += f", {ca.get('true_arcs', 0)} true arcs"
            else:
                txt = f"{m} {v.upper()}: {ca.get('status')} ({ca.get('seconds')} s)"
                ax.text(0.5, 0.5, ca.get("status", "").upper(), ha="center", va="center", fontsize=14, color="0.5", transform=ax.transAxes)
            ax.set_title(txt, fontsize=8, loc="left")
        axs[i][0].text(-0.02, 0.5, f"{m}\n{row_time(T, m)}", transform=axs[i][0].transAxes, rotation=90, ha="right", va="center", fontsize=11, fontweight="bold")
    fig.suptitle(f"Render modes on {title}  ({prep['solids']} solids, {prep['faces']} faces, STEP {res['step_mb']} MB, sheet scale {dwg.scale_str(s)}); "
                 f"UHQ timeout {a.uhq_timeout:g} s per view; tangent edges drawn", fontsize=10)
    fig.tight_layout(rect=(0.02, 0, 1, 0.97)); save_png(fig, os.path.join(out, "compare.png"), 110, "after")

    # ---- picker.png: the mode-picker strip (trimetric of each mode)
    fig, axs = plt.subplots(1, len(modes), figsize=(2.4 * len(modes), 2.0), squeeze=False)
    for ax, m in zip(axs[0], modes):
        ax.set_aspect("equal"); ax.axis("off"); got = data[(m, "after")]
        v = "iso" if "iso" in got else next((x for x in VIEWS if x in got), None)
        if v: it = to_draw(got[v], s); draw(ax, it, lw=0.3, lwt=0.18); lo, hi = bounds(it); ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1])
        else: ax.text(0.5, 0.5, "timed out", ha="center", va="center", transform=ax.transAxes, color="0.5")
        ax.set_title(f"{m.replace('FAST', 'FAST DRAFT')}" + (f" ({v})" if v and v != "iso" else "") + f"\n{row_time(T, m)}", fontsize=8, fontweight="bold")
    fig.tight_layout(); save_png(fig, os.path.join(out, "picker.png"), 150, "after")

    # ---- aa_zoom.png: the same 30 x 20 mm sheet window around a circle, HQ before vs after (and UHQ when it finished)
    from PIL import Image, ImageDraw
    hq = data.get(("HQ", "after"), {})
    if hq:
        nc = {v: len(L["vis"][1]) + len(L["vis"][2]) for v, L in hq.items()}; zv = max(nc, key=nc.get); L = hq[zv]
        A = np.r_[L["vis"][1][:, :2], L["vis"][2][:, :2]] if nc[zv] else np.concatenate(L["vis"][0])
        A = XF[zv](A); med = np.median(A, axis=0); cx, cy = A[np.argmin(np.hypot(*(A - med).T))]   # a real circle near the middle
        W, H = 30, 20; tiles = []; res["aa_zoom"] = dict(view=zv, centre_mm=[round(float(cx), 1), round(float(cy), 1)], window_mm=[W, H])
        for name in ("HQ_before", "HQ_after", "UHQ_after"):
            p = os.path.join(out, name + ".png")
            if not os.path.isfile(p) or (name.startswith("UHQ") and zv not in data.get(("UHQ", "after"), {})): continue
            im = Image.open(p); iw, ih = im.size; kx, ky = iw / 431.8, ih / 279.4
            box = (int((cx - W / 2) * kx), int(ih - (cy + H / 2) * ky), int((cx + W / 2) * kx), int(ih - (cy - H / 2) * ky))
            t = im.crop(box).resize(((box[2] - box[0]) * 4, (box[3] - box[1]) * 4), Image.NEAREST).convert("RGB")
            ImageDraw.Draw(t).text((8, 8), name.replace("_", " ") + f" ({zv} view, 150 dpi, pixels shown 4x)", fill=(200, 0, 0)); tiles.append(t)
        if tiles:
            pg = Image.new("RGB", (sum(t.size[0] for t in tiles) + 10 * (len(tiles) - 1), max(t.size[1] for t in tiles)), "white"); x = 0
            for t in tiles: pg.paste(t, (x, 0)); x += t.size[0] + 10
            pg.save(os.path.join(out, "aa_zoom.png"))

    # ---- F3D thumbnail of the whole model, without and with --anti-aliasing=ssaa
    F3D = os.environ.get("F3D_EXE", "")
    if os.path.isfile(F3D):
        res["f3d"] = {}
        for aa, extra in (("none", []), ("ssaa", ["--anti-aliasing=ssaa"])):
            png = os.path.join(out, f"f3d_{aa}.png"); t = tic()
            try:
                r = subprocess.run([F3D, a.step, "--output", png, "--resolution=600,600", "--no-background", "--grid=false", "--axis=false",
                                    "--filename=false", "--edges", "--up=+Z", "--camera-direction=-1,1.55,-1.15", "--camera-orthographic"] + extra,
                                   capture_output=True, encoding="utf-8", errors="replace", timeout=600)
                ok = r.returncode == 0 and os.path.isfile(png)
                res["f3d"][aa] = dict(ok=ok, seconds=round(tic() - t, 1), kb=round(os.path.getsize(png) / 1024) if ok else None, err=None if ok else r.stderr[-200:])
            except subprocess.TimeoutExpired:
                res["f3d"][aa] = dict(ok=False, seconds=600, err="timed out")
            save()
        a0, a1 = os.path.join(out, "f3d_none.png"), os.path.join(out, "f3d_ssaa.png")
        if os.path.isfile(a0) and os.path.isfile(a1):                   # f3d_zoom.png: the middle 150 px, shown 4x
            tiles = []
            for p, lab in ((a0, "F3D no anti-aliasing"), (a1, "F3D --anti-aliasing=ssaa")):
                im = Image.open(p).convert("RGBA"); bg = Image.new("RGBA", im.size, "white"); bg.alpha_composite(im); w, h = im.size
                t = bg.convert("RGB").crop((w // 2 - 75, h // 2 - 75, w // 2 + 75, h // 2 + 75)).resize((600, 600), Image.NEAREST)
                ImageDraw.Draw(t).text((8, 8), lab + " (pixels shown 4x)", fill=(200, 0, 0)); tiles.append(t)
            pg = Image.new("RGB", (1210, 600), "white"); pg.paste(tiles[0], (0, 0)); pg.paste(tiles[1], (610, 0)); pg.save(os.path.join(out, "f3d_zoom.png"))
    save(); print(json.dumps({k: res[k] for k in ("model", "runs", "files") if k in res}, indent=1))


if __name__ == "__main__":
    main()
