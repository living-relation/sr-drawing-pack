"""A plain cylinder must draw like the original exact-edge engine.

The original renderer lives in sr-drawing-pack and needs its own helpers, so
this check does not import it. It checks the lines that renderer draws for
this part: the top of a cylinder is a circle of the real radius, and nothing
bigger than the part appears.
"""
import math

import pytest

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from sheet2d.engines import get_engine
from sheet2d.engines.curves import arc_points


def _dist_point_seg(point, a, b):
    ax, ay = a
    bx, by = b
    px, py = point
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length < 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _covers(point, line, tol):
    kind = line['kind']
    if kind == 'circle':
        cx, cy = line['c']
        return abs(math.hypot(point[0] - cx, point[1] - cy) - line['r']) <= tol
    if kind == 'arc':
        pts = arc_points(line, 24)
    elif kind == 'ellipse':
        return False
    else:
        pts = line.get('pts') or []
    return any(_dist_point_seg(point, a, b) <= tol for a, b in zip(pts, pts[1:]))


def test_a_cylinder_top_is_covered_by_its_real_circle(tmp_path):
    radius = 5.0
    shape = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), radius, 12.0).Shape()
    step = tmp_path / 'cyl.step'
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    assert writer.Write(str(step)) == 1
    views, _timing = get_engine('xq').project_views(('top', 'front'), step=str(step), mode='exact')
    for name, view in views.items():
        for line in view['lines']:
            size = line.get('r') or max(line.get('rx') or 0, line.get('ry') or 0)
            assert size < 20, (name, line['kind'], size)
    samples = [
        (radius * math.cos(2 * math.pi * i / 16), radius * math.sin(2 * math.pi * i / 16))
        for i in range(16)
    ]
    missed = [point for point in samples if not any(_covers(point, line, 0.05) for line in views['top']['lines'])]
    assert not missed
