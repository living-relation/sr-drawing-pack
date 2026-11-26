"""View engines: XQ and Fusion. The old mesh line engine is not a choice."""
import math

import pytest

from sheet2d.engines import engine_for_preset, engine_names, get_engine, normalize_lines
from sheet2d.engines.curves import bridge_gaps, fit_chain, fit_circle, fit_ellipse
from sheet2d.commands import execute


def test_engines_are_xq_and_fusion_only():
    assert engine_names() == ('xq', 'fusion')
    with pytest.raises(ValueError):
        get_engine('mesh')
    draft, mode, note = engine_for_preset('draft')
    assert draft.name == 'xq' and mode == 'quick'
    hq, hq_mode, _note = engine_for_preset('hq')
    assert hq.name == 'xq' and hq_mode == 'exact'
    if draft.available()[0]:
        assert note == ''
    else:
        assert 'XQ' in note
    assert 'Fusion' in get_engine('fusion').available()[1]
    with pytest.raises(RuntimeError, match='inside Fusion'):
        get_engine('fusion').project_view('front')


def test_hidden_lines_are_dropped_and_tangent_edges_stay_thin():
    lines = normalize_lines([
        {'kind': 'poly', 'pts': [(0, 0), (1, 0)], 'style': 'hid'},
        {'kind': 'poly', 'pts': [(0, 1), (1, 1)], 'style': 'tan'},
        {'kind': 'poly', 'pts': [(0, 2), (1, 2)], 'style': 'vis'},
    ])
    assert [line['style'] for line in lines] == ['thin', 'vis']


def test_small_gaps_join_and_round_edges_fit():
    joined = bridge_gaps([[(0, 0), (1, 0)], [(1.05, 0), (2, 0)]], 0.1)
    assert len(joined) == 1 and joined[0][-1] == (2, 0)
    ring = [(2.85 * math.cos(2 * math.pi * i / 16), 2.85 * math.sin(2 * math.pi * i / 16)) for i in range(16)]
    ring.append(ring[0])
    circle = fit_circle(ring, 0.05)
    assert circle and circle['r'] == pytest.approx(2.85, abs=0.05)
    hexagon = [(5 * math.cos(2 * math.pi * i / 6), 5 * math.sin(2 * math.pi * i / 6)) for i in range(6)]
    hexagon.append(hexagon[0])
    assert fit_circle(hexagon, 0.05) is None
    assert fit_chain(ring, 'vis', curves=False)['kind'] == 'poly'
    phi = 0.4
    pts = []
    for i in range(24):
        t = 2 * math.pi * i / 24
        x, y = 6 * math.cos(t), 2.4 * math.sin(t)
        pts.append((math.cos(phi) * x - math.sin(phi) * y, math.sin(phi) * x + math.cos(phi) * y))
    pts.append(pts[0])
    ellipse = fit_ellipse(pts, 0.05)
    assert ellipse and ellipse['rx'] == pytest.approx(6, rel=0.08)
    assert ellipse['ry'] == pytest.approx(2.4, rel=0.12)
    assert abs((ellipse['rot'] - phi + math.pi / 2) % math.pi - math.pi / 2) < 0.15


def test_an_open_curve_is_an_arc_or_a_polyline_never_a_full_circle():
    gentle = []
    radius = 3000.0
    half = 20.0 / radius
    for i in range(16):
        t = -half + 2 * half * i / 15
        gentle.append((radius * math.sin(t), radius * (1.0 - math.cos(t))))
    assert fit_circle(gentle, 0.05) is None
    assert fit_chain(gentle, 'vis')['kind'] == 'poly'
    arc_pts = []
    for i in range(10):
        t = 0.2 + 1.0 * i / 9
        arc_pts.append((12.0 * math.cos(t), 12.0 * math.sin(t)))
    arc = fit_chain(arc_pts, 'vis')
    assert arc['kind'] == 'arc'
    assert arc['r'] == pytest.approx(12.0, abs=0.05)
    assert 0.5 < abs(arc['a1'] - arc['a0']) < 1.5


def test_a_circle_bigger_than_the_view_stays_a_polyline():
    big = [(3000 * math.cos(2 * math.pi * i / 32), 3000 * math.sin(2 * math.pi * i / 32)) for i in range(32)]
    big.append(big[0])
    assert fit_chain(big, 'vis', max_r=200)['kind'] == 'poly'
    small = [(5 * math.cos(2 * math.pi * i / 16), 5 * math.sin(2 * math.pi * i / 16)) for i in range(16)]
    small.append(small[0])
    assert fit_chain(small, 'vis', max_r=200)['kind'] == 'circle'
    assert fit_chain(arc_pts_of(12), 'vis', max_r=5)['kind'] == 'poly'


def arc_pts_of(radius):
    return [(radius * math.cos(0.2 + i / 9), radius * math.sin(0.2 + i / 9)) for i in range(10)]


def test_preset_is_stored_and_shown():
    doc = execute(None, 'add_sheet', {'id': 's1'})['document']
    out = execute(doc, 'set_view_preset', {'preset': 'hq'})
    assert out['document']['properties']['view_preset'] == 'hq'
    assert out['result']['preset'] == 'hq'
    assert out['result']['engine'] == 'xq' and out['result']['mode'] == 'exact'
    from sheet2d.scene import build_scene
    scene = build_scene(out['document'])
    assert scene['views']['preset'] == 'hq'
    assert scene['views']['presets'] == ['draft', 'hq']
    with pytest.raises(ValueError):
        execute(doc, 'set_view_preset', {'preset': 'ultra'})
