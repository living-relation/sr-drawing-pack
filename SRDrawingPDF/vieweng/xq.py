"""XQ exact lines: real STEP edges, visibility from a GPU depth buffer.

Ported from sr-drawing-pack research/render-tests/xq_render.py (ADR-051, ADR-052).
Needs OCP, VTK and numpy. Without them the engine reports that it cannot run.

Visible edges only: tangent edges are thin solid lines, never dashes. Short
breaks in a visible run are closed. Trimetric round edges that are ellipses
are fitted as ellipses. A STEP file is read once and cached by its hash.
"""
import os

from sheet2d.engines.curves import bridge_gaps, fit_chain

PAPER_PX = 0.02
PAPER_DEFL = 0.02
SMOOTH_DEG = 30.0


class XqEngine(object):
    name = 'xq'
    label = 'XQ exact lines'

    def available(self):
        missing = [name for name in ('numpy', 'vtk', 'OCP') if not _imports(name)]
        if missing:
            return False, 'XQ needs %s' % ', '.join(missing)
        return True, ''

    def project_view(self, name, parts=None, step=None, **opts):
        views, _timing = self.project_views((name,), step=step, **opts)
        return views[name]

    def project_views(self, names, parts=None, step=None, **opts):
        ok, why = self.available()
        if not ok:
            raise RuntimeError(why)
        if not step:
            raise ValueError('the XQ engine reads a STEP file')
        mode = opts.get('mode') or 'exact'
        if mode not in ('exact', 'quick'):
            raise ValueError('XQ mode must be exact or quick')
        return _render(step, tuple(names), workers=opts.get('workers'), mode=mode)


def _imports(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def cache_dir():
    folder = os.environ.get('SRDP_CACHE') or os.path.join(
        os.path.expanduser('~'), '.cache', 'sr-drawing-pdf', 'xq')
    os.makedirs(folder, exist_ok=True)
    return folder


def _hash(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_shape(step):
    """(shape, seconds, from_step). The second call reads the cached brep."""
    import time
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape
    t0 = time.perf_counter()
    cache = os.path.join(cache_dir(), _hash(step) + '.brep')
    if os.path.isfile(cache):
        shape = TopoDS_Shape()
        BinTools.Read_s(shape, cache)
        return shape, time.perf_counter() - t0, False
    from OCP.STEPControl import STEPControl_Reader
    reader = STEPControl_Reader()
    reader.ReadFile(step)
    reader.TransferRoots()
    shape = reader.OneShape()
    tmp = cache + '.%d.tmp' % os.getpid()
    BinTools.Write_s(shape, tmp)
    os.replace(tmp, cache)
    return shape, time.perf_counter() - t0, True


def _render(step, names, workers=None, mode='exact'):
    import time
    import numpy as np
    from sheet2d.project import _basis
    t0 = time.perf_counter()
    shape, read_s, from_step = load_shape(step)
    lo, hi = _bbox(shape)
    # Depth pixels follow the sheet scale the mesh views would pick, about 0.02 mm on paper.
    scale = _rough_scale(lo, hi, names)
    defl = PAPER_DEFL / max(scale, 1e-6)
    size = float(np.linalg.norm(hi - lo))
    fit = mode != 'quick'
    res = int(min(8192, max(512, (size * scale) / PAPER_PX)))
    if mode == 'quick':
        res = min(res, 2048)
    step_len = 0.7 * size / res
    t_mesh = time.perf_counter()
    V, F, CN = _mesh_arrays(shape, defl)
    mesh_s = time.perf_counter() - t_mesh
    t_edge = time.perf_counter()
    points, counts, tangent = _edges(shape, defl, step_len, workers)
    edge_s = time.perf_counter() - t_edge
    depth = _Depth(V, F)
    views = {}
    per = {}
    corners = _corners(lo, hi)
    for name in names:
        tv = time.perf_counter()
        toward, right, up = _basis(name)
        c = np.array(toward, float)
        r = np.array(right, float)
        u = np.array(up, float)
        ext_r = float(np.ptp(corners @ r))
        ext_u = float(np.ptp(corners @ u))
        zb, to_win, dz, px = depth.render(c, r, u, ext_r, ext_u, res)
        lines = _view_lines(V, F, CN, points, counts, tangent, c, r, u, zb, to_win, dz, px, defl, name, fit)
        us = [p[0] for line in lines for p in _pts_of(line)]
        vs = [p[1] for line in lines for p in _pts_of(line)]
        if not us:
            us = list(corners @ r)
            vs = list(corners @ u)
        views[name] = {
            'name': name,
            'lines': lines,
            'extent': (min(us), max(us), min(vs), max(vs)),
            'seconds': time.perf_counter() - tv,
        }
        per[name] = round(views[name]['seconds'], 3)
    timing = {
        'engine': 'xq',
        'read_s': round(read_s, 3),
        'from_step': from_step,
        'mesh_s': round(mesh_s, 3),
        'edges_s': round(edge_s, 3),
        'views_s': round(sum(v['seconds'] for v in views.values()), 3),
        'total_s': round(time.perf_counter() - t0, 3),
        'per_view': per,
        'res': res,
    }
    return views, timing


def _pts_of(line):
    if line['kind'] == 'poly':
        return line['pts']
    if line['kind'] == 'circle':
        c, r = line['c'], line['r']
        return [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]
    if line['kind'] == 'ellipse':
        c, rx, ry = line['c'], line['rx'], line['ry']
        return [(c[0] - rx, c[1] - ry), (c[0] + rx, c[1] + ry)]
    return []


def _bbox(shape):
    import numpy as np
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box, True)
    p, q = box.CornerMin(), box.CornerMax()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def _corners(lo, hi):
    import numpy as np
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


def _rough_scale(lo, hi, names):
    """A sheet-like scale so the depth buffer is about 0.02 mm on paper. Not the sheet layout."""
    import numpy as np
    from sheet2d.project import _basis
    corners = _corners(lo, hi)
    span = 1.0
    for name in names:
        _c, right, up = _basis(name)
        r = np.array(right, float)
        u = np.array(up, float)
        span = max(span, float(np.ptp(corners @ r)), float(np.ptp(corners @ u)))
    # Size B has about 380 mm of width for the views.
    return min(1.0, 380.0 / span)


def _mesh(shape, defl):
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    BRepMesh_IncrementalMesh(shape, defl, False, 0.25, True)


def _mesh_arrays(shape, defl):
    import os
    import tempfile
    import numpy as np
    from OCP.StlAPI import StlAPI_Writer
    _mesh(shape, defl)
    path = os.path.join(tempfile.gettempdir(), 'xq_%d.stl' % os.getpid())
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    writer.Write(shape, path)
    dt = np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    with open(path, 'rb') as handle:
        handle.seek(80)
        n = int(np.frombuffer(handle.read(4), '<u4')[0])
        rec = np.frombuffer(handle.read(n * 50), dt)
    try:
        os.remove(path)
    except OSError:
        pass
    tri = np.ascontiguousarray(rec['v'])
    V = tri.reshape(-1, 3)
    key = np.ascontiguousarray(V).view(np.dtype((np.void, 12))).ravel()
    _uniq, first, inv = np.unique(key, return_index=True, return_inverse=True)
    verts = V[first]
    faces = inv.reshape(-1, 3)
    raw = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]).astype(np.float64)
    return verts, faces, _corner_normals(faces, raw)


def _corner_normals(faces, raw):
    import numpy as np
    unit = raw / (np.linalg.norm(raw, axis=1, keepdims=True) + 1e-30)
    corners = faces.ravel()
    tri = np.repeat(np.arange(len(faces)), 3)
    order = np.argsort(corners, kind='stable')
    corners, tri = corners[order], tri[order]
    starts = np.r_[0, np.nonzero(corners[1:] != corners[:-1])[0] + 1]
    out = np.zeros((len(corners), 3))
    cos_t = np.cos(np.radians(SMOOTH_DEG))
    for begin, end in zip(starts, np.r_[starts[1:], len(corners)]):
        ids = tri[begin:end]
        normals = unit[ids]
        weights = raw[ids]
        near = normals @ normals.T > cos_t
        out[begin:end] = near.astype(float) @ weights
    out /= np.linalg.norm(out, axis=1, keepdims=True) + 1e-30
    cn = np.zeros((len(faces), 3, 3))
    slot = np.tile(np.arange(3), len(faces))[order]
    cn[tri, slot] = out
    return cn


def _edges(shape, defl, step, workers):
    import numpy as np
    count = _edge_count(shape)
    cache = _write_temp_brep(shape)
    workers = max(1, min(workers or 1, max(1, count // 400)))
    bounds = [int(v) for v in np.linspace(0, count, workers + 1)]
    jobs = [(cache, bounds[i], bounds[i + 1], defl, step) for i in range(workers)]
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        pool = ProcessPoolExecutor(workers)
        parts = list(pool.map(_sample_edges, jobs))
        pool.shutdown()
    else:
        parts = [_sample_edges(job) for job in jobs]
    try:
        os.remove(cache)
    except OSError:
        pass
    if not parts or all(len(p[1]) == 0 for p in parts):
        return np.zeros((0, 3)), np.zeros(0, int), np.zeros(0, bool)
    return (np.concatenate([p[0] for p in parts]),
            np.concatenate([p[1] for p in parts]).astype(int),
            np.concatenate([p[2] for p in parts]).astype(bool))


def _write_temp_brep(shape):
    import tempfile
    from OCP.BinTools import BinTools
    path = os.path.join(tempfile.gettempdir(), 'xq_edges_%d.brep' % os.getpid())
    BinTools.Write_s(shape, path)
    return path


def _edge_count(shape):
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.collections import (
        IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as Map,
    )
    mapped = Map()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, mapped)
    return mapped.Extent()


def _cast(mod, name):
    return getattr(mod, name + '_s', None) or getattr(mod, name)


def _sample_edges(args):
    """Worker: sample edges [i0, i1). Tangent edges are flagged, not dashed."""
    import numpy as np
    cache, i0, i1, defl, step = args
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepLib import BRepLib
    from OCP.BinTools import BinTools
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_G1, GeomAbs_Line
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS, TopoDS_Shape
    from OCP.collections import (
        IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as Map,
    )
    shape = TopoDS_Shape()
    BinTools.Read_s(shape, cache)
    mapped = Map()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, mapped)
    pts, counts, tangent = [], [], []
    for index in range(i0 + 1, min(i1, mapped.Extent()) + 1):
        edge = _cast(TopoDS, 'Edge')(mapped.FindKey(index))
        if BRep_Tool.Degenerated_s(edge):
            continue
        faces = [_cast(TopoDS, 'Face')(face) for face in mapped.FindFromIndex(index)]
        if len(faces) == 1 and BRep_Tool.IsClosed_s(edge, faces[0]):
            continue
        is_tan = False
        if len(faces) >= 2:
            if faces[0].IsSame(faces[1]) and BRep_Tool.IsClosed_s(edge, faces[0]):
                continue
            try:
                BRepLib.EncodeRegularity_s(edge, faces[0], faces[1], 0.01)
                is_tan = int(BRep_Tool.Continuity_s(edge, faces[0], faces[1])) >= int(GeomAbs_G1)
            except Exception:
                is_tan = False
        try:
            curve = BRepAdaptor_Curve(edge)
            kind = curve.GetType()
            if kind == GeomAbs_Line:
                p = curve.Value(curve.FirstParameter())
                q = curve.Value(curve.LastParameter())
                sampled = np.array([[p.X(), p.Y(), p.Z()], [q.X(), q.Y(), q.Z()]])
            elif kind == GeomAbs_Circle:
                circle = curve.Circle()
                ax = circle.Position()
                origin = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
                xd = np.array([ax.XDirection().X(), ax.XDirection().Y(), ax.XDirection().Z()])
                yd = np.array([ax.YDirection().X(), ax.YDirection().Y(), ax.YDirection().Z()])
                radius = circle.Radius()
                u0, u1 = curve.FirstParameter(), curve.LastParameter()
                da = 2 * np.arccos(max(-1.0, 1 - defl / max(radius, 1e-9))) if radius > defl else np.pi / 4
                params = np.linspace(u0, u1, max(3, int(np.ceil(abs(u1 - u0) / max(da, 1e-3))) + 1))
                sampled = origin + radius * (np.cos(params)[:, None] * xd + np.sin(params)[:, None] * yd)
            else:
                deflect = GCPnts_QuasiUniformDeflection(curve, defl)
                if not deflect.IsDone() or deflect.NbPoints() < 2:
                    continue
                sampled = np.array([
                    [deflect.Value(j).X(), deflect.Value(j).Y(), deflect.Value(j).Z()]
                    for j in range(1, deflect.NbPoints() + 1)])
        except Exception:
            continue
        dense = _densify(sampled, step)
        pts.append(dense)
        counts.append(len(dense))
        tangent.append(is_tan)
    if not pts:
        return np.zeros((0, 3)), np.zeros(0, int), np.zeros(0, bool)
    return np.concatenate(pts), np.array(counts), np.array(tangent)


def _densify(points, step):
    import numpy as np
    delta = np.linalg.norm(np.diff(points, axis=0), axis=1)
    pieces = np.maximum(1, np.ceil(delta / max(step, 1e-9)).astype(int))
    if pieces.max() == 1:
        return points
    index = np.repeat(np.arange(len(pieces)), pieces)
    k = np.arange(pieces.sum()) - np.repeat(np.cumsum(pieces) - pieces, pieces) + 1
    frac = (k / pieces[index])[:, None]
    return np.vstack([points[:1], points[index] + (points[index + 1] - points[index]) * frac])


def _offscreen_window():
    """A depth window that does not need a screen.

    The pip VTK build opens an X window by default. A check machine has no
    display, and that window crashes. OSMesa draws on the CPU instead.
    """
    import vtk
    if hasattr(vtk, 'vtkOSOpenGLRenderWindow'):
        win = vtk.vtkOSOpenGLRenderWindow()
    else:
        win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    return win


class _Depth(object):
    def __init__(self, verts, faces):
        import numpy as np
        import vtk
        from vtk.util import numpy_support as ns
        self.vtk = vtk
        self.np = np
        points = vtk.vtkPoints()
        points.SetData(ns.numpy_to_vtk(verts.astype(np.float32), deep=True))
        cells = vtk.vtkCellArray()
        offsets = np.arange(0, 3 * len(faces) + 1, 3, dtype=np.int64)
        cells.SetData(ns.numpy_to_vtkIdTypeArray(offsets, deep=True),
                      ns.numpy_to_vtkIdTypeArray(faces.astype(np.int64).ravel(), deep=True))
        data = vtk.vtkPolyData()
        data.SetPoints(points)
        data.SetPolys(cells)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(data)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(actor)
        self.win = _offscreen_window()
        self.win.AddRenderer(self.ren)
        self.center = (verts.min(0) + verts.max(0)) / 2
        self.radius = float(np.linalg.norm(verts.max(0) - verts.min(0)) / 2 + 1e-6)

    def render(self, toward, right, up, ext_r, ext_u, res):
        import numpy as np
        vtk = self.vtk
        longest = max(ext_r, ext_u, 1e-6)
        width = max(32, int(res * min(1.0, ext_r / longest)))
        height = max(32, int(res * min(1.0, ext_u / longest)))
        self.win.SetSize(width, height)
        cam = self.ren.GetActiveCamera()
        cam.ParallelProjectionOn()
        cam.SetFocalPoint(*self.center)
        cam.SetPosition(*(self.center + toward * 4 * self.radius))
        cam.SetViewUp(*up)
        cam.SetParallelScale(max(ext_u, ext_r * height / width) / 2 * 1.04)
        cam.SetClippingRange(2 * self.radius, 6 * self.radius)
        self.win.Render()
        zbuf = vtk.vtkFloatArray()
        self.win.GetZbufferData(0, 0, width - 1, height - 1, zbuf)
        from vtk.util import numpy_support as ns
        image = ns.vtk_to_numpy(zbuf).reshape(height, width).copy()
        matrix = cam.GetCompositeProjectionTransformMatrix(width / float(height), -1, 1)
        M = np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])

        def to_win(pts):
            hom = np.c_[pts, np.ones(len(pts))] @ M.T
            ndc = hom[:, :3] / hom[:, 3:4]
            return ((ndc[:, 0] + 1) / 2 * width - 0.5,
                    (ndc[:, 1] + 1) / 2 * height - 0.5,
                    (ndc[:, 2] + 1) / 2)

        dz = 1.0 / (4 * self.radius)
        px = 2 * cam.GetParallelScale() / height
        return image, to_win, dz, px


def _visible(points, image, to_win, tol):
    import numpy as np
    height, width = image.shape
    x, y, z = to_win(points)
    xi = np.clip(np.rint(x).astype(int), 0, width - 1)
    yi = np.clip(np.rint(y).astype(int), 0, height - 1)
    best = np.zeros(len(points))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            best = np.maximum(best, image[np.clip(yi + dy, 0, height - 1), np.clip(xi + dx, 0, width - 1)])
    return z <= best + tol


def _runs(points2d, keep, counts):
    """Visible runs. Hidden gaps of up to 8 samples are closed so a line does not break into dashes."""
    import numpy as np
    if not len(counts):
        return []
    edge = np.repeat(np.arange(len(counts)), counts)
    keep = keep.copy()
    change = np.r_[True, (keep[1:] != keep[:-1]) | (edge[1:] != edge[:-1])]
    starts = np.nonzero(change)[0]
    ends = np.r_[starts[1:], len(keep)]
    length = ends - starts
    value = keep[starts]
    which = edge[starts]
    prev_ok = np.r_[False, value[:-1] & (which[:-1] == which[1:])]
    next_ok = np.r_[value[1:] & (which[1:] == which[:-1]), False]
    fill = ~value & (length <= 8) & prev_ok & next_ok
    for a, b in zip(starts[fill], ends[fill]):
        keep[a:b] = True
    change = np.r_[True, (keep[1:] != keep[:-1]) | (edge[1:] != edge[:-1])]
    starts = np.nonzero(change)[0]
    ends = np.r_[starts[1:], len(keep)]
    out = []
    for a, b in zip(starts, ends):
        if keep[a] and b - a >= 2:
            out.append(points2d[a:b])
    return out


def _view_lines(verts, faces, corners, points, counts, tangent, toward, right, up, image, to_win, dz, px, defl, name, fit):
    import numpy as np
    lines = []
    if len(counts):
        tol = dz * (2.5 * px + defl)
        keep = _visible(points, image, to_win, tol)
        flat = np.c_[points @ right, points @ up]
        for flag, style in ((False, 'vis'), (True, 'thin')):
            mask = tangent == flag
            if not mask.any():
                continue
            index = np.nonzero(np.repeat(mask, counts))[0]
            runs = _runs(flat[index], keep[index], counts[mask])
            # Close breaks of about two pixels. Back edges stay out: they were not kept.
            bridged = bridge_gaps([[(float(x), float(y)) for x, y in run] for run in runs], 2.0 * px)
            for poly in bridged:
                if len(poly) < 2:
                    continue
                item = fit_chain(poly, style, ellipses=(fit and name == 'trimetric' and style == 'vis'))
                if item and _length(item) >= 1.5 * px:
                    lines.append(item)
    sil = _silhouettes(verts, faces, corners, toward)
    if len(sil):
        projected = np.stack([sil @ right, sil @ up], axis=-1)
        keep_len = np.linalg.norm(projected[:, 1] - projected[:, 0], axis=1) > 0.5 * px
        sil = sil[keep_len]
        projected = projected[keep_len]
    if len(sil):
        chains = _chain(projected, sil, 0.6 * px)
        for chain in chains:
            if len(chain) < 2:
                continue
            dense = _densify(np.array(chain), max(px, 1e-6))
            vis = _visible(dense, image, to_win, dz * (2.5 * px + defl))
            flat = np.c_[dense @ right, dense @ up]
            for run in _runs(flat, vis, np.array([len(dense)])):
                poly = [(float(x), float(y)) for x, y in run]
                item = fit_chain(poly, 'vis', ellipses=(fit and name == 'trimetric'))
                if item and _length(item) >= 1.5 * px:
                    lines.append(item)
    return lines


def _length(line):
    import math
    if line['kind'] == 'circle':
        return 2 * math.pi * line['r']
    if line['kind'] == 'ellipse':
        return 2 * math.pi * max(line['rx'], line['ry'])
    pts = line['pts']
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _silhouettes(verts, faces, corners, toward):
    import numpy as np
    g = corners @ toward
    g = np.where(np.abs(g) < 1e-5, 1e-12, g)
    sign = g > 0
    cross = (sign.any(1) & ~sign.all(1)) & (np.abs(g).max(1) > 5e-4)
    if not cross.any():
        return np.zeros((0, 2, 3))
    ft, gt = faces[cross], g[cross]
    pieces = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ga, gb = gt[:, a], gt[:, b]
        ok = (ga > 0) != (gb > 0)
        va, vb = ft[:, a], ft[:, b]
        swap = va > vb
        lo = np.where(swap, vb, va)
        hi = np.where(swap, va, vb)
        glo = np.where(swap, gb, ga)
        ghi = np.where(swap, ga, gb)
        t = glo / np.where(ok, glo - ghi, 1.0)
        point = verts[lo].astype(float) + t[:, None] * (verts[hi].astype(float) - verts[lo].astype(float))
        pieces.append((ok, point))
    (o0, p0), (o1, p1), (o2, p2) = pieces
    a = np.where(o0[:, None], p0, p1)
    b = np.where(o0[:, None] & o1[:, None], p1, p2)
    seg = np.stack([a, b], axis=1)
    seg = seg[np.linalg.norm(a - b, axis=1) > 1e-9]
    return seg


def _chain(projected, segs, tol):
    """Join 3-D silhouette segments whose 2-D ends are within tol. Returns 3-D polylines."""
    import numpy as np
    if not len(segs):
        return []
    ends = []
    links = []
    for i, seg in enumerate(segs):
        a = (float(projected[i, 0, 0]), float(projected[i, 0, 1]))
        b = (float(projected[i, 1, 0]), float(projected[i, 1, 1]))
        links.append((a, b, seg[0], seg[1]))
    # Reuse the 2-D gap joiner on the projected ends, then rebuild 3-D by index.
    polylines = bridge_gaps([[link[0], link[1]] for link in links], tol)
    # Map each 2-D point back to the nearest 3-D end. Good enough for a silhouette chain.
    flat2 = np.array([p for link in links for p in link[:2]])
    flat3 = np.array([p for link in links for p in (link[2], link[3])])
    out = []
    for poly in polylines:
        chain = []
        for x, y in poly:
            d = np.hypot(flat2[:, 0] - x, flat2[:, 1] - y)
            chain.append(flat3[int(np.argmin(d))])
        out.append(chain)
    return out
