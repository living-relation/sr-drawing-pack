"""Put an assembly's front, top, right and trimetric views on a size B sheet.

Default: one sheet scale for the standard views, the largest standard scale that
fits with room for dimensions (sr-drawing-pack ADR-035). Third-angle projection:
top above front, right to the right. The trimetric takes the largest standard
scale that fits the space left over and prints its scale when it differs.

Every view can take its own scale afterwards (set_view_scale): any standard
scale or a custom ratio. A view without its own scale follows the sheet scale
(set_sheet_scale), the scale in the title block. A view at another scale prints
a SCALE caption. After a change the views are laid out again.

View lines are kept here, outside the drawing JSON, under the view's `geom`
key. render.py draws them when the key is known, otherwise the empty frame.
Small things are thinned by size on paper, not by segment length: a joined line
smaller than MIN_LINE_MM across is left out, and a group of touching lines
smaller than SMALL_FEATURE_MM across keeps only its outline (the lines that reach
the group's edge). A screw head then prints as its outer ring, not as a dot made
of its socket, chamfer and cone edges. Both are drawing properties
(`min_line_mm`, `small_feature_mm`); 0 turns one off.
"""
import gc
import math
import time

from .canvas import PH, PW, VIEW_CAPTION_H, VIEW_SUB_H, revlog_rect
from .model import DrawingDocument
from .project import project_view, view_extent

# Largest first. handbuilt-cad dwg.STD_SCALES, plus 1:20, 1:30 and 1:50 for machines.
STD_SCALES = (
    (10.0, '10:1'), (8.0, '8:1'), (5.0, '5:1'), (4.0, '4:1'), (3.0, '3:1'), (2.0, '2:1'),
    (1.5, '1.5:1'), (1.0, '1:1'), (2.0 / 3.0, '1:1.5'), (0.5, '1:2'), (0.4, '1:2.5'),
    (1.0 / 3.0, '1:3'), (0.25, '1:4'), (0.2, '1:5'), (0.1, '1:10'), (0.05, '1:20'),
    (1.0 / 30.0, '1:30'), (0.02, '1:50'),
)
VIEW_NAMES = ('front', 'top', 'right', 'trimetric')
MIN_LINE_MM = 0.3       # a line smaller than this across on paper is not drawn
SMALL_FEATURE_MM = 3.0  # a feature smaller than this on paper keeps only its outline
# Space for the views on size B: inside the border, above the title and tolerance blocks.
REGION = (16.0, 67.0, PW - 16.0, PH - 16.0)
GAP = 16.0           # between views, room for dimensions
CAPTION_ROOM = 9.0   # under a view that prints a caption
PX_PER_MM = 4.0      # depth-buffer pixels per printed millimetre
MAX_BUF = 1800
STYLE = {'vis': 'vis', 'thin': 'thin', 'ctr': 'ctr'}

_GEOM = {}


def register_view_geometry(key, view):
    """Keep a view's lines (model units) for render.py. Returns key."""
    buf = view.get('buf')
    _GEOM[key] = {'lines': view['lines'], 'extent': view['extent'], 'name': view.get('name'),
                  'px_per_model_mm': buf[3] if buf else None}
    return key


def view_geometry(key):
    return _GEOM.get(key) if key else None


def clear_view_geometry(prefix=''):
    for key in [k for k in _GEOM if k.startswith(prefix)]:
        del _GEOM[key]


def _setting(properties, key, default):
    try:
        v = float((properties or {}).get(key))
    except (TypeError, ValueError):
        return default
    return v if v >= 0 else default


def min_line_mm(properties):
    """Smallest printed line, mm across (MIN_LINE_MM unless the drawing sets min_line_mm)."""
    return _setting(properties, 'min_line_mm', MIN_LINE_MM)


def small_feature_mm(properties):
    """Features smaller than this on paper keep only their outline (small_feature_mm)."""
    return _setting(properties, 'small_feature_mm', SMALL_FEATURE_MM)


def _bbox(line):
    if line['kind'] == 'circle':
        (cx, cy), r = line['c'], line['r']
        return (cx - r, cy - r, cx + r, cy + r)
    xs = [p[0] for p in line['pts']]
    ys = [p[1] for p in line['pts']]
    return (min(xs), min(ys), max(xs), max(ys))


def thin_small_features(lines, scale, min_mm=MIN_LINE_MM, small_mm=SMALL_FEATURE_MM):
    """(kept lines, dropped count). Sizes are on paper at `scale`; lines are in model mm."""
    s = float(scale or 1.0)
    cut = (min_mm or 0.0) / s
    small = (small_mm or 0.0) / s
    boxes = [_bbox(line) for line in lines]
    keep = [max(b[2] - b[0], b[3] - b[1]) >= cut for b in boxes]
    if small > 0:
        # Group lines whose boxes touch (grid buckets the size of a small feature).
        tol = 0.02 * small
        parent = list(range(len(lines)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        grid = {}
        for i, b in enumerate(boxes):
            if not keep[i] or max(b[2] - b[0], b[3] - b[1]) > small:
                continue  # big lines are never thinned and do not join groups
            for gx in range(int(math.floor(b[0] / small)), int(math.floor(b[2] / small)) + 1):
                for gy in range(int(math.floor(b[1] / small)), int(math.floor(b[3] / small)) + 1):
                    for j in grid.get((gx, gy), ()):
                        c = boxes[j]
                        if b[0] <= c[2] + tol and c[0] <= b[2] + tol and b[1] <= c[3] + tol and c[1] <= b[3] + tol:
                            ri, rj = find(i), find(j)
                            if ri != rj:
                                parent[ri] = rj
                    grid.setdefault((gx, gy), []).append(i)
        groups = {}
        for i in range(len(lines)):
            if keep[i] and max(boxes[i][2] - boxes[i][0], boxes[i][3] - boxes[i][1]) <= small:
                groups.setdefault(find(i), []).append(i)
        for members in groups.values():
            if len(members) < 2:
                continue
            g = (min(boxes[i][0] for i in members), min(boxes[i][1] for i in members),
                 max(boxes[i][2] for i in members), max(boxes[i][3] for i in members))
            size = max(g[2] - g[0], g[3] - g[1])
            if size > small:
                continue
            edge = 0.03 * size
            for i in members:
                b = boxes[i]
                if not (b[0] <= g[0] + edge or b[1] <= g[1] + edge or b[2] >= g[2] - edge or b[3] >= g[3] - edge):
                    keep[i] = False  # inside the feature's outline
    kept = [line for line, k in zip(lines, keep) if k]
    return kept, len(lines) - len(kept)


def draw_view_lines(sh, el, geom, scale, caption=None, min_mm=MIN_LINE_MM, small_mm=SMALL_FEATURE_MM):
    """The view's visible lines, centred in its frame at `scale`, then its caption.

    Small features are thinned first (thin_small_features). Returns the number
    of lines left out."""
    x, y, w, h = float(el['x']), float(el['y']), float(el['w']), float(el['h'])
    u0, u1, v0, v1 = geom['extent']
    s = float(scale or 1.0)
    cx, cy = x + w / 2.0, y + h / 2.0
    uc, vc = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    key = (round(s, 9), min_mm, small_mm)
    cache = geom.setdefault('_thinned', {})
    if key not in cache:
        cache.clear()
        cache[key] = thin_small_features(geom['lines'], s, min_mm, small_mm)
    lines, dropped = cache[key]
    for line in lines:
        sty = STYLE.get(line['style'], 'thin')
        if line['kind'] == 'circle':
            c = line['c']
            r = line['r'] * s
            sh.circle((cx + (c[0] - uc) * s, cy + (c[1] - vc) * s), r, sty, n=max(12, min(72, int(r * 4))))
            continue
        sh.pl([(cx + (p[0] - uc) * s, cy + (p[1] - vc) * s) for p in line['pts']], sty)
    yy = y - 2.0
    for i, text in enumerate(caption or []):
        hh = VIEW_CAPTION_H if i == 0 and not text.startswith('SCALE ') else VIEW_SUB_H
        sh.txt(x + w / 2, yy, text, h=hh, bold=(hh == VIEW_CAPTION_H), va='top')
        yy -= hh * 1.6
    return dropped


def _size(ext):
    return ext[1] - ext[0], ext[3] - ext[2]


def scale_label(value):
    """'1:30' style text for a scale number: the standard label when there is one."""
    for v, label in STD_SCALES:
        if abs(v - value) < 1e-9 * max(1.0, v):
            return label
    if value >= 1:
        return ('%g:1' % round(value, 4))
    return ('1:%g' % round(1.0 / value, 4))


def _overlap(a, b):
    return a[0] < b[0] + b[2] - 1e-6 and b[0] < a[0] + a[2] - 1e-6 and \
        a[1] < b[1] + b[3] - 1e-6 and b[1] < a[1] + a[3] - 1e-6


def arrange(extents, scales, sheet_value, rev_rect, region=REGION, gap=GAP):
    """Frames for the views at the given scales (name -> number).

    Front sits low left, top above it, right beside it, centred on the front
    view; the trimetric goes right of the top view (under the rev table) or,
    when it fits better, right of the right view. Views whose scale is not the
    sheet scale get room under them for the SCALE caption. Never refuses: what
    does not fit is listed in 'problems'."""
    L, B, R, T = region
    rx0, ry0 = rev_rect[0] - 3.0, rev_rect[1] - 3.0

    def size(n):
        w, h = _size(extents[n])
        return w * scales[n], h * scales[n]

    def room(n):
        return 0.0 if abs(scales[n] - sheet_value) < 1e-12 else CAPTION_ROOM

    wf, hf = size('front')
    wt, ht = size('top')
    wr, hr = size('right')
    cf, ct, cr = room('front'), room('top'), room('right')
    colw = max(wf, wt)
    cap = max(cf, cr)
    band = max(hf, hr)
    total_h = cap + band + gap + ht + ct
    t_eff = ry0 if L + colw > rx0 else T
    y0 = B + max(0.0, (t_eff - B - total_h) / 2.0)
    cy = y0 + cap + band / 2.0
    xc = L + colw / 2.0
    frames = {
        'front': (xc - wf / 2.0, cy - hf / 2.0, wf, hf),
        'top': (xc - wt / 2.0, y0 + cap + band + gap + ct, wt, ht),
    }
    xr = frames['front'][0] + wf + gap
    frames['right'] = (xr, cy - hr / 2.0, wr, hr)
    problems = []
    if 'trimetric' in extents and 'trimetric' in scales:
        tw, th = size('trimetric')
        tc = room('trimetric')
        top = frames['top']
        areas = []
        ax0 = top[0] + top[2] + gap
        ay0 = max(frames['right'][1] + hr, frames['front'][1] + hf) + gap
        areas.append((ax0, ay0, R - ax0, (ry0 if R > rx0 else T) - ay0))
        bx0 = xr + wr + gap
        areas.append((bx0, B, R - bx0, (ry0 if R > rx0 else T) - B))
        best = None
        for ax, ay, aw, ah in areas:
            if tw <= aw and th + tc <= ah:
                best = (ax + (aw - tw) / 2.0, ay + tc + (ah - tc - th) / 2.0, tw, th)
                break
        if best is None:
            ax, ay, aw, ah = areas[0]
            best = (ax + max(0.0, (aw - tw) / 2.0), ay + tc, tw, th)
        frames['trimetric'] = best
    rev = (rx0, ry0, R - rx0 + 16.0, T - ry0 + 16.0)
    boxes = {}
    for n, (x, y, w, h) in frames.items():
        c = room(n)
        boxes[n] = (x, y - c, w, h + c)
        if x < L - 1e-6 or y - c < B - 1e-6 or x + w > R + 1e-6 or y + h > T + 1e-6:
            problems.append('%s view runs off the drawing area' % n)
        elif _overlap(boxes[n], rev):
            problems.append('%s view runs into the rev table' % n)
    names = list(frames)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _overlap(boxes[a], boxes[b]):
                problems.append('%s and %s views overlap' % (a, b))
    return {'frames': frames, 'problems': problems}


def auto_scales(extents, rev_rect, region=REGION, gap=GAP):
    """(sheet scale, trimetric scale) as (value, label): the default before anyone picks."""
    std = [n for n in ('front', 'top', 'right')]
    for s, label in STD_SCALES:
        plan = arrange({n: extents[n] for n in std}, {n: s for n in std}, s, rev_rect, region, gap)
        if not plan['problems']:
            break
    else:
        raise ValueError('the views do not fit on one size B sheet at any standard scale')
    tri = None
    if 'trimetric' in extents:
        for s2, label2 in STD_SCALES:
            scales = {n: s for n in std}
            scales['trimetric'] = s2
            plan = arrange(extents, scales, s, rev_rect, region, gap)
            if not plan['problems']:
                tri = (s2, label2)
                break
    return (s, label), tri


def layout(extents, rev_rect, region=REGION, gap=GAP):
    """Default frames and scales. extents: name -> (u0, u1, v0, v1)."""
    (s, label), tri = auto_scales(extents, rev_rect, region, gap)
    scales = {n: s for n in ('front', 'top', 'right')}
    if tri:
        scales['trimetric'] = tri[0]
    plan = arrange({n: extents[n] for n in scales}, scales, s, rev_rect, region, gap)
    out = {'scale': s, 'label': label, 'frames': {n: plan['frames'][n] for n in ('front', 'top', 'right')}}
    if tri:
        out['trimetric'] = {'scale': tri[0], 'label': tri[1], 'frame': plan['frames']['trimetric']}
    return out


def relayout(doc, sheet_id=None):
    """Lay out the generated views of one sheet again at their current scales.

    Works on the drawing dict in place (commands pass doc.sheets). Views without
    registered lines are left where they are. Returns the problems list."""
    from .annotate import scale_value
    from .model import sheet_scale
    sheets = doc.sheets
    sheet = next((sh for sh in sheets if sheet_id in (None, sh.get('id'))), None)
    if sheet is None:
        raise ValueError('no sheet %r' % sheet_id)
    sheet_value = scale_value(sheet_scale(doc, sheet)) or 1.0
    els, extents, scales = {}, {}, {}
    for el in sheet.get('elements') or []:
        if el.get('type') != 'view':
            continue
        geom = view_geometry(el.get('geom'))
        name = geom and geom.get('name')
        if name not in VIEW_NAMES:
            continue
        els[name] = el
        extents[name] = geom['extent']
        scales[name] = scale_value(el.get('scale')) or sheet_value
    if not all(n in els for n in ('front', 'top', 'right')):
        return []
    plan = arrange(extents, scales, sheet_value, revlog_rect(doc.revlog))
    for name, (x, y, w, h) in plan['frames'].items():
        el = els[name]
        el['x'], el['y'], el['w'], el['h'] = round(x, 4), round(y, 4), round(w, 4), round(h, 4)
    return plan['problems']


def _buffer(frame, px_per_mm):
    bw = int(min(MAX_BUF, max(240, math.ceil(frame[2] * px_per_mm))))
    bh = int(min(MAX_BUF, max(180, math.ceil(frame[3] * px_per_mm))))
    return bw, bh


def reproject_sharper(parts, doc, sheet_id=None, px_per_mm=PX_PER_MM, factor=1.25):
    """Project again the generated views whose scale outgrew their depth buffer.

    After a view is made bigger (set_view_scale) its lines were found on a
    coarser buffer. Returns [(name, seconds)] for the views redone."""
    from .annotate import scale_value
    from .model import sheet_scale
    if isinstance(doc, dict):
        doc = DrawingDocument.from_dict(doc)
    out = []
    for sheet in doc.sheets:
        if sheet_id not in (None, sheet.get('id')):
            continue
        sv = scale_value(sheet_scale(doc, sheet)) or 1.0
        for el in sheet.get('elements') or []:
            geom = view_geometry(el.get('geom')) if el.get('type') == 'view' else None
            if not geom or geom.get('name') not in VIEW_NAMES:
                continue
            s = scale_value(el.get('scale')) or sv
            have = geom.get('px_per_model_mm') or 0.0
            bw, bh = _buffer((0, 0, float(el['w']), float(el['h'])), px_per_mm)
            want = min(bw / max(geom['extent'][1] - geom['extent'][0], 1e-6),
                       bh / max(geom['extent'][3] - geom['extent'][2], 1e-6))
            if want <= have * factor or s <= 0:
                continue
            t = time.perf_counter()
            view = project_view(parts, geom['name'], buf_w=bw, buf_h=bh)
            register_view_geometry(el['geom'], view)
            out.append((geom['name'], time.perf_counter() - t))
    return out


def build_view_sheet(parts, title, key='asm', source='', date='', draft=1, px_per_mm=PX_PER_MM,
                     sheet_scale=None, view_scales=None):
    """(drawing dict, report). Four views of `parts` on one size B sheet.

    Default scales come from auto_scales. sheet_scale ('1:30') sets the sheet
    scale; view_scales ({'trimetric': '1:20'}) gives views their own scale."""
    from .annotate import scale_value
    from .commands import execute
    t0 = time.perf_counter()
    names = VIEW_NAMES
    extents = {n: view_extent(parts, n) for n in names}
    doc = None

    def run(command, **args):
        nonlocal doc
        out = execute(doc, command, args)
        doc = out['document']
        return out['result']

    run('add_sheet', id='s1', name='Sheet 1')
    for field, value in (('title', title), ('material', 'SEE BOM'), ('units', 'mm'),
                         ('source', source), ('date', date)):
        if value:
            run('set_title', field=field, value=value)
    if draft:
        run('set_draft', n=draft)
    rev = revlog_rect(DrawingDocument.from_dict(doc).revlog)
    try:
        (sv, _label), tri = auto_scales(extents, rev)
    except ValueError:
        if not sheet_scale:
            raise
        sv, tri = None, None
    if sheet_scale:
        sv = scale_value(sheet_scale)
        if sv is None:
            raise ValueError('sheet_scale must be a ratio like 1:30')
    scales = {n: sv for n in names}
    if tri and not sheet_scale:
        scales['trimetric'] = tri[0]
    for n, text in (view_scales or {}).items():
        if n not in scales:
            raise ValueError('no view %r' % n)
        scales[n] = sv if text in (None, '', 'sheet') else scale_value(text)
        if scales[n] is None:
            raise ValueError('scale for %s must be a ratio like 1:20' % n)
    plan = arrange(extents, scales, sv, rev)
    label = scale_label(sv)
    run('set_title', field='scale', value=label)
    report = {'scale': label, 'views': [], 'problems': plan['problems']}
    was = gc.isenabled()
    gc.disable()
    try:
        for n in names:
            frame = plan['frames'][n]
            bw, bh = _buffer(frame, px_per_mm)
            t = time.perf_counter()
            view = project_view(parts, n, buf_w=bw, buf_h=bh)
            dt = time.perf_counter() - t
            gkey = register_view_geometry('%s:%s' % (key, n), view)
            args = dict(id='v_' + n, sheet='s1', x=frame[0], y=frame[1], w=frame[2], h=frame[3],
                        label=n.upper(), geom=gkey)
            own = scale_label(scales[n])
            if abs(scales[n] - sv) > 1e-12:
                args['scale'] = own
            run('place_view', **args)
            report['views'].append({'name': n, 'seconds': dt, 'buffer': (bw, bh), 'lines': len(view['lines']),
                                    'scale': own})
    finally:
        if was:
            gc.enable()
    report['seconds'] = time.perf_counter() - t0
    return doc, report
