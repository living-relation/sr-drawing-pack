"""Assembly instances keep the position they have in the STEP file."""
import math

import pytest

pytest.importorskip('OCP')

from OCP.BRepBndLib import BRepBndLib
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.Bnd import Bnd_Box
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

from sheet2d.engines import get_engine  # noqa: F401  (loads xq without a circular import)
from vieweng.xq import _read_step, load_shape


def _shift(x, y, z):
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(x, y, z))
    return TopLoc_Location(trsf)


def _spin(axis, origin, degrees, then):
    """Rotation, then the translation in `then` (x, y, z)."""
    turn = gp_Trsf()
    turn.SetRotation(gp_Ax1(gp_Pnt(*origin), gp_Dir(*axis)), math.radians(degrees))
    move = gp_Trsf()
    move.SetTranslation(gp_Vec(*then))
    both = gp_Trsf()
    both.Multiply(move)
    both.Multiply(turn)
    return TopLoc_Location(both)


def _write_nested(path):
    """A machine holds two arms. Each arm holds two brackets, one of them turned."""
    box = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString('XmlXCAF'))
    app.NewDocument(TCollection_ExtendedString('MDTV-XCAF'), doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    machine = tool.NewShape()
    arm = tool.NewShape()
    bracket = tool.AddShape(box, False)
    TDataStd_Name.Set_s(machine, TCollection_ExtendedString('machine'))
    TDataStd_Name.Set_s(arm, TCollection_ExtendedString('arm'))
    TDataStd_Name.Set_s(bracket, TCollection_ExtendedString('bracket'))
    tool.AddComponent(arm, bracket, _shift(0, 0, 0))
    tool.AddComponent(arm, bracket, _spin((1, 0, 0), (0, 0, 0), 90, (40, 10, 0)))
    tool.AddComponent(machine, arm, _spin((0, 0, 1), (0, 0, 0), 30, (100, 0, 0)))
    tool.AddComponent(machine, arm, _shift(0, 200, 0))
    tool.UpdateAssemblies()
    writer = STEPCAFControl_Writer()
    writer.Transfer(doc, STEPControl_AsIs)
    assert writer.Write(path) == IFSelect_ReturnStatus.IFSelect_RetDone


def _solids(shape):
    found = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        found.append(explorer.Current())
        explorer.Next()
    return found


def _box(shape):
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box, True)
    lo, hi = box.CornerMin(), box.CornerMax()
    return (lo.X(), lo.Y(), lo.Z(), hi.X(), hi.Y(), hi.Z())


def _plain(path):
    reader = STEPControl_Reader()
    assert reader.ReadFile(path) == IFSelect_ReturnStatus.IFSelect_RetDone
    assert reader.TransferRoots() == 1
    return reader.OneShape()


def test_nested_instances_sit_where_the_plain_reader_puts_them(tmp_path):
    step = tmp_path / 'nested.step'
    _write_nested(str(step))
    placed, names = _read_step(str(step))
    plain = _plain(str(step))
    ours = sorted(_box(solid) for solid in _solids(placed))
    truth = sorted(_box(solid) for solid in _solids(plain))
    assert len(ours) == len(truth) == 4
    assert names == ['bracket', 'bracket', 'bracket', 'bracket']
    for got, want in zip(ours, truth):
        for a, b in zip(got, want):
            assert abs(a - b) < 0.01
    assert all(abs(a - b) < 0.01 for a, b in zip(_box(placed), _box(plain)))
    centers = [((b[0] + b[3]) / 2, (b[1] + b[4]) / 2) for b in ours]
    assert max(c[0] for c in centers) - min(c[0] for c in centers) > 100
    assert max(c[1] for c in centers) - min(c[1] for c in centers) > 100


def test_a_cached_assembly_keeps_those_positions(tmp_path):
    step = tmp_path / 'nested-cache.step'
    _write_nested(str(step))
    first, _secs, from_step, names = load_shape(str(step))
    second, _secs2, from_cache, names2 = load_shape(str(step))
    assert from_step and not from_cache
    assert names == names2 == ['bracket', 'bracket', 'bracket', 'bracket']
    assert all(abs(a - b) < 0.01 for a, b in zip(_box(first), _box(second)))
    assert _box(first)[3] > 100
