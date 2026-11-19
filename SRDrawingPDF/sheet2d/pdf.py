"""Vector PDF using the standard Helvetica fonts (nothing to embed).

Page space is points, origin bottom left. Drawing space is millimetres.
"""
import math

from .canvas import STY

MM = 72.0 / 25.4
# Cap height / em for Helvetica. The sheet text height is the cap height,
# matching the  h * (72/25.4) / 0.72  size used by the drawings we copy.
_CAP = 0.718
_EM = 0.72

# Unicode code point -> width in 1000-em units. ASCII plus the symbols the
# tolerance block uses. Parsed once from the Adobe AFM metrics.
_REG = (
    '32:278,33:278,34:355,35:556,36:556,37:889,38:667,39:222,40:333,41:333,42:389,43:584,44:278,45:333,'
    '46:278,47:278,48:556,49:556,50:556,51:556,52:556,53:556,54:556,55:556,56:556,57:556,58:278,59:278,'
    '60:584,61:584,62:584,63:556,64:1015,65:667,66:667,67:722,68:722,69:667,70:611,71:778,72:722,73:278,'
    '74:500,75:667,76:556,77:833,78:722,79:778,80:667,81:778,82:722,83:667,84:611,85:722,86:667,87:944,'
    '88:667,89:667,90:611,91:278,92:278,93:278,94:469,95:556,96:222,97:556,98:556,99:500,100:556,101:556,'
    '102:278,103:556,104:556,105:222,106:222,107:500,108:222,109:833,110:556,111:556,112:556,113:556,'
    '114:333,115:500,116:278,117:556,118:500,119:722,120:500,121:500,122:500,123:334,124:260,125:334,'
    '126:584,176:400,177:584,181:556,8211:556,8212:1000,8216:222,8217:222,8220:333,8221:333,8226:350'
)
_BOLD = (
    '32:278,33:333,34:474,35:556,36:556,37:889,38:722,39:278,40:333,41:333,42:389,43:584,44:278,45:333,'
    '46:278,47:278,48:556,49:556,50:556,51:556,52:556,53:556,54:556,55:556,56:556,57:556,58:333,59:333,'
    '60:584,61:584,62:584,63:611,64:975,65:722,66:722,67:722,68:722,69:667,70:611,71:778,72:722,73:278,'
    '74:556,75:722,76:611,77:833,78:722,79:778,80:667,81:778,82:722,83:667,84:611,85:722,86:667,87:944,'
    '88:667,89:667,90:611,91:333,92:278,93:333,94:584,95:556,96:278,97:556,98:611,99:556,100:611,101:556,'
    '102:333,103:611,104:611,105:278,106:278,107:556,108:278,109:889,110:611,111:611,112:611,113:611,'
    '114:389,115:556,116:333,117:611,118:556,119:778,120:556,121:556,122:500,123:389,124:280,125:389,'
    '126:584,176:400,177:584,181:611,8211:556,8212:1000,8216:278,8217:278,8220:500,8221:500,8226:350'
)

# Unicode punctuation that WinAnsi stores in the 0x80-0x9F range.
_WIN = {
    0x2013: 0x96,
    0x2014: 0x97,
    0x2018: 0x91,
    0x2019: 0x92,
    0x201C: 0x93,
    0x201D: 0x94,
    0x2022: 0x95,
    0x20AC: 0x80,
}


def _widths(spec):
    out = {}
    for part in spec.split(','):
        k, v = part.split(':')
        out[int(k)] = int(v)
    return out


REG_W = _widths(_REG)
BOLD_W = _widths(_BOLD)


def font_pt(h_mm):
    return h_mm * MM / _EM


def text_width_mm(text, h_mm, bold=False):
    table = BOLD_W if bold else REG_W
    units = 0
    for ch in str(text):
        units += table.get(ord(ch), 500)
    return (units / 1000.0 * font_pt(h_mm)) / MM


def to_winansi(text):
    out = bytearray()
    for ch in str(text):
        o = ord(ch)
        if o in _WIN:
            out.append(_WIN[o])
        elif o < 128 or (160 <= o <= 255):
            out.append(o)
        else:
            out.append(ord('?'))
    return bytes(out)


def _escape(raw):
    parts = []
    for b in raw:
        if b in (0x5C, 0x28, 0x29):
            parts.append('\\' + chr(b))
        elif 32 <= b < 127:
            parts.append(chr(b))
        else:
            parts.append('\\%03o' % b)
    return ''.join(parts)


def _text_op(x_mm, y_mm, text, h_mm, bold, rot):
    size = font_pt(h_mm)
    face = 'F2' if bold else 'F1'
    esc = _escape(to_winansi(text))
    if not rot:
        return 'BT /%s %.2f Tf %.3f %.3f Td (%s) Tj ET' % (face, size, x_mm * MM, y_mm * MM, esc)
    ang = math.radians(rot)
    c, s = math.cos(ang), math.sin(ang)
    return 'BT /%s %.2f Tf %.4f %.4f %.4f %.4f %.3f %.3f Tm (%s) Tj ET' % (
        face, size, c, s, -s, c, x_mm * MM, y_mm * MM, esc)


def _draw_text(ops, x, y, text, h, ha, va, rot, bold):
    lines = str(text).split('\n')
    pitch = h * 1.6
    cap = _CAP / _EM * h
    n = len(lines)
    if va == 'top':
        base0 = y - cap
    elif va == 'bottom':
        base0 = y + pitch * (n - 1)
    else:
        block = pitch * (n - 1)
        base0 = y + block / 2.0 - cap / 2.0
    for i, line in enumerate(lines):
        if line == '':
            continue
        tw = text_width_mm(line, h, bold)
        if ha == 'left':
            lx = x
        elif ha == 'right':
            lx = x - tw
        else:
            lx = x - tw / 2.0
        ly = base0 - i * pitch
        ops.append(_text_op(lx, ly, line, h, bold, rot or 0))


def _watermark(ops, text, h, cx, cy, angle):
    tw = text_width_mm(text, h, True)
    cap = _CAP / _EM * h
    ang = math.radians(angle)
    c, s = math.cos(ang), math.sin(ang)
    x = cx - c * (tw / 2.0) + s * (cap / 2.0)
    y = cy - s * (tw / 2.0) - c * (cap / 2.0)
    ops.append('q 0.72 g')
    ops.append(_text_op(x, y, text, h, True, angle))
    ops.append('Q')


def _poly(pts, close, op):
    x, y = pts[0]
    parts = ['%.3f %.3f m' % (x * MM, y * MM)]
    for px, py in pts[1:]:
        parts.append('%.3f %.3f l' % (px * MM, py * MM))
    if close:
        parts.append('h')
    parts.append(op)
    return ' '.join(parts)


def page_stream(sheet):
    """Content stream bytes for one sheet."""
    ops = ['0 g 0 G 1 J 1 j']
    marks = [it for it in sheet.items if it[0] == 'wm']
    for it in marks:
        _, x, y, text, h, ang = it
        _watermark(ops, text, h, x, y, ang)
    ops.append('0 g 0 G')
    for it in sheet.items:
        kind = it[0]
        if kind == 'wm':
            continue
        if kind == 'pl':
            _, pts, sty, closed = it
            width, dash = STY[sty]
            ops.append('%.3f w' % (width * MM))
            if dash:
                ops.append('[%s] 0 d' % ' '.join('%.3f' % (d * MM) for d in dash))
            else:
                ops.append('[] 0 d')
            if len(pts) >= 2:
                ops.append(_poly(pts, closed, 'S'))
        elif kind == 'tri':
            ops.append('0 g')
            ops.append(_poly(it[1], True, 'f'))
        elif kind == 'tx':
            _, x, y, text, h, ha, va, rot, bold, bg, _layer = it
            if bg and text:
                tw = text_width_mm(text, h, bold)
                cap = _CAP / _EM * h
                if ha == 'left':
                    lx = x
                elif ha == 'right':
                    lx = x - tw
                else:
                    lx = x - tw / 2.0
                ops.append('q 1 g %.3f %.3f %.3f %.3f re f Q' % (
                    (lx - 0.4) * MM, (y - 0.3) * MM, (tw + 0.8) * MM, (cap + 0.4) * MM))
            _draw_text(ops, x, y, text, h, ha, va, rot, bold)
    data = ('\n'.join(ops) + '\n').encode('ascii')
    return data


def write_pdf(sheets, path):
    """Write sheets (canvas.Sheet with page_size in mm) to a PDF file."""
    contents = []
    for sh in sheets:
        w_mm, h_mm = sh.page_size
        contents.append((w_mm * MM, h_mm * MM, page_stream(sh)))
    n = len(contents)
    # 1 catalog, 2 pages, then content, page, content, page, ...
    blobs = {}
    kids = []
    for i, (w, h, data) in enumerate(contents):
        cid = 3 + i
        pid = 3 + n + i
        blobs[cid] = _stream(cid, data)
        blobs[pid] = _page(pid, 2, cid, w, h)
        kids.append(pid)
    blobs[2] = _pages(2, kids)
    blobs[1] = _catalog(1, 2)
    objects = [blobs[i] for i in range(1, 3 + 2 * n)]
    _write_objects(path, objects)
    return path


def _stream(num, data):
    head = ('%d 0 obj\n<< /Length %d >>\nstream\n' % (num, len(data))).encode('ascii')
    return head + data + b'endstream\nendobj\n'


def _page(num, parent, content, w, h):
    return (
        '%d 0 obj\n<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] '
        '/Contents %d 0 R /Resources << /Font << '
        '/F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> '
        '/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >> '
        '>> >> >>\nendobj\n' % (num, parent, w, h, content)
    ).encode('ascii')


def _pages(num, kids):
    refs = ' '.join('%d 0 R' % k for k in kids)
    return ('%d 0 obj\n<< /Type /Pages /Kids [%s] /Count %d >>\nendobj\n' % (num, refs, len(kids))).encode('ascii')


def _catalog(num, pages):
    return ('%d 0 obj\n<< /Type /Catalog /Pages %d 0 R >>\nendobj\n' % (num, pages)).encode('ascii')


def _write_objects(path, objects):
    out = bytearray(b'%PDF-1.4\n')
    offsets = []
    for obj in objects:
        offsets.append(len(out))
        out += obj if isinstance(obj, bytes) else obj.encode('ascii')
    xref_at = len(out)
    n = len(objects) + 1
    xref = ['xref', '0 %d' % n, '0000000000 65535 f ']
    for off in offsets:
        xref.append('%010d 00000 n ' % off)
    trailer = 'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (n, xref_at)
    out += ('\n'.join(xref) + '\n').encode('ascii')
    out += trailer.encode('ascii')
    with open(path, 'wb') as f:
        f.write(out)
