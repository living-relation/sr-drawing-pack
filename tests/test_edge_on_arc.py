"""An arc seen edge-on draws only as long as its own span, not the whole diameter."""
import math

from sheet2d.engines.curves import analytic_curve

RIGHT = (1.0, 0.0, 0.0)
UP = (0.0, 1.0, 0.0)


def _len(item):
    (x0, y0), (x1, y1) = item['pts']
    return math.hypot(x1 - x0, y1 - y0)


def test_short_piece_of_big_arc_stays_short():
    # Circle in the X-Z plane, radius 300, seen from +Z: edge-on, a line along X.
    item = analytic_curve((0, 0, 0), (1, 0, 0), (0, 0, 1), 300.0, 1.5, 1.55, RIGHT, UP, 'vis', partial=True)
    assert item['kind'] == 'poly'
    chord = 300.0 * abs(math.cos(1.5) - math.cos(1.55))
    assert abs(_len(item) - chord) < 0.5
    assert _len(item) < 20


def test_full_edge_on_circle_spans_diameter():
    item = analytic_curve((0, 0, 0), (1, 0, 0), (0, 0, 1), 10.0, 0.0, 2 * math.pi, RIGHT, UP, 'vis')
    assert abs(_len(item) - 20.0) < 1e-6


def test_half_arc_edge_on_spans_its_half():
    # u from 0 to pi on cos: x goes 10 -> -10, full width.
    item = analytic_curve((0, 0, 0), (1, 0, 0), (0, 0, 1), 10.0, 0.0, math.pi, RIGHT, UP, 'vis', partial=True)
    assert abs(_len(item) - 20.0) < 0.1
    # u from 0 to pi/2: x goes 10 -> 0.
    item = analytic_curve((0, 0, 0), (1, 0, 0), (0, 0, 1), 10.0, 0.0, math.pi / 2, RIGHT, UP, 'vis', partial=True)
    assert abs(_len(item) - 10.0) < 0.1


def test_folded_short_curve_is_not_a_full_circle():
    from sheet2d.engines.curves import fit_circle
    # A thin closed loop along the top 20 degrees of a radius-37 circle, out and back.
    r = 37.0
    out = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in range(80, 101)]
    back = [(x * 0.999, y * 0.999) for x, y in reversed(out)]
    loop = out + back + [out[0]]
    assert fit_circle(loop, 0.05) is None


def test_real_ring_is_still_a_circle():
    from sheet2d.engines.curves import fit_circle
    ring = [(5 * math.cos(2 * math.pi * k / 24), 5 * math.sin(2 * math.pi * k / 24)) for k in range(25)]
    got = fit_circle(ring, 0.05)
    assert got and abs(got['r'] - 5) < 0.01
