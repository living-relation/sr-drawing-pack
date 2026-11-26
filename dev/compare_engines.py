"""Run each view engine on one STEP file.

  python dev/compare_engines.py --step assembly.step --out folder

Writes engines.png (one column per engine, four views) and engines.json.
The json separates read time from view time, cold and cached. An engine
that cannot run is named in the json and left blank in the picture.

The old mesh line engine is not included.
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, 'SRDrawingPDF'))

from sheet2d.engines import engine_names, get_engine  # noqa: E402
from sheet2d.project import VIEW_NAMES  # noqa: E402


def run_engine(engine, step, names):
    """(cold timing, cached timing, views). Views are None when it cannot run."""
    ok, why = engine.available()
    if not ok:
        return {'available': False, 'reason': why}, None, None
    t0 = time.perf_counter()
    views, timing = engine.project_views(names, step=step, mode='exact')
    timing = dict(timing)
    timing['wall_s'] = round(time.perf_counter() - t0, 3)
    t1 = time.perf_counter()
    _views2, cached = engine.project_views(names, step=step, mode='exact')
    cached = dict(cached)
    cached['wall_s'] = round(time.perf_counter() - t1, 3)
    return {'available': True, 'cold': _public(timing), 'cached': _public(cached)}, views, cached


def _public(timing):
    return {
        'read_s': timing.get('read_s'),
        'views_s': timing.get('views_s'),
        'total_s': timing.get('total_s'),
        'wall_s': timing.get('wall_s'),
        'from_step': timing.get('from_step'),
    }


def build_report(step, names=VIEW_NAMES):
    engines = {}
    pictures = {}
    for name in engine_names():
        row, views, _cached = run_engine(get_engine(name), step, names)
        engines[name] = row
        pictures[name] = views
    return {'step': os.path.basename(step or ''), 'views': list(names), 'engines': engines}, pictures


def write_png(path, pictures, names):
    """One column of views per engine. A blank column means that engine did not run."""
    cols = list(pictures)
    cell = 280
    gap = 12
    width = gap + len(cols) * (cell + gap)
    height = gap + cell + len(names) * (cell + gap)
    rgb = bytearray([255]) * (width * height * 3)
    for c, eng in enumerate(cols):
        x0 = gap + c * (cell + gap)
        _label_bar(rgb, width, height, x0, gap, cell, 18)
        views = pictures.get(eng)
        for r, name in enumerate(names):
            y0 = gap + cell + r * (cell + gap)
            _box(rgb, width, height, x0, y0, cell, cell)
            if not views or name not in views:
                continue
            _draw_view(rgb, width, height, x0 + 8, y0 + 8, cell - 16, views[name].get('lines') or [])
    _write_png(path, width, height, rgb)


def _label_bar(rgb, width, height, x, y, w, h):
    _box(rgb, width, height, x, y, w, h)


def _box(rgb, width, height, x, y, w, h):
    for yy in range(int(y), int(y + h)):
        if yy < 0 or yy >= height:
            continue
        for xx in range(int(x), int(x + w)):
            if 0 <= xx < width:
                i = (yy * width + xx) * 3
                rgb[i:i + 3] = b'\x22\x22\x22' if (yy in (int(y), int(y + h - 1)) or xx in (int(x), int(x + w - 1))) else rgb[i:i + 3]


def _draw_view(rgb, width, height, x, y, size, lines):
    pts = []
    for line in lines:
        pts.extend(_pts(line))
    if len(pts) < 2:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    u0, u1, v0, v1 = min(xs), max(xs), min(ys), max(ys)
    scale = (size - 4) / max(u1 - u0, v1 - v0, 1e-6)

    def pix(p):
        return (int(x + (p[0] - u0) * scale), int(y + size - (p[1] - v0) * scale))

    for line in lines:
        chain = _pts(line)
        for a, b in zip(chain, chain[1:]):
            _seg(rgb, width, height, pix(a), pix(b))


def _pts(line):
    import math
    if line.get('kind') == 'circle':
        cx, cy = line['c']
        r = line['r']
        return [(cx + r * math.cos(2 * math.pi * i / 24), cy + r * math.sin(2 * math.pi * i / 24)) for i in range(25)]
    if line.get('kind') == 'ellipse':
        cx, cy = line['c']
        rx, ry = line['rx'], line['ry']
        rot = line.get('rot') or 0.0
        c, s = math.cos(rot), math.sin(rot)
        out = []
        for i in range(25):
            t = 2 * math.pi * i / 24
            lx, ly = rx * math.cos(t), ry * math.sin(t)
            out.append((cx + c * lx - s * ly, cy + s * lx + c * ly))
        return out
    return list(line.get('pts') or [])


def _seg(rgb, width, height, a, b):
    x0, y0 = a
    x1, y1 = b
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        x = int(x0 + (x1 - x0) * i / steps)
        y = int(y0 + (y1 - y0) * i / steps)
        if 0 <= x < width and 0 <= y < height:
            k = (y * width + x) * 3
            rgb[k:k + 3] = b'\x11\x11\x11'


def _write_png(path, w, h, rgb):
    import struct
    import zlib
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw.extend(rgb[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b'')
    with open(path, 'wb') as handle:
        handle.write(png)


def main(argv):
    step = None
    out = None
    args = list(argv[1:])
    while args:
        item = args.pop(0)
        if item == '--step' and args:
            step = args.pop(0)
        elif item == '--out' and args:
            out = args.pop(0)
        else:
            step = step or item
    if not step:
        print(__doc__)
        return 2
    out = out or os.path.dirname(os.path.abspath(step)) or '.'
    os.makedirs(out, exist_ok=True)
    report, pictures = build_report(step)
    json_path = os.path.join(out, 'engines.json')
    png_path = os.path.join(out, 'engines.png')
    with open(json_path, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=1)
        handle.write('\n')
    write_png(png_path, pictures, report['views'])
    print(json_path)
    print(png_path)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
