"""A screw draws its outline. The hex socket inside the head is left out."""
import pytest

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from sheet2d.engines import get_engine
from vieweng.xq import _is_fastener


def _write(path, shape):
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    assert writer.Write(path) == 1


def _screw():
    axis = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    head = BRepPrimAPI_MakeCylinder(axis, 5.0, 8.0).Shape()
    socket = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 5), gp_Dir(0, 0, 1)), 2.0, 4.0).Shape()
    return BRepAlgoAPI_Cut(head, socket).Shape()


def test_a_screw_is_hardware_and_a_box_is_not():
    assert _is_fastener(_screw())
    assert not _is_fastener(BRepPrimAPI_MakeBox(80, 60, 8).Shape())


def test_the_socket_circle_is_left_out_of_the_top_view(tmp_path):
    step = tmp_path / 'screw.step'
    _write(str(step), _screw())
    views, _timing = get_engine('xq').project_views(('top',), step=str(step), mode='exact')
    circles = [line for line in views['top']['lines'] if line['kind'] == 'circle']
    assert circles
    assert all(line['r'] > 3.5 for line in circles)
    assert any(line['r'] > 4.0 for line in circles)
