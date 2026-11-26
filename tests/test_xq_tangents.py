"""Tangent edges are shown unless a view asks to hide them."""
import pytest

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

from sheet2d.engines import get_engine
from vieweng.xq import _show_tangents


def test_tangents_show_unless_a_view_hides_them():
    assert _show_tangents('top', True)
    assert _show_tangents('top', None)
    assert _show_tangents('front', False) is False
    assert _show_tangents('top', {'top': False}) is False
    assert _show_tangents('front', {'top': False}) is True


def test_hiding_tangents_drops_the_fillet_edges(tmp_path):
    box = BRepPrimAPI_MakeBox(30.0, 20.0, 16.0).Shape()
    fillet = BRepFilletAPI_MakeFillet(box)
    edge = TopoDS.Edge(TopExp_Explorer(box, TopAbs_EDGE).Current())
    fillet.Add(2.0, edge)
    shape = fillet.Shape()
    step = tmp_path / 'fillet.step'
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    assert writer.Write(str(step)) == 1
    engine = get_engine('xq')
    shown, _t = engine.project_views(('front',), step=str(step), mode='quick', tangents=True)
    hidden, _t = engine.project_views(('front',), step=str(step), mode='quick', tangents={'front': False})
    assert len(shown['front']['lines']) > len(hidden['front']['lines'])
