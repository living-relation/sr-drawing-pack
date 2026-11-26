"""A loose face must not stretch the view, and a deep picture is drawn in tiles."""
import pytest

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Pnt

from sheet2d.engines import get_engine
from vieweng.xq import TILE


def _write(path, shape):
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    assert writer.Write(path) == 1


def test_loose_face_does_not_stretch_the_depth_picture(tmp_path):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    builder.Add(compound, BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 20, 10, 8).Shape())
    wire = BRepBuilderAPI_MakePolygon(
        gp_Pnt(2500, 0, 0), gp_Pnt(2600, 0, 0), gp_Pnt(2600, 80, 0), gp_Pnt(2500, 80, 0), True).Wire()
    builder.Add(compound, BRepBuilderAPI_MakeFace(wire).Face())
    step = tmp_path / 'loose.step'
    _write(str(step), compound)
    _views, timing = get_engine('xq').project_views(('front',), step=str(step), mode='quick')
    assert timing['res'] < 3000


def test_a_wide_depth_picture_is_tiled(tmp_path):
    from vieweng import xq
    shape = BRepPrimAPI_MakeBox(20, 20, 10).Shape()
    verts, faces, _normals = xq._mesh_arrays(shape, 0.5)
    depth = xq._Depth(verts, faces)
    image, _to_win, _dz, _px = depth.render((0, 0, 1), (1, 0, 0), (0, 1, 0), 20, 20, TILE * 2)
    assert max(image.shape) > TILE
    assert image.min() < 1.0
    step = tmp_path / 'box.step'
    _write(str(step), shape)
    views, timing = get_engine('xq').project_views(('front',), step=str(step), mode='exact')
    assert views['front']['lines']
    assert timing['res'] <= 8192
