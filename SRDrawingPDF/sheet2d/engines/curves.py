"""Circle and ellipse fits, and closing small gaps between visible runs.

Pure Python so the checks can run without the XQ packages. A hexagon is not
a circle. A closed chain that is round becomes a circle. In a trimetric view
a closed chain that is an ellipse becomes an ellipse.
"""
import math


def _near(a, b, tol):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def bridge_gaps(polylines, tol):
    """Join polylines whose ends lie within tol. Short breaks in a visible edge close up."""
    unused = [list(p) for p in polylines if len(p) >= 2]
    used = [False] * len(unused)
    out = []
    for i, pts in enumerate(unused):
        if used[i]:
            continue
        used[i] = True
        grew = True
        while grew:
            grew = False
            for j, other in enumerate(unused):
                if used[j]:
                    continue
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
    """A circle dict, or None. Flats (a hexagon) stay polylines."""
    ring = list(pts)
    closed = len(ring) > 2 and _near(ring[0], ring[-1], tol)
    if closed:
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


def fit_ellipse(pts, tol):
    """An ellipse dict for a closed chain that is not a circle, or None."""
    ring = list(pts)
    if len(ring) > 2 and _near(ring[0], ring[-1], tol):
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


def _rho(x, y, cx, cy, rx, ry, c, s):
    dx, dy = x - cx, y - cy
    u = c * dx + s * dy
    v = -s * dx + c * dy
    return math.hypot(u / rx, v / ry)


def fit_chain(pts, style, ellipses=False, tol=0.05):
    """A circle, an ellipse, or a polyline. Hidden styles are not used."""
    if style in ('hid', 'hidden', 'dash'):
        return None
    style = 'thin' if style in ('tan', 'thin') else 'ctr' if style == 'ctr' else 'vis'
    circ = fit_circle(pts, tol)
    if circ:
        circ['style'] = style
        return circ
    if ellipses:
        ell = fit_ellipse(pts, tol)
        if ell:
            ell['style'] = style
            return ell
    closed = len(pts) > 2 and _near(pts[0], pts[-1], tol)
    return {'kind': 'poly', 'pts': [tuple(p) for p in pts], 'style': style, 'closed': closed}
