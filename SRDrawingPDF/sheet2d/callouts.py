"""BOM rows and balloons from an assembly component list.

Views are frames the caller already placed. This module does not look at
view lines. A leader tip is a point the component record supplies, or a
point spread inside the chosen view when the record has none.

Balloon layout follows the SOLIDWORKS Auto Balloon PropertyManager
(https://my.solidworks.com/reader/onlinehelp/2021%252Fenglish%252Fswconnected%252Fswdotworks%252Fhidd_dve_auto_balloon.htm/auto-balloon-propertymanager):
Square, Circular, Top, Bottom, Left, Right, Reverse direction, Ignore
multiple instances, and Insert magnetic line(s) (not offered for Circular).
"""
import math

from .canvas import BALLOON_R

LAYOUTS = ('square', 'circular', 'top', 'bottom', 'left', 'right')
# Circle plus a small gap, so neighbours do not touch.
CLEAR = BALLOON_R + 1.2
PAD = BALLOON_R + 2.5


def rollup_components(components):
    """(rows, targets). One BOM row per part. qty is how many times it appears.

    Part number and description are copied from the records. A missing part
    number stays blank. A missing description uses the component name when
    the record has one, and stays blank when it does not. Nothing else is filled in.

    targets[key] is the leader tip of each instance, in list order. A tip is
    (u, v) fractions of the view, (x, y) sheet millimetres when the record
    says so, or None when the record has no point.
    """
    groups = []
    index = {}
    for rec in components or []:
        ident = _identity(rec)
        if ident is None:
            ident = 'row:%d' % len(groups)
        if ident not in index:
            index[ident] = len(groups)
            groups.append({
                'key': ident,
                'pn': _text(rec, 'part_number', 'pn'),
                'desc': _text(rec, 'description', 'desc') or _text(rec, 'name'),
                'mat': _text(rec, 'material', 'mat'),
                'qty': 0,
                'shown': False,
                'component': rec.get('component') or ident,
                'thumbnail': rec.get('thumbnail'),
                'tips': [],
            })
        group = groups[index[ident]]
        group['qty'] += _qty(rec)
        if rec.get('shown', True):
            group['shown'] = True
        if not group['desc']:
            group['desc'] = _text(rec, 'description', 'desc') or _text(rec, 'name')
        if not group['mat']:
            group['mat'] = _text(rec, 'material', 'mat')
        if not group['thumbnail'] and rec.get('thumbnail'):
            group['thumbnail'] = rec.get('thumbnail')
        group['tips'].extend(_tips(rec))
    rows = []
    targets = {}
    for i, group in enumerate(groups, 1):
        tips = group.pop('tips')
        group['item'] = i
        if group['qty'] == int(group['qty']):
            group['qty'] = int(group['qty'])
        rows.append(group)
        targets[group['key']] = tips
    return rows, targets


def layout_balloons(view, tips, pattern, reverse, blockers, sheet, magnetic):
    """(placements, lines). placements are (x, y, ax, ay) in sheet millimetres.

    Balloons sit outside the view on the chosen pattern and move until they
    clear each other and the blockers (other views, the title block, the BOM).
    """
    if pattern not in LAYOUTS:
        raise ValueError('layout must be one of %s' % ', '.join(LAYOUTS))
    x, y, w, h = (float(v) for v in view)
    n = len(tips)
    if n == 0:
        return [], []
    slots = _slots(x, y, w, h, n, pattern)
    if reverse:
        slots = list(reversed(slots))
    width, height = sheet
    placed = []
    centers = []
    for (sx, sy, side), tip in zip(slots, tips):
        px, py = _clear(sx, sy, (x, y, w, h), blockers, centers, (width, height))
        ax, ay = _tip_xy((x, y, w, h), tip, len(placed), n)
        placed.append((px, py, ax, ay, side))
        centers.append((px, py))
    lines = []
    if magnetic and pattern != 'circular':
        lines = _magnetic_lines(placed)
    return [(px, py, ax, ay) for px, py, ax, ay, _side in placed], lines


def _identity(rec):
    pn = _text(rec, 'part_number', 'pn')
    if pn:
        return 'pn:' + pn
    name = _text(rec, 'name')
    if name:
        return 'name:' + name
    key = _text(rec, 'key')
    if key:
        return 'key:' + key
    return None


def _text(rec, *names):
    for name in names:
        value = rec.get(name)
        if value is not None and str(value).strip() != '':
            return str(value).strip()
    return ''


def _qty(rec):
    value = rec.get('qty', 1)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 1
    return number if number > 0 else 1


def _tips(rec):
    """One tip per instance. qty with no per-instance points repeats the record tip."""
    raw = rec.get('instances')
    if raw:
        out = []
        for item in raw:
            if isinstance(item, dict):
                out.append(item.get('at'))
            else:
                out.append(item)
        return out or [None]
    count = _qty(rec)
    count = int(count) if count == int(count) else 1
    return [rec.get('at') for _i in range(max(1, count))]


def _slots(x, y, w, h, n, pattern):
    pad = PAD
    if pattern == 'top':
        return [_row(x, y + h + pad, w, n, i, 'top', True) for i in range(n)]
    if pattern == 'bottom':
        return [_row(x, y - pad, w, n, i, 'bottom', True) for i in range(n)]
    if pattern == 'left':
        return [_row(x - pad, y, h, n, i, 'left', False) for i in range(n)]
    if pattern == 'right':
        return [_row(x + w + pad, y, h, n, i, 'right', False) for i in range(n)]
    if pattern == 'circular':
        cx, cy = x + w / 2.0, y + h / 2.0
        rad = math.hypot(w / 2.0, h / 2.0) + pad
        slots = []
        for i in range(n):
            ang = math.pi / 2.0 - 2.0 * math.pi * i / n
            slots.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang), 'circular'))
        return slots
    return _square_slots(x, y, w, h, n, pad)


def _row(origin, fixed, span, n, i, side, horizontal):
    t = (i + 0.5) / n
    if horizontal:
        return (origin + span * t, fixed, side)
    return (fixed, origin + span * t, side)


def _square_slots(x, y, w, h, n, pad):
    x0, y0 = x - pad, y - pad
    x1, y1 = x + w + pad, y + h + pad
    edges = (
        ('top', (x0, y1), (x1, y1)),
        ('right', (x1, y1), (x1, y0)),
        ('bottom', (x1, y0), (x0, y0)),
        ('left', (x0, y0), (x0, y1)),
    )
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for _side, a, b in edges]
    total = sum(lengths) or 1.0
    slots = []
    for i in range(n):
        dist = total * (i + 0.5) / n
        acc = 0.0
        for (side, a, b), length in zip(edges, lengths):
            if dist <= acc + length or side == 'left':
                t = 0.0 if length <= 0 else min(1.0, max(0.0, (dist - acc) / length))
                slots.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, side))
                break
            acc += length
    return slots


def _clear(x, y, view, blockers, centers, sheet):
    vx, vy, vw, vh = view
    ox, oy = x - (vx + vw / 2.0), y - (vy + vh / 2.0)
    length = math.hypot(ox, oy) or 1.0
    outward = (ox / length, oy / length)
    along = (-outward[1], outward[0])
    width, height = sheet
    for step in range(0, 40):
        shifts = (0,) if step == 0 else (0, step, -step)
        for shift in shifts:
            px = x + outward[0] * step * 2.0 + along[0] * shift * 2.0
            py = y + outward[1] * step * 2.0 + along[1] * shift * 2.0
            if _free(px, py, blockers, centers, width, height):
                return px, py
    return x, y


def _free(x, y, blockers, centers, width, height):
    margin = BALLOON_R + 1.0
    if x < margin or y < margin or x > width - margin or y > height - margin:
        return False
    for rect in blockers:
        if _hits_rect(x, y, CLEAR, rect):
            return False
    for cx, cy in centers:
        if math.hypot(x - cx, y - cy) < 2.0 * CLEAR:
            return False
    return True


def _hits_rect(cx, cy, r, rect):
    x0, y0, x1, y1 = rect
    nx = min(max(cx, x0), x1)
    ny = min(max(cy, y0), y1)
    return math.hypot(cx - nx, cy - ny) < r


def _tip_xy(view, tip, index, n):
    x, y, w, h = view
    if isinstance(tip, dict) and 'x' in tip and 'y' in tip:
        return float(tip['x']), float(tip['y'])
    if isinstance(tip, (list, tuple)) and len(tip) == 2:
        return x + float(tip[0]) * w, y + float(tip[1]) * h
    cols = int(math.ceil(math.sqrt(n))) or 1
    rows = int(math.ceil(n / float(cols)))
    col = index % cols
    row = index // cols
    return (x + w * (col + 0.5) / cols, y + h * (row + 0.5) / rows)


def _magnetic_lines(placed):
    """One line per pattern side that holds at least two balloons."""
    by_side = {}
    for px, py, _ax, _ay, side in placed:
        by_side.setdefault(side, []).append((px, py))
    lines = []
    for side, pts in by_side.items():
        if len(pts) < 2 or side == 'circular':
            continue
        if side in ('top', 'bottom'):
            y = sum(p[1] for p in pts) / len(pts)
            xs = [p[0] for p in pts]
            lines.append((min(xs), y, max(xs), y))
        else:
            x = sum(p[0] for p in pts) / len(pts)
            ys = [p[1] for p in pts]
            lines.append((x, min(ys), x, max(ys)))
    return lines
