"""Round edges come from the real circle, not a fit through straight pieces."""
import math

import pytest

from sheet2d.engines.curves import analytic_curve

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from sheet2d.engines import get_engine


def test_a_facing_circle_stays_a_circle_and_a_tilted_one_is_an_ellipse():
    origin = (0.0, 0.0, 0.0)
    xdir = (1.0, 0.0, 0.0)
    ydir = (0.0, 1.0, 0.0)
    facing = analytic_curve(origin, xdir, ydir, 5.0, 0.0, 2.0 * math.pi, (1, 0, 0), (0, 1, 0), 'vis')
    assert facing['kind'] == 'circle'
    assert abs(facing['r'] - 5.0) < 1e-9
    tilted = analytic_curve(
        origin, xdir, ydir, 5.0, 0.0, 2.0 * math.pi, (1, 0, 0), (0, 0.6, 0.8), 'vis')
    assert tilted['kind'] == 'ellipse'
    assert tilted['rx'] > tilted['ry'] > 0
    # Principal axes already at 30 degrees must not come out as 0.
    deg = math.radians(30)
    xdir = (4.0 * math.cos(deg), 4.0 * math.sin(deg), 0.0)
    ydir = (-1.5 * math.sin(deg), 1.5 * math.cos(deg), 0.0)
    turned = analytic_curve(origin, xdir, ydir, 1.0, 0.0, 2.0 * math.pi, (1, 0, 0), (0, 1, 0), 'vis')
    assert turned['kind'] == 'ellipse'
    assert abs((turned['rot'] - deg + math.pi / 2) % math.pi - math.pi / 2) < 1e-6
    partial = analytic_curve(origin, xdir, ydir, 1.0, 0.0, math.pi / 2, (1, 0, 0), (0, 1, 0), 'vis')
    # A tilted partial edge is not a circular arc.
    assert partial['kind'] == 'poly'
    quarter = analytic_curve(
        origin, (1, 0, 0), (0, 1, 0), 5.0, 0.0, math.pi / 2, (1, 0, 0), (0, 1, 0), 'vis')
    assert quarter['kind'] == 'arc'
    assert quarter['r'] == pytest.approx(5.0)
    assert abs(abs(quarter['a1'] - quarter['a0']) - math.pi / 2) < 1e-6


def test_a_cylinder_top_uses_the_real_radius(tmp_path):
    axis = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    shape = BRepPrimAPI_MakeCylinder(axis, 5.0, 12.0).Shape()
    step = tmp_path / 'cyl.step'
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    assert writer.Write(str(step)) == 1
    views, _timing = get_engine('xq').project_views(('top', 'trimetric'), step=str(step), mode='exact')
    top = [line for line in views['top']['lines'] if line.get('analytic') and line['kind'] == 'circle']
    assert top
    assert abs(top[0]['r'] - 5.0) < 1e-6
    assert any(line.get('analytic') and line['kind'] == 'ellipse' for line in views['trimetric']['lines'])


def test_a_cut_circle_is_an_arc_not_a_polyline(tmp_path):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    cyl = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 5.0, 12.0).Shape()
    box = BRepPrimAPI_MakeBox(gp_Pnt(-10, -10, -1), gp_Pnt(0, 10, 20)).Shape()
    shape = BRepAlgoAPI_Cut(cyl, box).Shape()
    step = tmp_path / 'half.step'
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    assert writer.Write(str(step)) == 1
    views, _timing = get_engine('xq').project_views(('top',), step=str(step), mode='exact')
    arcs = [line for line in views['top']['lines'] if line.get('analytic') and line['kind'] == 'arc']
    assert arcs
    assert abs(arcs[0]['r'] - 5.0) < 1e-4
    assert all(not (line['kind'] == 'circle' and abs(line['r'] - 5.0) < 0.1) for line in views['top']['lines'])
