"""Title-block templates, one per sheet size.

This is the sheet-format editor SOLIDWORKS calls Edit Sheet Format
(https://help.solidworks.com/2021/english/SolidWorks/sldworks/c_sheet_formats.htm).
Boxes can be moved, resized, added and removed. A company logo is a picture
on the format. The drawing uses the template saved for its sheet size.

Company and project text still come from the design. An unknown name stays blank.
"""
import copy
import json
import os

# Landscape millimetres. ANSI A-D and ISO A-series.
SIZES = {
    'A': (279.4, 215.9, 'A (8.5x11)'),
    'B': (431.8, 279.4, 'B (11x17)'),
    'C': (558.8, 431.8, 'C (17x22)'),
    'D': (863.6, 558.8, 'D (22x34)'),
    'A4': (297.0, 210.0, 'A4'),
    'A3': (420.0, 297.0, 'A3'),
    'A2': (594.0, 420.0, 'A2'),
    'A1': (841.0, 594.0, 'A1'),
    'A0': (1189.0, 841.0, 'A0'),
}

FIELDS = (
    'project', 'title', 'pn', 'rev', 'material', 'scale', 'units', 'size',
    'sheet', 'date', 'drawn', 'source', 'tol', 'angle', 'static',
)

# The label sits in a band at the top of the box. The value stays below that band.
LABEL_H = 1.8
LABEL_TOP_GAP = 1.0
VALUE_GAP = 0.8


def standard_size(name):
    row = SIZES.get(name)
    if not row:
        return None
    width, height, label = row
    zones = [8, 4] if name == 'B' else [6, 4] if width < 450 else [8, 6]
    return {'width': width, 'height': height, 'label': label, 'zones': zones}


def default_template(size='B'):
    """The built-in format. Size B matches the title block the sheets already draw."""
    spec = standard_size(size)
    if spec is None:
        raise ValueError('unknown sheet size %r' % size)
    width, height = spec['width'], spec['height']
    margin = 10.0
    block_w, block_h, tol_w = 178.0, 52.0, 92.0
    room = width - 2 * margin
    scale = 1.0 if room >= block_w + tol_w else room / (block_w + tol_w)
    block_w *= scale
    block_h *= scale
    tol_w *= scale
    x1 = width - margin
    x0 = x1 - block_w
    y0 = margin
    y1 = y0 + block_h

    def box(bid, x, y, w, h, field, label):
        return {'id': bid, 'x': round(x, 3), 'y': round(y, 3), 'w': round(w, 3),
                'h': round(h, 3), 'field': field, 'label': label}

    boxes = [
        box('project', x0, y1 - 10 * scale, block_w, 10 * scale, 'project', 'COMPANY / PROJECT'),
        box('title', x0, y1 - 24 * scale, block_w, 14 * scale, 'title', 'TITLE'),
        box('pn', x0, y1 - 34 * scale, 90 * scale, 10 * scale, 'pn', 'PART / DWG NO.'),
        box('rev', x0 + 90 * scale, y1 - 34 * scale, 20 * scale, 10 * scale, 'rev', 'REV'),
        box('material', x0 + 110 * scale, y1 - 34 * scale, block_w - 110 * scale, 10 * scale, 'material', 'MATERIAL'),
        box('scale', x0, y0 + 8 * scale, 30 * scale, block_h - 42 * scale, 'scale', 'SCALE'),
        box('units', x0 + 30 * scale, y0 + 8 * scale, 22 * scale, block_h - 42 * scale, 'units', 'UNITS'),
        box('size', x0 + 52 * scale, y0 + 8 * scale, 28 * scale, block_h - 42 * scale, 'size', 'SIZE'),
        box('sheet', x0 + 80 * scale, y0 + 8 * scale, 28 * scale, block_h - 42 * scale, 'sheet', 'SHEET'),
        box('date', x0 + 108 * scale, y0 + 8 * scale, 32 * scale, block_h - 42 * scale, 'date', 'DATE'),
        box('drawn', x0 + 140 * scale, y0 + 8 * scale, block_w - 140 * scale, block_h - 42 * scale, 'drawn', 'DRAWN'),
        box('source', x0, y0, 140 * scale, 8 * scale, 'source', 'SOURCE'),
        box('angle', x0 + 140 * scale, y0, block_w - 140 * scale, 8 * scale, 'angle', '3RD ANGLE'),
        box('tol', x0 - tol_w, y0, tol_w, block_h, 'tol', 'BLOCK TOLERANCE'),
    ]
    return {
        'size': size, 'width': width, 'height': height,
        'boxes': boxes, 'logo': None,
    }


def field_text(field, info, sheet_no=1, n_sheets=1, static=''):
    """The words a box shows. An unknown company or project stays blank."""
    info = info or {}
    if field == 'sheet':
        return '%s OF %s' % (sheet_no, n_sheets)
    if field == 'size':
        return str(info.get('size') or '')
    if field == 'project':
        return info.get('project') or ''
    if field == 'angle':
        return '3RD ANGLE'
    if field == 'static':
        return static or ''
    if field == 'tol':
        return info.get('tol') or ''
    return str(info.get(field) or '')


def add_box(template, field='static', label='NOTE', x=20, y=20, w=40, h=12, text=''):
    if field not in FIELDS:
        raise ValueError('field must be one of %s' % ', '.join(FIELDS))
    out = copy.deepcopy(template)
    n = 1 + max([_num(b.get('id')) for b in out['boxes']] or [0])
    out['boxes'].append({
        'id': 'box%d' % n, 'x': float(x), 'y': float(y), 'w': float(w), 'h': float(h),
        'field': field, 'label': label or field.upper(), 'text': text or '',
    })
    return out


def move_box(template, box_id, x, y):
    return _edit(template, box_id, x=float(x), y=float(y))


def resize_box(template, box_id, w, h):
    if float(w) <= 0 or float(h) <= 0:
        raise ValueError('a box needs a width and a height')
    return _edit(template, box_id, w=float(w), h=float(h))


def remove_box(template, box_id):
    out = copy.deepcopy(template)
    before = len(out['boxes'])
    out['boxes'] = [b for b in out['boxes'] if b.get('id') != box_id]
    if len(out['boxes']) == before:
        raise ValueError('no box %r' % box_id)
    return out


def set_logo(template, name, data, x=None, y=None, w=40, h=16):
    """data is a data URI (PNG or SVG) or raw SVG text."""
    if not data:
        raise ValueError('a logo needs image data')
    kind = 'svg' if ('<svg' in str(data)[:400].lower() or str(data).startswith('data:image/svg')) else 'png'
    out = copy.deepcopy(template)
    width = out['width']
    out['logo'] = {
        'name': name or 'logo',
        'data': data,
        'kind': kind,
        # Top-left, inside the border. The top-right is the revision table.
        'x': float(14 if x is None else x),
        'y': float(out['height'] - 10 - h if y is None else y),
        'w': float(w), 'h': float(h),
    }
    return out


def clear_logo(template):
    out = copy.deepcopy(template)
    out['logo'] = None
    return out


def move_logo(template, x, y):
    if not template.get('logo'):
        raise ValueError('this format has no logo')
    out = copy.deepcopy(template)
    out['logo']['x'] = float(x)
    out['logo']['y'] = float(y)
    return out


def save_template(template, path):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(template, handle, indent=1)
        handle.write('\n')
    return path


def load_template(path):
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    if data.get('size') not in SIZES:
        raise ValueError('template size must be one of %s' % ', '.join(SIZES))
    if not isinstance(data.get('boxes'), list):
        raise ValueError('template needs boxes')
    return data


def attach_template(document, template):
    """Store the template on the drawing under its sheet size."""
    doc = copy.deepcopy(document)
    formats = dict(doc.get('formats') or {})
    formats[template['size']] = template
    doc['formats'] = formats
    return doc


def template_for(document, size):
    found = (document.get('formats') or {}).get(size) if isinstance(document, dict) else None
    if found is None and document is not None and not isinstance(document, dict):
        found = (getattr(document, 'formats', None) or {}).get(size)
    return found or default_template(size)


def label_rect(w, h, label):
    """The label's box, origin at the box bottom-left. It hugs the top edge."""
    from .font import text_width_mm
    tw = text_width_mm(label or '', LABEL_H, False)
    top = float(h) - LABEL_TOP_GAP
    return (1.0, top - LABEL_H, tw, LABEL_H)


def value_place(w, h, value, preferred, bold=False):
    """Center of the value, below the label. None when the box is only a label row.

    The returned rect is (left, bottom, width, height) in the same box space.
    Its top edge stays VALUE_GAP below the label.
    """
    text = (value or '').split('\n')[0]
    if not text:
        return None
    from .font import text_width_mm
    ceiling = float(h) - LABEL_TOP_GAP - LABEL_H - VALUE_GAP
    floor = 0.6
    if ceiling - floor < 1.5:
        return None
    size = min(float(preferred), (ceiling - floor) * 0.85)
    limit = max(4.0, float(w) - 2.0)
    for _ in range(8):
        if text_width_mm(text, size, bold) <= limit or size <= 1.5:
            break
        size *= 0.85
    half = size / 2.0
    cy = (floor + ceiling) / 2.0
    if cy + half > ceiling:
        cy = ceiling - half
    tw = text_width_mm(text, size, bold)
    rect = (float(w) / 2.0 - tw / 2.0, cy - half, tw, size)
    return {'size': size, 'x': float(w) / 2.0, 'y': cy, 'rect': rect}


def template_svg(template, info=None, sheet_no=1, n_sheets=1):
    """SVG of one title-block format, for the format editor. y grows up in the data and down in the SVG."""
    width, height = float(template['width']), float(template['height'])
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.3f %.3f">' % (width, height),
        '<rect width="100%%" height="100%%" fill="#f7f6f2"/>',
        '<rect x="10" y="10" width="%.3f" height="%.3f" fill="none" stroke="#222" stroke-width="0.6"/>'
        % (width - 20, height - 20),
    ]
    logo = template.get('logo')
    if logo:
        parts.append(_logo_svg(logo, height))
    for box in template.get('boxes') or []:
        x, y, w, h = float(box['x']), float(box['y']), float(box['w']), float(box['h'])
        top = height - (y + h)
        parts.append(
            '<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#fff" stroke="#222" '
            'stroke-width="0.35" data-box="%s"/>' % (x, top, w, h, _esc(box.get('id') or '')))
        parts.append(
            '<text x="%.3f" y="%.3f" font-size="%.2f" font-family="sans-serif" fill="#666">%s</text>'
            % (x + 1.0, top + LABEL_TOP_GAP + LABEL_H * 0.92, LABEL_H, _esc(box.get('label') or '')))
        value = field_text(box.get('field'), info, sheet_no, n_sheets, box.get('text') or '')
        bold = box.get('field') in ('project', 'title', 'rev', 'size')
        preferred = 4.6 if box.get('field') == 'title' and len(value) < 38 else 3.2
        if box.get('field') == 'title' and len(value) >= 38:
            preferred = 3.6
        place = None if box.get('field') in ('angle', 'tol') else value_place(w, h, value, preferred, bold)
        if place:
            parts.append(
                '<text x="%.3f" y="%.3f" font-size="%.2f" font-family="sans-serif" fill="#111" '
                'text-anchor="middle" dominant-baseline="central">%s</text>'
                % (x + place['x'], top + (h - place['y']), place['size'], _esc(value.split('\n')[0][:48])))
    parts.append('</svg>')
    return ''.join(parts)


def draw_template(sheet, template, info, sheet_no, n_sheets):
    """Draw the format onto a sheet canvas. Coordinates are millimetres, origin bottom left."""
    groups = {}
    for box in template.get('boxes') or []:
        groups.setdefault('tol' if box.get('field') == 'tol' else 'title', []).append(box)
    for group in groups.values():
        x0 = min(float(b['x']) for b in group)
        y0 = min(float(b['y']) for b in group)
        x1 = max(float(b['x']) + float(b['w']) for b in group)
        y1 = max(float(b['y']) + float(b['h']) for b in group)
        sheet.pl([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 'tb', closed=True)
    for box in template.get('boxes') or []:
        x, y, w, h = (float(box[k]) for k in ('x', 'y', 'w', 'h'))
        sheet.pl([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 'thin', closed=True)
        sheet.txt(x + 1, y + h - LABEL_TOP_GAP, box.get('label') or '', h=LABEL_H, ha='left', va='top')
        field = box.get('field')
        if field == 'angle':
            _angle_mark(sheet, x, y, w, h)
            continue
        if field == 'tol':
            from .canvas import TOL_H, tol_lines
            sheet.txt(x + 2, y + h - 4.5, 'UNLESS OTHERWISE SPECIFIED:', h=2.2, ha='left', va='top', bold=True)
            sheet.txt(x + 2, y + min(h - 8, 43.0 * h / 52.0), '\n'.join(tol_lines(info.get('tol'))),
                      h=TOL_H, ha='left', va='top')
            continue
        value = field_text(field, info, sheet_no, n_sheets, box.get('text') or '')
        bold = field in ('project', 'title', 'rev', 'size')
        preferred = 4.6 if field == 'title' and len(value) < 38 else 3.2
        if field == 'title' and len(value) >= 38:
            preferred = 3.6
        place = value_place(w, h, value, preferred, bold)
        if place:
            sheet.txt(x + place['x'], y + place['y'], value.split('\n')[0], h=place['size'], bold=bold)
    logo = template.get('logo')
    if logo:
        sheet.items.append(('im', float(logo['x']), float(logo['y']), float(logo['w']), float(logo['h']),
                             logo_href(logo), logo.get('kind') or 'png'))


def _angle_mark(sheet, x, y, w, h):
    """The projection symbol sits under the label, in the value area."""
    ceiling = h - LABEL_TOP_GAP - LABEL_H - 0.4
    cy = y + max(1.6, ceiling / 2.0)
    reach = max(1.0, ceiling / 2.0 - 0.2)
    sheet.pl([(x + 5, cy - reach * 0.7), (x + 9.5, cy - reach * 0.4),
              (x + 9.5, cy + reach * 0.4), (x + 5, cy + reach * 0.7)], 'thin', closed=True)
    sheet.line((x + 4, cy), (x + 10.5, cy), 'ctr')
    sheet.circle((x + 15, cy), min(2.2, reach), 'thin')
    sheet.circle((x + 15, cy), min(1.0, reach / 2.0), 'thin')
    sheet.txt(x + w - 1.5, cy, '3RD ANGLE', h=min(1.8, reach), ha='right')


def logo_href(logo):
    """A browser image href. Raw SVG text becomes a data URI."""
    href = logo.get('data') or ''
    if logo.get('kind') == 'svg' and str(href).lstrip().startswith('<svg'):
        href = 'data:image/svg+xml;utf8,' + str(href).replace('#', '%23')
    return href


def _logo_svg(logo, height):
    x, y, w, h = float(logo['x']), float(logo['y']), float(logo['w']), float(logo['h'])
    top = height - (y + h)
    return (
        '<image x="%.3f" y="%.3f" width="%.3f" height="%.3f" href="%s" data-logo="1"/>'
        % (x, top, w, h, _esc(logo_href(logo))))


def _edit(template, box_id, **fields):
    out = copy.deepcopy(template)
    for box in out['boxes']:
        if box.get('id') == box_id:
            box.update(fields)
            return out
    raise ValueError('no box %r' % box_id)


def _num(text):
    digits = ''.join(ch for ch in str(text or '') if ch.isdigit())
    return int(digits) if digits else 0


def _esc(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def template_dir(root):
    folder = os.path.join(root, 'formats')
    os.makedirs(folder, exist_ok=True)
    return folder
