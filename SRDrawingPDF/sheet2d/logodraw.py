"""Turn a title-block logo into PDF drawing commands.

PNG bytes become an RGB image (with an alpha mask when the file has one).
SVG is drawn as vectors: rectangles, circles, ellipses, lines, polylines,
polygons, paths, and text. Coordinates come back in sheet millimetres,
origin at the bottom left, already placed in the logo box.
"""
import base64
import math
import re
import struct
import zlib
from urllib.parse import unquote
from xml.etree import ElementTree as ET

_NUM = re.compile(r'[+-]?(?:\d+\.\d+|\d+\.|\.\d+|\d+)(?:[eE][+-]?\d+)?')


def logo_chars(data):
    """Characters an SVG logo draws, so the PDF font includes them."""
    kind, body = _open(data)
    if kind != 'svg':
        return ''
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return ''
    return ''.join(root.itertext())


def prepare(data, x, y, w, h):
    """A logo ready to draw.

    Returns {'image': (width, height, rgb, alpha or None) or None,
             'paths': [...], 'texts': [...]}.
    Paths are lists of ('M', x, y), ('L', x, y), ('C', x1, y1, x2, y2, x, y)
    in sheet millimetres. Texts are (x, y, text, cap_mm, (r, g, b), anchor).
    """
    kind, body = _open(data)
    if kind == 'png':
        return {'image': _decode_png(body), 'paths': [], 'texts': []}
    paths, texts = _svg(body, float(x), float(y), float(w), float(h))
    if not paths and not texts:
        raise ValueError('the SVG logo has nothing to draw')
    return {'image': None, 'paths': paths, 'texts': texts}


def _open(data):
    if isinstance(data, bytes):
        if data.startswith(b'\x89PNG'):
            return 'png', data
        text = data.decode('utf-8', 'replace').strip()
    else:
        text = str(data or '').strip()
    if not text:
        raise ValueError('the logo has no image data')
    if text.startswith('data:'):
        header, _, body = text.partition(',')
        raw = base64.b64decode(body) if ';base64' in header else unquote(body).encode('utf-8')
        if 'svg' in header or raw.lstrip().startswith(b'<svg') or raw.lstrip().startswith(b'<?xml'):
            return 'svg', raw.decode('utf-8')
        return 'png', raw
    if text.lstrip().startswith('<svg') or text.lstrip().startswith('<?xml'):
        return 'svg', text
    raise ValueError('a logo must be a PNG or an SVG')


def _decode_png(blob):
    if not blob.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('logo PNG is not a PNG')
    pos = 8
    width = height = bit = color = None
    palette = trns = None
    idat = []
    while pos + 8 <= len(blob):
        length = struct.unpack('>I', blob[pos:pos + 4])[0]
        tag = blob[pos + 4:pos + 8]
        chunk = blob[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b'IHDR':
            width, height, bit, color, _comp, _filt, interlace = struct.unpack('>IIBBBBB', chunk[:13])
            if interlace:
                raise ValueError('logo PNG cannot be interlaced')
            if bit != 8:
                raise ValueError('logo PNG must be 8 bits per channel')
        elif tag == b'PLTE':
            palette = chunk
        elif tag == b'tRNS':
            trns = chunk
        elif tag == b'IDAT':
            idat.append(chunk)
        elif tag == b'IEND':
            break
    if not width or not idat:
        raise ValueError('logo PNG is incomplete')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if channels is None:
        raise ValueError('logo PNG uses an unsupported color type')
    raw = zlib.decompress(b''.join(idat))
    stride = width * channels
    rows = []
    prev = bytearray(stride)
    i = 0
    for _y in range(height):
        filt = raw[i]
        i += 1
        row = bytearray(raw[i:i + stride])
        i += stride
        _unfilter(filt, row, prev, channels)
        prev = row
        rows.append(bytes(row))
    rgb = bytearray()
    alpha = bytearray()
    has_alpha = False
    for row in rows:
        if color == 2:
            rgb += row
        elif color == 6:
            has_alpha = True
            for p in range(width):
                rgb += row[p * 4:p * 4 + 3]
                alpha.append(row[p * 4 + 3])
        elif color == 0:
            for b in row:
                rgb += bytes((b, b, b))
        elif color == 4:
            has_alpha = True
            for p in range(width):
                b = row[p * 2]
                rgb += bytes((b, b, b))
                alpha.append(row[p * 2 + 1])
        else:
            if palette is None:
                raise ValueError('logo PNG has no palette')
            for idx in row:
                rgb += palette[idx * 3:idx * 3 + 3]
                if trns is not None:
                    has_alpha = True
                    alpha.append(trns[idx] if idx < len(trns) else 255)
    return width, height, bytes(rgb), (bytes(alpha) if has_alpha else None)


def _unfilter(filt, row, prev, channels):
    n = len(row)
    if filt == 0:
        return
    if filt == 1:
        for i in range(n):
            left = row[i - channels] if i >= channels else 0
            row[i] = (row[i] + left) & 255
        return
    if filt == 2:
        for i in range(n):
            row[i] = (row[i] + prev[i]) & 255
        return
    if filt == 3:
        for i in range(n):
            left = row[i - channels] if i >= channels else 0
            row[i] = (row[i] + ((left + prev[i]) // 2)) & 255
        return
    if filt == 4:
        for i in range(n):
            left = row[i - channels] if i >= channels else 0
            up = prev[i]
            ul = prev[i - channels] if i >= channels else 0
            row[i] = (row[i] + _paeth(left, up, ul)) & 255
        return
    raise ValueError('logo PNG has a bad filter')


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _svg(text, x, y, w, h):
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError('logo SVG could not be read: %s' % exc)
    vb = _viewbox(root)
    paths, texts = [], []
    _walk(root, (1, 0, 0, 1, 0, 0), _style(root), vb, (x, y, w, h), paths, texts)
    return paths, texts


def _viewbox(root):
    raw = root.get('viewBox') or root.get('viewbox')
    if raw:
        nums = [float(n) for n in _NUM.findall(raw)]
        if len(nums) == 4 and nums[2] > 0 and nums[3] > 0:
            return nums
    width = _len(root.get('width'), 100.0)
    height = _len(root.get('height'), 100.0)
    return [0.0, 0.0, width or 100.0, height or 100.0]


def _walk(el, matrix, inherited, vb, box, paths, texts):
    matrix = _mul(matrix, _transform(el.get('transform')))
    style = dict(inherited)
    style.update(_style(el))
    name = el.tag.rsplit('}', 1)[-1]
    if name == 'rect':
        _rect(el, matrix, style, vb, box, paths)
    elif name == 'circle':
        _ellipse(el, matrix, style, vb, box, paths, _num_attr(el, 'r', 0), _num_attr(el, 'r', 0))
    elif name == 'ellipse':
        _ellipse(el, matrix, style, vb, box, paths, _num_attr(el, 'rx', 0), _num_attr(el, 'ry', 0))
    elif name == 'line':
        _line(el, matrix, style, vb, box, paths)
    elif name in ('polyline', 'polygon'):
        _poly(el, matrix, style, vb, box, paths, name == 'polygon')
    elif name == 'path':
        _path(el, matrix, style, vb, box, paths)
    elif name == 'text':
        _text(el, matrix, style, vb, box, texts)
    for child in list(el):
        _walk(child, matrix, style, vb, box, paths, texts)


def _rect(el, matrix, style, vb, box, paths):
    rx = _num_attr(el, 'x', 0)
    ry = _num_attr(el, 'y', 0)
    rw = _num_attr(el, 'width', 0)
    rh = _num_attr(el, 'height', 0)
    if rw <= 0 or rh <= 0:
        return
    pts = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)]
    segs = [('M',) + _map(pts[0], matrix, vb, box)]
    for pt in pts[1:]:
        segs.append(('L',) + _map(pt, matrix, vb, box))
    segs.append(('Z',))
    _add(paths, segs, style, vb, box)


def _ellipse(el, matrix, style, vb, box, paths, rx, ry):
    if rx <= 0 or ry <= 0:
        return
    cx, cy = _num_attr(el, 'cx', 0), _num_attr(el, 'cy', 0)
    k = 0.551784
    segs = [('M',) + _map((cx + rx, cy), matrix, vb, box)]
    cubics = (
        ((cx + rx, cy + ry * k), (cx + rx * k, cy + ry), (cx, cy + ry)),
        ((cx - rx * k, cy + ry), (cx - rx, cy + ry * k), (cx - rx, cy)),
        ((cx - rx, cy - ry * k), (cx - rx * k, cy - ry), (cx, cy - ry)),
        ((cx + rx * k, cy - ry), (cx + rx, cy - ry * k), (cx + rx, cy)),
    )
    for c1, c2, end in cubics:
        segs.append(('C',) + _map(c1, matrix, vb, box) + _map(c2, matrix, vb, box) + _map(end, matrix, vb, box))
    segs.append(('Z',))
    _add(paths, segs, style, vb, box)


def _line(el, matrix, style, vb, box, paths):
    a = _map((_num_attr(el, 'x1', 0), _num_attr(el, 'y1', 0)), matrix, vb, box)
    b = _map((_num_attr(el, 'x2', 0), _num_attr(el, 'y2', 0)), matrix, vb, box)
    style = dict(style)
    if style.get('stroke') is None and style.get('fill') is None:
        style['stroke'] = (0, 0, 0)
    _add(paths, [('M',) + a, ('L',) + b], style, vb, box)


def _poly(el, matrix, style, vb, box, paths, close):
    nums = [float(n) for n in _NUM.findall(el.get('points') or '')]
    if len(nums) < 4:
        return
    pts = list(zip(nums[0::2], nums[1::2]))
    segs = [('M',) + _map(pts[0], matrix, vb, box)]
    for pt in pts[1:]:
        segs.append(('L',) + _map(pt, matrix, vb, box))
    if close:
        segs.append(('Z',))
    _add(paths, segs, style, vb, box)


def _path(el, matrix, style, vb, box, paths):
    segs = []
    cur = start = None
    prev_ctrl = None
    cmd = None
    nums = []
    tokens = _tokens(el.get('d') or '')
    i = 0

    def take(n):
        nonlocal i
        if i + n > len(tokens) or any(isinstance(tokens[i + k], str) for k in range(n)):
            return None
        got = tokens[i:i + n]
        i += n
        return got

    while i < len(tokens):
        tok = tokens[i]
        if isinstance(tok, str):
            cmd = tok
            i += 1
            nums = []
        if cmd is None:
            break
        rel = cmd.islower()
        op = cmd.upper()
        if op == 'Z':
            segs.append(('Z',))
            cur = start
            prev_ctrl = None
            cmd = None
            continue
        need = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2, 'A': 7}.get(op)
        if need is None:
            cmd = None
            continue
        got = take(need)
        if got is None:
            cmd = None
            continue
        if rel and cur is not None:
            if op == 'H':
                got[0] += cur[0]
            elif op == 'V':
                got[0] += cur[1]
            elif op == 'A':
                got[5] += cur[0]
                got[6] += cur[1]
            else:
                for k in range(0, len(got), 2):
                    got[k] += cur[0]
                    got[k + 1] += cur[1]
        if op == 'M':
            cur = (got[0], got[1])
            start = cur
            segs.append(('M',) + _map(cur, matrix, vb, box))
            cmd = 'l' if rel else 'L'
            prev_ctrl = None
        elif op == 'L':
            cur = (got[0], got[1])
            segs.append(('L',) + _map(cur, matrix, vb, box))
            prev_ctrl = None
        elif op == 'H':
            cur = (got[0], cur[1] if cur else 0)
            segs.append(('L',) + _map(cur, matrix, vb, box))
            prev_ctrl = None
        elif op == 'V':
            cur = (cur[0] if cur else 0, got[0])
            segs.append(('L',) + _map(cur, matrix, vb, box))
            prev_ctrl = None
        elif op in ('C', 'S'):
            if op == 'S':
                c1 = _reflect(prev_ctrl, cur)
                c2, end = (got[0], got[1]), (got[2], got[3])
            else:
                c1, c2, end = (got[0], got[1]), (got[2], got[3]), (got[4], got[5])
            segs.append(('C',) + _map(c1, matrix, vb, box) + _map(c2, matrix, vb, box) + _map(end, matrix, vb, box))
            prev_ctrl = c2
            cur = end
        elif op in ('Q', 'T'):
            if op == 'T':
                c = _reflect(prev_ctrl, cur)
                end = (got[0], got[1])
            else:
                c, end = (got[0], got[1]), (got[2], got[3])
            c1, c2 = _quad(cur, c, end)
            segs.append(('C',) + _map(c1, matrix, vb, box) + _map(c2, matrix, vb, box) + _map(end, matrix, vb, box))
            prev_ctrl = c
            cur = end
        elif op == 'A':
            end = (got[5], got[6])
            for c1, c2, pt in _arc(cur or (0, 0), got[0], got[1], got[2], got[3], got[4], end):
                segs.append(('C',) + _map(c1, matrix, vb, box) + _map(c2, matrix, vb, box) + _map(pt, matrix, vb, box))
            prev_ctrl = None
            cur = end
    if segs:
        _add(paths, segs, style, vb, box)


def _text(el, matrix, style, vb, box, texts):
    body = el.text or ''
    if not body.strip():
        return
    from .font import cap_ratio
    tx = _num_attr(el, 'x', 0)
    ty = _num_attr(el, 'y', 0)
    em = _num_attr(el, 'font-size', _len(style.get('font-size'), 16))
    px, py = _map((tx, ty), matrix, vb, box)
    # font-size is the em square. Sheet text height is the cap height.
    cap = em * (box[3] / vb[3]) * cap_ratio(False)
    anchor = (el.get('text-anchor') or style.get('text-anchor') or 'start').strip()
    ha = {'middle': 'center', 'end': 'right'}.get(anchor, 'left')
    fill = style.get('fill') if 'fill' in style else (0, 0, 0)
    if fill is None:
        return
    texts.append((px, py, body.strip(), cap, fill, ha))


def _tokens(d):
    out = []
    i = 0
    while i < len(d):
        c = d[i]
        if c.isalpha():
            out.append(c)
            i += 1
            continue
        if c in ' \t\r\n,':
            i += 1
            continue
        match = _NUM.match(d, i)
        if not match:
            i += 1
            continue
        out.append(float(match.group()))
        i = match.end()
    return out


def _quad(p0, p1, p2):
    c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
    c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
    return c1, c2


def _reflect(ctrl, cur):
    if ctrl is None or cur is None:
        return cur or (0, 0)
    return (2 * cur[0] - ctrl[0], 2 * cur[1] - ctrl[1])


def _arc(p0, rx, ry, phi_deg, large, sweep, p1):
    """SVG arc as cubic beziers. Returns (c1, c2, end) tuples in user space."""
    rx, ry = abs(rx), abs(ry)
    if rx < 1e-9 or ry < 1e-9 or p0 == p1:
        return []
    phi = math.radians(phi_deg)
    cos, sin = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2.0, (p0[1] - p1[1]) / 2.0
    x1 = cos * dx + sin * dy
    y1 = -sin * dx + cos * dy
    lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
    if lam > 1:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    sign = -1 if bool(large) == bool(sweep) else 1
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    coef = sign * math.sqrt(max(0.0, num / den)) if den else 0.0
    cxp, cyp = coef * rx * y1 / ry, -coef * ry * x1 / rx
    cx = cos * cxp - sin * cyp + (p0[0] + p1[0]) / 2.0
    cy = sin * cxp + cos * cyp + (p0[1] + p1[1]) / 2.0

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        n = math.hypot(ux, uy) * math.hypot(vx, vy)
        ang = math.acos(max(-1.0, min(1.0, dot / n))) if n else 0.0
        if ux * vy - uy * vx < 0:
            ang = -ang
        return ang

    t1 = angle(1, 0, (x1 - cxp) / rx, (y1 - cyp) / ry)
    dt = angle((x1 - cxp) / rx, (y1 - cyp) / ry, (-x1 - cxp) / rx, (-y1 - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    nseg = max(1, int(math.ceil(abs(dt) / (math.pi / 2))))
    step = dt / nseg
    out = []
    for i in range(nseg):
        a0 = t1 + i * step
        a1 = a0 + step
        alpha = math.tan(step / 2) * 4 / 3
        def point(a):
            return (
                cos * rx * math.cos(a) - sin * ry * math.sin(a) + cx,
                sin * rx * math.cos(a) + cos * ry * math.sin(a) + cy,
            )
        p_a = point(a0)
        p_b = point(a1) if i < nseg - 1 else p1
        c1 = (p_a[0] - alpha * (cos * rx * math.sin(a0) + sin * ry * math.cos(a0)),
              p_a[1] - alpha * (sin * rx * math.sin(a0) - cos * ry * math.cos(a0)))
        c2 = (p_b[0] + alpha * (cos * rx * math.sin(a1) + sin * ry * math.cos(a1)),
              p_b[1] + alpha * (sin * rx * math.sin(a1) - cos * ry * math.cos(a1)))
        out.append((c1, c2, p_b))
    return out


def _add(paths, segs, style, vb, box):
    # SVG fills shapes black unless the file says otherwise. Stroke is off unless asked.
    fill = style['fill'] if 'fill' in style else (0, 0, 0)
    stroke = style['stroke'] if 'stroke' in style else None
    if fill is None and stroke is None:
        return
    sw = _len(style.get('stroke-width'), 1.0)
    scale = ((box[2] / vb[2]) + (box[3] / vb[3])) / 2.0
    paths.append({'segs': segs, 'fill': fill, 'stroke': stroke, 'width': max(0.05, sw * scale)})


def _map(pt, matrix, vb, box):
    a, b, c, d, e, f = matrix
    x, y = a * pt[0] + c * pt[1] + e, b * pt[0] + d * pt[1] + f
    bx, by, bw, bh = box
    vx, vy, vw, vh = vb
    return (
        bx + (x - vx) / vw * bw,
        by + bh - (y - vy) / vh * bh,
    )


def _mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1,
    )


def _transform(text):
    m = (1, 0, 0, 1, 0, 0)
    if not text:
        return m
    for name, args in re.findall(r'([a-zA-Z]+)\s*\(([^)]*)\)', text):
        nums = [float(n) for n in _NUM.findall(args)]
        if name == 'translate':
            tx = nums[0] if nums else 0
            ty = nums[1] if len(nums) > 1 else 0
            step = (1, 0, 0, 1, tx, ty)
        elif name == 'scale':
            sx = nums[0] if nums else 1
            sy = nums[1] if len(nums) > 1 else sx
            step = (sx, 0, 0, sy, 0, 0)
        elif name == 'matrix' and len(nums) >= 6:
            step = tuple(nums[:6])
        elif name == 'rotate' and nums:
            ang = math.radians(nums[0])
            cos, sin = math.cos(ang), math.sin(ang)
            step = (cos, sin, -sin, cos, 0, 0)
        else:
            continue
        m = _mul(m, step)
    return m


def _style(el):
    raw = {}
    if el.get('style'):
        for part in el.get('style').split(';'):
            if ':' in part:
                key, val = part.split(':', 1)
                raw[key.strip()] = val.strip()
    for key in ('fill', 'stroke', 'stroke-width', 'font-size', 'text-anchor'):
        if el.get(key) is not None:
            raw[key] = el.get(key)
    out = {}
    if 'fill' in raw:
        out['fill'] = _color(raw['fill'])
    if 'stroke' in raw:
        out['stroke'] = _color(raw['stroke'])
    if 'stroke-width' in raw:
        out['stroke-width'] = raw['stroke-width']
    if 'font-size' in raw:
        out['font-size'] = raw['font-size']
    if 'text-anchor' in raw:
        out['text-anchor'] = raw['text-anchor']
    return out


_NAMED = {
    'black': (0, 0, 0), 'white': (1, 1, 1), 'red': (1, 0, 0), 'green': (0, 0.5, 0),
    'blue': (0, 0, 1), 'none': None,
}


def _color(text):
    text = (text or '').strip().lower()
    if text in _NAMED:
        return _NAMED[text]
    if text.startswith('#') and len(text) == 4:
        return tuple(int(c * 2, 16) / 255.0 for c in text[1:])
    if text.startswith('#') and len(text) >= 7:
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    match = re.match(r'rgb\(\s*([0-9.]+%?)\s*,\s*([0-9.]+%?)\s*,\s*([0-9.]+%?)\s*\)', text)
    if match:
        vals = []
        for part in match.groups():
            if part.endswith('%'):
                vals.append(float(part[:-1]) / 100.0)
            else:
                vals.append(float(part) / 255.0)
        return tuple(vals)
    return (0, 0, 0)


def _num_attr(el, name, default):
    return _len(el.get(name), default)


def _len(text, default):
    if text is None or text == '':
        return float(default)
    match = _NUM.match(str(text).strip())
    return float(match.group()) if match else float(default)
