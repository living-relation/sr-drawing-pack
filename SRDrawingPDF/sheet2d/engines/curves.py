"""Circle and ellipse fits, and closing small gaps between visible runs.

Pure Python so the checks can run without the XQ packages. A hexagon is not
a circle. A closed chain that is round becomes a circle. In a trimetric view
a closed chain that is an ellipse becomes an ellipse.
"""
import math


def _near(a, b, tol):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def bridge_gaps(polylines, tol):
    """Join polylines whose ends lie within tol. Short breaks in a visible edge close up.

    A spatial hash finds the same neighbor the old scan found: the lowest
    unused index, and the same end-to-end order. The result matches that scan.
    """
    unused = [list(p) for p in polylines if len(p) >= 2]
    n = len(unused)
    used = [False] * n
    cell = tol if tol > 0 else 1e-12
    buckets = {}

    def _cell(p):
        return (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)))

    for i, pts in enumerate(unused):
        buckets.setdefault(_cell(pts[0]), []).append(i)
        if _cell(pts[-1]) != _cell(pts[0]):
            buckets.setdefault(_cell(pts[-1]), []).append(i)

    def _nearby(p):
        cx, cy = _cell(p)
        found = []
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                found.extend(buckets.get((cx + dx, cy + dy), ()))
        return found

    out = []
    for i, pts in enumerate(unused):
        if used[i]:
            continue
        used[i] = True
        grew = True
        while grew:
            grew = False
            seen = set()
            order = []
            for end in (pts[-1], pts[0]):
                for j in _nearby(end):
                    if used[j] or j in seen:
                        continue
                    seen.add(j)
                    order.append(j)
            order.sort()
            for j in order:
                other = unused[j]
                if _near(pts[-1], other[0], tol):
                    pts.extend(other[1:])
                elif _near(pts[-1], other[-1], tol):
                    pts.extend(reversed(other[:-1]))
                elif _near(pts[0], other[-1], tol):
                    pts[:0] = other[:-1]
                elif _near(pts[0], other[0], tol):
                    pts[:0] = list(reversed(other[1:]))
                else:
                    continue
                used[j] = True
                grew = True
                break
        if _near(pts[0], pts[-1], tol) and len(pts) > 2:
            pts[-1] = pts[0]
        out.append(pts)
    return out


def _solve3(rows, rhs):
    m = [list(rows[i]) + [rhs[i]] for i in range(3)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda row: abs(m[row][col]))
        m[col], m[pivot] = m[pivot], m[col]
        if abs(m[col][col]) < 1e-14:
            return None
        scale = m[col][col]
        for j in range(col, 4):
            m[col][j] /= scale
        for row in range(3):
            if row == col:
                continue
            factor = m[row][col]
            for j in range(col, 4):
                m[row][j] -= factor * m[col][j]
    return [m[i][3] for i in range(3)]


def _circle(pts):
    """Kasa circle fit. Returns (cx, cy, r) or None."""
    n = float(len(pts))
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sxy = sx = syy = sy = sz = sxz = syz = 0.0
    for x0, y0 in pts:
        x, y = x0 - mx, y0 - my
        xx, yy = x * x, y * y
        sx += x
        sy += y
        sxx += xx
        syy += yy
        sxy += x * y
        sz += xx + yy
        sxz += x * (xx + yy)
        syz += y * (xx + yy)
    sol = _solve3(((sxx, sxy, sx), (sxy, syy, sy), (sx, sy, n)), (-sxz, -syz, -sz))
    if not sol:
        return None
    d, e, f = sol
    cx, cy = -d / 2.0, -e / 2.0
    r2 = cx * cx + cy * cy - f
    if r2 <= 1e-8:
        return None
    return (cx + mx, cy + my, math.sqrt(r2))


def _flat(pts, tol):
    a = pts[0]
    b = max(pts, key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    return max(abs(dx * (p[1] - a[1]) - dy * (p[0] - a[0])) / length for p in pts) <= tol


def _sagitta_ok(pts, cx, cy, r, tol, closed):
    seq = list(pts)
    if closed:
        seq = seq + [seq[0]]
    for a, b in zip(seq, seq[1:]):
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        if abs(math.hypot(mx - cx, my - cy) - r) > tol:
            return False
        if abs(math.hypot(a[0] - cx, a[1] - cy) - r) > tol:
            return False
    return True


def fit_circle(pts, tol):
    """A full circle, or None. An open chain is never a circle. Flats stay polylines."""
    ring = list(pts)
    closed = len(ring) > 2 and _near(ring[0], ring[-1], tol)
    if not closed:
        return None
    ring = ring[:-1]
    if len(ring) < 6 or _flat(pts, tol):
        return None
    got = _circle(ring)
    if not got:
        return None
    cx, cy, r = got
    if r < 1e-3 or r > 1e6:
        return None
    # 0.11 of the radius: an octagon passes, a hexagon (0.134) does not.
    limit = max(tol, 0.11 * r)
    if not _sagitta_ok(ring, cx, cy, r, limit, True):
        return None
    return {'kind': 'circle', 'c': (cx, cy), 'r': r}


def _sweep(a0, a1, amid):
    """Start and end angles whose sweep passes through the middle sample."""
    twopi = 2.0 * math.pi

    def ccw(a, b):
        return (b - a) % twopi

    if ccw(a0, amid) <= ccw(a0, a1) + 1e-9:
        return a0, a0 + ccw(a0, a1)
    return a0, a0 - ccw(a1, a0)


def arc_points(line, n=24):
    """Points along an arc from a0 to a1. a1 may be less than a0."""
    cx, cy = line['c']
    r = line['r']
    a0, a1 = line['a0'], line['a1']
    steps = max(2, int(n))
    pts = []
    for i in range(steps + 1):
        t = a0 + (a1 - a0) * i / steps
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def fit_arc(pts, tol):
    """An open arc, or None. A gentle curve is not a giant circle."""
    ring = list(pts)
    if len(ring) > 2 and _near(ring[0], ring[-1], tol):
        return None
    if len(ring) < 6 or _flat(ring, tol):
        return None
    got = _circle(ring)
    if not got:
        return None
    cx, cy, r = got
    diag = 0.0
    for p in ring:
        diag = max(diag, math.hypot(p[0] - ring[0][0], p[1] - ring[0][1]))
    if r < 1e-3 or r > max(50.0, 8.0 * max(diag, 1e-6)):
        return None
    residual = max(abs(math.hypot(p[0] - cx, p[1] - cy) - r) for p in ring)
    if residual > max(tol, 0.02 * max(diag, 1e-6)):
        return None
    if not _sagitta_ok(ring, cx, cy, r, max(tol, 0.11 * r), False):
        return None
    a0 = math.atan2(ring[0][1] - cy, ring[0][0] - cx)
    a1 = math.atan2(ring[-1][1] - cy, ring[-1][0] - cx)
    mid = ring[len(ring) // 2]
    amid = math.atan2(mid[1] - cy, mid[0] - cx)
    start, end = _sweep(a0, a1, amid)
    if abs(end - start) < 1e-3 or abs(end - start) > 2.0 * math.pi - 0.05:
        return None
    return {'kind': 'arc', 'c': (cx, cy), 'r': r, 'a0': start, 'a1': end}


def fit_ellipse(pts, tol):
    """An ellipse dict for a closed chain that is not a circle, or None."""
    ring = list(pts)
    if not (len(ring) > 2 and _near(ring[0], ring[-1], tol)):
        return None
    ring = ring[:-1]
    if len(ring) < 8:
        return None
    n = float(len(ring))
    cx = sum(p[0] for p in ring) / n
    cy = sum(p[1] for p in ring) / n
    sxx = syy = sxy = 0.0
    for x, y in ring:
        dx, dy = x - cx, y - cy
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy
    sxx /= n
    syy /= n
    sxy /= n
    tr = sxx + syy
    disc = math.sqrt(max(0.0, tr * tr / 4.0 - (sxx * syy - sxy * sxy)))
    l1 = tr / 2.0 + disc
    l2 = tr / 2.0 - disc
    if l2 <= 1e-9:
        return None
    if abs(sxy) < 1e-9 and abs(l1 - sxx) < 1e-9:
        phi = 0.0
    elif abs(sxy) < 1e-9:
        phi = math.pi / 2.0
    else:
        phi = math.atan2(l1 - sxx, sxy)
    rx, ry = math.sqrt(2.0 * l1), math.sqrt(2.0 * l2)
    if ry > rx:
        rx, ry = ry, rx
        phi += math.pi / 2.0
    if ry > 0.92 * rx or ry < 0.2 * rx:
        return None
    c, s = math.cos(phi), math.sin(phi)
    seq = ring + [ring[0]]
    for i, (x, y) in enumerate(ring):
        if abs(_rho(x, y, cx, cy, rx, ry, c, s) - 1.0) > 0.11:
            return None
        mx = (seq[i][0] + seq[i + 1][0]) / 2.0
        my = (seq[i][1] + seq[i + 1][1]) / 2.0
        if abs(_rho(mx, my, cx, cy, rx, ry, c, s) - 1.0) > 0.11:
            return None
    return {'kind': 'ellipse', 'c': (cx, cy), 'rx': rx, 'ry': ry, 'rot': phi}


def _major_angle(ax, ay, bx, by):
    """Angle of the long axis. The conjugate-radius formula's parameter is not that angle."""
    t = 0.5 * math.atan2(2.0 * (ax * bx + ay * by), (ax * ax + ay * ay) - (bx * bx + by * by))
    ct, st = math.cos(t), math.sin(t)
    px, py = ct * ax + st * bx, ct * ay + st * by
    qx, qy = -st * ax + ct * bx, -st * ay + ct * by
    if px * px + py * py < qx * qx + qy * qy:
        px, py = qx, qy
    if px * px + py * py < 1e-18:
        return 0.0
    return math.atan2(py, px)


def _rho(x, y, cx, cy, rx, ry, c, s):
    dx, dy = x - cx, y - cy
    u = c * dx + s * dy
    v = -s * dx + c * dy
    return math.hypot(u / rx, v / ry)


def analytic_curve(origin, xdir, ydir, radius, u0, u1, right, up, style, partial=False):
    """A circle, ellipse, or arc from the real edge, projected into the view.

    origin, xdir and ydir are the circle's center and two axis directions in
    model space. right and up are the view axes. A full circle facing the
    viewer stays a circle. Tilted, it is an ellipse. Edge-on, it is a line.
    A partial span that still looks round is an arc. A tilted partial span
    stays points on that true curve.
    """
    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    cx, cy = dot(origin, right), dot(origin, up)
    ax, ay = radius * dot(xdir, right), radius * dot(xdir, up)
    bx, by = radius * dot(ydir, right), radius * dot(ydir, up)
    q = ax * ax + ay * ay + bx * bx + by * by
    area = ax * by - ay * bx
    disc = max(0.0, q * q - 4.0 * area * area)
    root = math.sqrt(disc)
    rx = math.sqrt(max(0.0, (q + root) / 2.0))
    ry = math.sqrt(max(0.0, (q - root) / 2.0))
    if rx < 1e-6:
        return None
    span = abs(u1 - u0)
    full = span >= 2.0 * math.pi - 0.25 and not partial
    if ry < 0.08 * rx:
        # The circle is edge-on. The long conjugate radius is the line.
        if ax * ax + ay * ay >= bx * bx + by * by:
            p0, p1 = (cx - ax, cy - ay), (cx + ax, cy + ay)
        else:
            p0, p1 = (cx - bx, cy - by), (cx + bx, cy + by)
        return {'kind': 'poly', 'pts': [p0, p1], 'style': style, 'closed': False, 'analytic': True}
    if full and ry > 0.92 * rx:
        return {'kind': 'circle', 'c': (cx, cy), 'r': (rx + ry) / 2.0, 'style': style, 'analytic': True}
    if full:
        return {
            'kind': 'ellipse', 'c': (cx, cy), 'rx': rx, 'ry': ry,
            'rot': _major_angle(ax, ay, bx, by),
            'style': style, 'analytic': True,
        }
    if ry > 0.92 * rx:
        def _ang(t):
            return math.atan2(
                math.cos(t) * ay + math.sin(t) * by,
                math.cos(t) * ax + math.sin(t) * bx)
        a0, a1 = _sweep(_ang(u0), _ang(u1), _ang((u0 + u1) / 2.0))
        return {
            'kind': 'arc', 'c': (cx, cy), 'r': (rx + ry) / 2.0, 'a0': a0, 'a1': a1,
            'style': style, 'analytic': True,
        }
    steps = max(8, int(span / (math.pi / 36.0)))
    pts = []
    for i in range(steps + 1):
        t = u0 + (u1 - u0) * i / steps
        ct, st = math.cos(t), math.sin(t)
        pts.append((cx + ct * ax + st * bx, cy + ct * ay + st * by))
    closed = _near(pts[0], pts[-1], 1e-6)
    return {'kind': 'poly', 'pts': pts, 'style': style, 'closed': closed, 'analytic': True}


def fit_chain(pts, style, ellipses=False, tol=0.05):
    """A circle, an ellipse, or a polyline. Hidden styles are not used."""
    if style in ('hid', 'hidden', 'dash'):
        return None
    style = 'thin' if style in ('tan', 'thin') else 'ctr' if style == 'ctr' else 'vis'
    circ = fit_circle(pts, tol)
    if circ:
        circ['style'] = style
        return circ
    arc = fit_arc(pts, tol)
    if arc:
        arc['style'] = style
        return arc
    if ellipses:
        ell = fit_ellipse(pts, tol)
        if ell:
            ell['style'] = style
            return ell
    closed = len(pts) > 2 and _near(pts[0], pts[-1], tol)
    return {'kind': 'poly', 'pts': [tuple(p) for p in pts], 'style': style, 'closed': closed}
