"""A copy that is turned 180 degrees is drawn where its hole really is, not as a moved copy."""
import pytest

pytest.importorskip('OCP')
pytest.importorskip('vtk')

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

from sheet2d.engines import get_engine


def _plate():
    # 40 x 20 x 4 plate, one hole near the +X end.
    plate = BRepPrimAPI_MakeBox(40, 20, 4).Shape()
    hole = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(32, 10, -1), gp_Dir(0, 0, 1)), 3.0, 6.0).Shape()
    return BRepAlgoAPI_Cut(plate, hole).Shape()


def _write(path, placements):
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString('XmlXCAF'))
    app.NewDocument(TCollection_ExtendedString('MDTV-XCAF'), doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    top = tool.NewShape()
    TDataStd_Name.Set_s(top, TCollection_ExtendedString('ASY'))
    proto = tool.AddShape(_plate(), False)
    TDataStd_Name.Set_s(proto, TCollection_ExtendedString('Bracket plate'))
    for trsf in placements:
        tool.AddComponent(top, proto, TopLoc_Location(trsf))
    tool.UpdateAssemblies()
    writer = STEPCAFControl_Writer()
    writer.Transfer(doc, STEPControl_AsIs)
    assert writer.Write(path) == IFSelect_ReturnStatus.IFSelect_RetDone


def test_turned_copy_hole_is_where_it_really_is(tmp_path):
    first = gp_Trsf()
    turned = gp_Trsf()
    # Turn 180 degrees about Z through the plate center, then move 60 mm along Y.
    turned.SetRotation(gp_Ax1(gp_Pnt(20, 10, 0), gp_Dir(0, 0, 1)), 3.141592653589793)
    move = gp_Trsf()
    move.SetTranslation(gp_Vec(0, 60, 0))
    turned = move.Multiplied(turned)
    step = tmp_path / 'turned.step'
    _write(str(step), [first, turned])
    views, _timing = get_engine('xq').project_views(('top',), step=str(step), mode='exact')
    holes = [line for line in views['top']['lines'] if line['kind'] in ('circle', 'arc') and abs(line['r'] - 3.0) < 0.2]
    centers = sorted((round(line['c'][0]), round(line['c'][1])) for line in holes)
    # First plate: hole at x=32. Turned plate: hole at x=8 (40 - 32), y = 70.
    xs = {c[0] for c in centers}
    assert 32 in xs and 8 in xs, centers
