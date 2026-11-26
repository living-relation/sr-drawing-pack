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
