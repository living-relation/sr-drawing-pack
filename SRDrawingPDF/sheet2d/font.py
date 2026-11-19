"""DejaVu Sans, embedded in the PDF. Metrics come from the font file."""
import os
import struct

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
_FACES = {}


def _tables(data):
    count = struct.unpack('>H', data[4:6])[0]
    out = {}
    for i in range(count):
        tag, _sum, offset, length = struct.unpack('>4sIII', data[12 + i * 16:28 + i * 16])
        out[tag] = data[offset:offset + length]
    return out


def _cmap(table):
    _version, ntables = struct.unpack('>HH', table[:4])
    chosen = None
    for i in range(ntables):
        platform, encoding, offset = struct.unpack('>HHI', table[4 + i * 8:12 + i * 8])
        fmt = struct.unpack('>H', table[offset:offset + 2])[0]
        # Windows Unicode BMP (format 4) or full repertoire (format 12).
        if (platform, encoding, fmt) in ((3, 1, 4), (0, 3, 4), (3, 10, 12), (0, 4, 12)):
            rank = 2 if fmt == 12 else 1
            if chosen is None or rank > chosen[0]:
                chosen = (rank, fmt, offset)
    if chosen is None:
        raise ValueError('DejaVu font has no Unicode cmap')
    _rank, fmt, offset = chosen
    if fmt == 12:
        return _cmap12(table, offset)
    return _cmap4(table, offset)


def _cmap4(table, offset):
    seg_x2 = struct.unpack('>H', table[offset + 6:offset + 8])[0]
    seg = seg_x2 // 2
    end_at = offset + 14
    ends = struct.unpack('>%dH' % seg, table[end_at:end_at + 2 * seg])
    start_at = end_at + 2 * seg + 2
    starts = struct.unpack('>%dH' % seg, table[start_at:start_at + 2 * seg])
    delta_at = start_at + 2 * seg
    deltas = struct.unpack('>%dh' % seg, table[delta_at:delta_at + 2 * seg])
    range_at = delta_at + 2 * seg
    ranges = struct.unpack('>%dH' % seg, table[range_at:range_at + 2 * seg])
    mapping = {}
    for i in range(seg):
        start, end = starts[i], ends[i]
        if start == 0xFFFF:
            break
        for code in range(start, end + 1):
            if ranges[i] == 0:
                gid = (code + deltas[i]) & 0xFFFF
            else:
                pos = range_at + 2 * i + ranges[i] + 2 * (code - start)
                gid = struct.unpack('>H', table[pos:pos + 2])[0]
                if gid:
                    gid = (gid + deltas[i]) & 0xFFFF
            if gid:
                mapping[code] = gid
    return mapping


def _cmap12(table, offset):
    ngroups = struct.unpack('>I', table[offset + 12:offset + 16])[0]
    mapping = {}
    pos = offset + 16
    for _i in range(ngroups):
        start, end, glyph = struct.unpack('>III', table[pos:pos + 12])
        pos += 12
        for code in range(start, end + 1):
            mapping[code] = glyph + (code - start)
    return mapping


class Face(object):
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        tables = _tables(self.data)
        head = tables[b'head']
        self.upem = struct.unpack('>H', head[18:20])[0]
        self.bbox = struct.unpack('>hhhh', head[36:44])
        hhea = tables[b'hhea']
        self.ascent, self.descent = struct.unpack('>hh', hhea[4:8])
        nmetrics = struct.unpack('>H', hhea[34:36])[0]
        maxp = tables[b'maxp']
        nglyphs = struct.unpack('>H', maxp[4:6])[0]
        hmtx = tables[b'hmtx']
        advances = []
        for i in range(nmetrics):
            advances.append(struct.unpack('>H', hmtx[i * 4:i * 4 + 2])[0])
        if advances:
            advances.extend([advances[-1]] * (nglyphs - nmetrics))
        self.advances = advances
        os2 = tables.get(b'OS/2')
        cap = None
        if os2 and len(os2) >= 90 and struct.unpack('>H', os2[:2])[0] >= 2:
            cap = struct.unpack('>h', os2[88:90])[0]
        self.cap = cap or int(self.upem * 0.72)
        self.cmap = _cmap(tables[b'cmap'])
        self._widths = None
        self._tounicode = None

    def glyph_id(self, char):
        return self.cmap.get(ord(char), 0)

    def has(self, char):
        return ord(char) in self.cmap

    def width_mm(self, text, h_mm):
        total = 0
        for char in text:
            total += self.advances[self.glyph_id(char)]
        return total * float(h_mm) / float(self.cap)

    def glyphs(self, text):
        ids = []
        missing = []
        for char in text:
            gid = self.glyph_id(char)
            if gid == 0 and char != '\x00':
                if ord(char) not in self.cmap:
                    missing.append(char)
            ids.append(gid)
        return ids, missing

    def width_pdf(self):
        """CID width array in 1000-em units. Cached."""
        if self._widths is None:
            scale = 1000.0 / self.upem
            parts = []
            gid = 0
            chunk = 64
            while gid < len(self.advances):
                nums = [str(int(round(a * scale))) for a in self.advances[gid:gid + chunk]]
                parts.append('%d [%s]' % (gid, ' '.join(nums)))
                gid += chunk
            self._widths = ' '.join(parts)
        return self._widths

    def tounicode(self):
        if self._tounicode is None:
            lines = [
                '/CIDInit /ProcSet findresource begin',
                '12 dict begin',
                'begincmap',
                '/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> def',
                '/CMapName /DejaVu-UTF16 def',
                '/CMapType 2 def',
                '1 begincodespacerange',
                '<0000> <FFFF>',
                'endcodespacerange',
            ]
            pairs = []
            for code, gid in sorted(self.cmap.items()):
                if gid <= 0 or gid > 0xFFFF or code > 0x10FFFF:
                    continue
                if code > 0xFFFF:
                    high = 0xD800 + ((code - 0x10000) >> 10)
                    low = 0xDC00 + ((code - 0x10000) & 0x3FF)
                    uni = '%04X%04X' % (high, low)
                else:
                    uni = '%04X' % code
                pairs.append('<%04X> <%s>' % (gid, uni))
            for i in range(0, len(pairs), 100):
                block = pairs[i:i + 100]
                lines.append('%d beginbfchar' % len(block))
                lines.extend(block)
                lines.append('endbfchar')
            lines.extend(['endcmap', 'CMapName currentdict /CMap defineresource pop', 'end', 'end'])
            self._tounicode = ('\n'.join(lines) + '\n').encode('ascii')
        return self._tounicode


def face(bold=False):
    key = 'bold' if bold else 'regular'
    if key not in _FACES:
        name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
        _FACES[key] = Face(os.path.join(_DIR, name))
    return _FACES[key]


def text_width_mm(text, h_mm, bold=False):
    return face(bold).width_mm(str(text), h_mm)


def cap_ratio(bold=False):
    loaded = face(bold)
    return float(loaded.cap) / float(loaded.upem)
