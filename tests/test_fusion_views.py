"""Real views from Fusion meshes: edge finding, the dump format, one-scale layout, and the sheet."""
import json
import math
import os
import struct

import pytest

from sheet2d.meshparts import load_fusion_dump, mesh_features, place
from sheet2d.scene import build_scene
from sheet2d.viewsheet import STD_SCALES, build_view_sheet, clear_view_geometry, layout

IDENT = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def _fusion_box(sx, sy, sz):
    """A box meshed the way Fusion does it: each face has its own four nodes, wound outward."""
    c = [(x, y, z) for x in (0.0, sx) for y in (0.0, sy) for z in (0.0, sz)]
    faces = ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5))
    mid = (sx / 2.0, sy / 2.0, sz / 2.0)
    pts, tris = [], []
    for quad in faces:
        q = [c[i] for i in quad]
        e1 = [q[1][k] - q[0][k] for k in range(3)]
        e2 = [q[2][k] - q[0][k] for k in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        centre = [sum(p[k] for p in q) / 4.0 for k in range(3)]
        if sum(n[k] * (centre[k] - mid[k]) for k in range(3)) < 0:
            q.reverse()
        k0 = len(pts)
        pts += q
        tris += [(k0, k0 + 1, k0 + 2), (k0, k0 + 2, k0 + 3)]
    return pts, tris


def _fusion_cylinder(r, h, n=24):
    """Side face with shared nodes (one face), caps with their own nodes."""
    ring = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts = [(x, y, 0.0) for x, y in ring] + [(x, y, h) for x, y in ring]
    tris = []
    for i in range(n):
        j = (i + 1) % n
        tris += [(i, j, n + j), (i, n + j, n + i)]
    for z, flip in ((0.0, True), (h, False)):
        base = len(pts)
        pts += [(x, y, z) for x, y in ring]
        for i in range(1, n - 1):
            tris.append((base, base + i + 1, base + i) if flip else (base, base + i, base + i + 1))
    return pts, tris


def test_box_draws_only_its_twelve_edges():
    edges, smooth = mesh_features(*_fusion_box(10, 20, 30))
    assert len(edges) == 12
    assert all(style == 'vis' for _poly, style in edges)
    assert smooth == []  # face diagonals are never drawn


def test_cylinder_keeps_rims_and_silhouette_edges():
    edges, smooth = mesh_features(*_fusion_cylinder(5.0, 10.0))
    assert len(edges) == 48 and all(style == 'vis' for _p, style in edges)  # two rims
    assert len(smooth) == 24  # side seams, for silhouettes
    # cap triangles are flat: none of their inner edges is drawn or kept
    assert all(abs(a[2] - b[2]) > 1.0 for a, b, _n1, _n2 in smooth)


def _write_dump(folder, bodies, placements, units='cm'):
    with open(os.path.join(folder, 'occurrences.json'), 'w', encoding='utf-8') as handle:
        json.dump({'document': 'Test Assy', 'units': units,
                   'bodies': [{'key': k, 'comp': 'c', 'body': 0, 'name': k} for k in bodies],
                   'placements': placements}, handle)
    with open(os.path.join(folder, 'mesh_00000.bin'), 'wb') as handle:
        for key, (pts, tris) in bodies.items():
            k = key.encode('utf-8')
            flat = [v for p in pts for v in p]
            idx = [i for t in tris for i in t]
            handle.write(struct.pack('<I', len(k)) + k + struct.pack('<II', len(flat), len(idx)))
            handle.write(struct.pack('<%df' % len(flat), *flat))
            handle.write(struct.pack('<%di' % len(idx), *idx))


def test_dump_reuses_one_mesh_for_each_placement(tmp_path):
    moved = list(IDENT)
    moved[3] = 5.0  # 5 cm along x
    _write_dump(str(tmp_path), {'box#0': _fusion_box(1, 2, 3)}, [
        {'key': 'box#0', 'occ': 'a:1', 'xf': IDENT},
        {'key': 'box#0', 'occ': 'a:2', 'xf': moved},
        {'key': 'gone#0', 'occ': 'b:1', 'xf': IDENT},
    ])
    parts, info = load_fusion_dump(str(tmp_path))
    assert info['document'] == 'Test Assy'
    assert info['unique_bodies'] == 1 and info['placements'] == 3 and info['missing'] == 1
    assert len(parts) == 2
    xs0 = [p[0] for p in parts[0][1]]
    xs1 = [p[0] for p in parts[1][1]]
    assert max(xs0) == pytest.approx(10.0)  # cm to mm
    assert min(xs1) == pytest.approx(50.0) and max(xs1) == pytest.approx(60.0)


def test_place_rotates_normals_without_scaling_them():
    rot = [0.0, -1.0, 0, 0, 1.0, 0.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]  # 90 deg about z
    pts, tris = _fusion_cylinder(1.0, 1.0, n=8)
    edges, smooth = mesh_features(pts, tris)
    part = place((pts, tris, edges, smooth), rot, 10.0)
    for _a, _b, n1, _n2 in part[4]:
        assert math.sqrt(sum(v * v for v in n1)) == pytest.approx(1.0)


def test_layout_one_scale_and_third_angle_alignment():
    ext = {'front': (0, 400, 0, 200), 'top': (0, 400, 0, 150), 'right': (0, 150, 0, 200),
           'trimetric': (0, 300, 0, 250)}
    plan = layout(ext, (253.8, 240.0, 421.8, 263.8))
    f, t, r = plan['frames']['front'], plan['frames']['top'], plan['frames']['right']
    assert plan['label'] in [label for _s, label in STD_SCALES]
    assert t[0] == f[0] and t[2] == f[2]  # top above front, same width
    assert t[1] > f[1] + f[3]
    assert r[1] == f[1] and r[3] == f[3]  # right beside front, same height
    assert r[0] > f[0] + f[2]
    # the next bigger standard scale would not fit
    bigger = [s for s, _l in STD_SCALES if s > plan['scale']]
    if bigger:
        s = min(bigger)
        assert 400 * s + 16 + 150 * s > 399.8 - 16 or 200 * s + 16 + 150 * s > 263.4 - 67
    tri = plan['trimetric']
    assert tri['frame'][0] >= r[0] - 1e-9
    assert tri['frame'][1] > f[1]  # never beside the front view


def test_layout_refuses_when_nothing_fits():
    big = (0, 1e6, 0, 1e6)
    with pytest.raises(ValueError):
        layout({'front': big, 'top': big, 'right': big, 'trimetric': big}, (253.8, 240.0, 421.8, 263.8))


def test_sheet_with_real_views_draws_lines_in_the_editor(tmp_path):
    pts, tris = _fusion_box(120, 60, 40)
    edges, smooth = mesh_features(pts, tris)
    parts = [place((pts, tris, edges, smooth), IDENT)]
    doc, report = build_view_sheet(parts, 'Box Test', key='t-box', source='Fusion')
    views = [el for s in doc['sheets'] for el in s['elements'] if el.get('type') == 'view']
    assert sorted(v['label'] for v in views) == ['FRONT', 'RIGHT', 'TOP', 'TRIMETRIC']
    assert all(v.get('geom') for v in views)
    assert report['scale'] and len(report['views']) == 4
    with_lines = build_scene(doc)['svg'].count(' L ')
    clear_view_geometry('t-box')
    frames_only = build_scene(doc)['svg'].count(' L ')
    assert with_lines > frames_only  # the box outlines are drawn, not empty frames
    from sheet2d.model import DrawingDocument
    from sheet2d.render import export_pdf
    out = tmp_path / 'box.pdf'
    export_pdf(DrawingDocument.from_dict(doc), str(out))
    assert out.stat().st_size > 1000


# --- per-view scales -------------------------------------------------------

from sheet2d.commands import execute  # noqa: E402
from sheet2d.meshparts import component_name, is_hardware  # noqa: E402
from sheet2d.project import project_view  # noqa: E402
from sheet2d.viewsheet import arrange, scale_label, thin_small_features  # noqa: E402


def _box_parts(sx=120, sy=60, sz=40, meta=None):
    pts, tris = _fusion_box(sx, sy, sz)
    edges, smooth = mesh_features(pts, tris)
    return [place((pts, tris, edges, smooth), IDENT, 1.0, meta)]


def _views(doc):
    return {el['id']: el for s in doc['sheets'] for el in s['elements'] if el.get('type') == 'view'}


def test_scale_label_names_standard_and_custom_ratios():
    assert scale_label(1.0 / 30.0) == '1:30'
    assert scale_label(2.0) == '2:1'
    assert scale_label(1.0 / 16.0) == '1:16'


def test_arrange_lists_what_does_not_fit():
    ext = {'front': (0, 400, 0, 200), 'top': (0, 400, 0, 150), 'right': (0, 150, 0, 200)}
    plan = arrange(ext, {'front': 2.0, 'top': 2.0, 'right': 2.0}, 2.0, (253.8, 240.0, 421.8, 263.8))
    assert plan['problems']
    ok = arrange(ext, {'front': 0.25, 'top': 0.25, 'right': 0.25}, 0.25, (253.8, 240.0, 421.8, 263.8))
    assert ok['problems'] == []


def test_set_view_scale_lays_out_again_and_prints_caption():
    doc, report = build_view_sheet(_box_parts(), 'Box', key='t-scale')
    before = _views(doc)['v_right']
    out = execute(doc, 'set_view_scale', {'id': 'v_right', 'scale': '1:2' if report['scale'] != '1:2' else '1:4'})
    doc = out['document']
    after = _views(doc)['v_right']
    assert after['scale'] in ('1:2', '1:4')
    assert out['result']['caption'] == ['SCALE %s' % after['scale']]
    assert abs(after['w'] - before['w']) > 1.0  # the frame follows the new scale
    # back to the sheet scale: no own scale, no caption
    out = execute(doc, 'set_view_scale', {'id': 'v_right', 'scale': 'sheet'})
    assert _views(out['document'])['v_right'].get('scale') is None
    assert out['result']['caption'] == []
    with pytest.raises(ValueError):
        execute(doc, 'set_view_scale', {'id': 'v_right', 'scale': 'big'})


def test_set_sheet_scale_moves_views_that_follow_it():
    doc, report = build_view_sheet(_box_parts(), 'Box', key='t-sheet')
    doc = execute(doc, 'set_view_scale', {'id': 'v_top', 'scale': '1:5'})['document']
    out = execute(doc, 'set_sheet_scale', {'scale': '1:5'})
    doc = out['document']
    assert doc['properties']['scale'] == '1:5'
    views = _views(doc)
    assert views['v_top'].get('scale') is None  # same as the sheet now
    assert views['v_front']['w'] == pytest.approx(120 * 0.2, rel=0.05)


def test_view_options_round_trip_and_custom_scale():
    doc, _report = build_view_sheet(_box_parts(), 'Box', key='t-opt',
                                    sheet_scale='1:4', view_scales={'trimetric': '1:16'})
    assert doc['properties']['scale'] == '1:4'
    assert _views(doc)['v_trimetric']['scale'] == '1:16'
    out = execute(doc, 'set_view_options', {'min_line_mm': 0.5, 'small_feature_mm': 0})
    assert out['result'] == {'min_line_mm': 0.5, 'small_feature_mm': 0.0}
    from sheet2d.model import DrawingDocument
    again = DrawingDocument.from_dict(out['document']).to_dict()
    assert again['properties']['min_line_mm'] == 0.5
    scene = build_scene(out['document'])
    assert scene['views']['sheet_scale'] == '1:4'
    assert '1:30' in scene['views']['options']
    row = next(v for v in scene['views']['views'] if v['id'] == 'v_trimetric')
    assert row['scale'] == '1:16' and row['generated']


# --- small lines and hardware outlines -------------------------------------

def _ring(cx, cy, r, n=24):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    return {'kind': 'poly', 'pts': pts, 'style': 'vis'}


def test_small_feature_keeps_only_its_outline():
    head = [_ring(0, 0, 2.85), _ring(0, 0, 2.6), _ring(0, 0, 1.0),
            {'kind': 'poly', 'pts': [(-1.0, 0.0), (0.5, 0.8)], 'style': 'vis'}]
    plate = {'kind': 'poly', 'pts': [(-50, -50), (50, -50)], 'style': 'vis'}
    kept, dropped = thin_small_features(head + [plate], 1.0 / 3.0)
    assert dropped == 3
    assert head[0] in kept and plate in kept
    # at 2:1 the head is 11 mm on paper: nothing is thinned
    kept, dropped = thin_small_features(head + [plate], 2.0)
    assert dropped == 0
    # min line: a 0.6 mm stub is gone at 1:3 (0.2 mm on paper)
    stub = {'kind': 'poly', 'pts': [(80, 0), (80.6, 0)], 'style': 'vis'}
    kept, dropped = thin_small_features([stub, plate], 1.0 / 3.0, small_mm=0)
    assert stub not in kept and dropped == 1


def _stepped(meta=None):
    """A 20 x 20 x 4 block with a 10 x 10 x 2 boss on top, meshed face by face."""
    pts, tris = _fusion_box(20, 20, 4)
    bp, bt = _fusion_box(10, 10, 2)
    n = len(pts)
    pts = pts + [(x + 5, y + 5, z + 4) for x, y, z in bp]
    tris = tris + [(a + n, b + n, c + n) for a, b, c in bt]
    edges, smooth = mesh_features(pts, tris)
    return place((pts, tris, edges, smooth), IDENT, 1.0, meta)


def _lengths(view):
    return sum(math.dist(a, b) for line in view['lines'] for a, b in zip(line['pts'], line['pts'][1:]))


def test_hardware_draws_only_its_outline():
    def inner(view):  # lines inside the outer square: the boss edges
        return [line for line in view['lines'] if all(2 < p[0] < 18 and 2 < p[1] < 18 for p in line['pts'])]
    plain = project_view([_stepped({'key': 'b', 'outline': False})], 'top', buf_w=400, buf_h=400)
    outline = project_view([_stepped({'key': 'b', 'outline': True})], 'top', buf_w=400, buf_h=400)
    assert sum(math.dist(a, b) for line in inner(plain) for a, b in zip(line['pts'], line['pts'][1:])) >= 39
    assert inner(outline) == []
    assert _lengths(outline) >= 79  # the outer square stays


def test_another_part_in_front_hides_edges_on_a_coarse_view():
    # A 3 mm plate lies on a smaller block; the block's top edges are under the plate.
    plate = _box_parts(400, 400, 3)[0]
    plate = ('mesh', [(x, y, z + 10) for x, y, z in plate[1]], plate[2],
             [([(x, y, z + 10) for x, y, z in poly], st) for poly, st in plate[3]], plate[4])
    block = _box_parts(100, 100, 10)[0]
    block = ('mesh', [(x + 150, y + 150, z) for x, y, z in block[1]], block[2],
             [([(x + 150, y + 150, z) for x, y, z in poly], st) for poly, st in block[3]], block[4])
    view = project_view([plate, block], 'top', buf_w=240, buf_h=240)
    inner = [line for line in view['lines'] if all(140 < p[0] < 260 and 140 < p[1] < 260 for p in line['pts'])]
    assert inner == []


def test_hardware_names():
    for name in ('SBH-M3-0.5 x 8', 'NHX-M3-0.5 18-8 SS', 'WSL-M2 x 4.4 18-8 SS',
                 'SO-M3-6ZI, Self-Clinching Thru-Thread Standoff M3x0.5 x 6mm, Steel Zinc, PEM',
                 'ISO 7045 M3x35 A2, Pan Head Phillips', 'M3X6mm v1', 'Standoff, Hex, M3 x 6mm F-F'):
        assert is_hardware(name), name
    for name in ('1827842, MC 1,5-16-STF-3,81, Screw Plug, Phoenix Contact', 'Lid', 'Main Shell',
                 'LP-16-J/TYPEC31/215/SX-42-401, Conn, Jam Nut, LP16, USB Type-C', 'COMPOUND (5)'):
        assert not is_hardware(name), name
    assert component_name('Assy:1+SBH-M3-0.5 x 8:4') == 'SBH-M3-0.5 x 8'


def test_editor_demo_changes_a_view_scale_and_sharpens_it():
    sys_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dev')
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from sheet_demo import Demo
    parts = _box_parts()
    doc, _report = build_view_sheet(parts, 'Box', key='t-demo')
    demo = Demo(lambda: json.loads(json.dumps(doc)), parts)
    scene = demo.command('set_view_scale', {'id': 'v_trimetric', 'scale': '1:1'})
    row = next(v for v in scene['views']['views'] if v['id'] == 'v_trimetric')
    assert row['shown'] == '1:1'
    assert 'SCALE 1:1' in scene['svg'] or row['scale'] is None
    scene = demo.command('set_sheet_scale', {'scale': '1:4'})
    assert scene['views']['sheet_scale'] == '1:4'
    scene = demo.command('reset')
    assert scene['views']['sheet_scale'] == doc['properties']['scale']
