"""Copies of one part are meshed once and placed, not meshed again."""
import pytest

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRep import BRep_Builder
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from sheet2d.engines import get_engine


def test_three_copies_share_one_mesh(tmp_path):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for x in (0.0, 30.0, 60.0):
        axis = gp_Ax2(gp_Pnt(x, 0, 0), gp_Dir(0, 0, 1))
        builder.Add(compound, BRepPrimAPI_MakeCylinder(axis, 4.0, 10.0).Shape())
    step = tmp_path / 'copies.step'
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    assert writer.Write(str(step)) == 1
    views, timing = get_engine('xq').project_views(('top',), step=str(step), mode='quick')
    assert timing['unique_solids'] == 1
    circles = [line for line in views['top']['lines'] if line['kind'] == 'circle' and line['r'] > 3]
    centers = sorted(line['c'][0] for line in circles)
    assert len(centers) >= 3
    assert centers[-1] - centers[0] > 40
