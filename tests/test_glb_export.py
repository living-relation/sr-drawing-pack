"""STEP to GLB keeps the part names the 3D viewer lists (ADR-066)."""
import json
import struct

import pytest

pytest.importorskip('OCP')

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from vieweng.glb import step_to_glb


def _write_named(path, parts):
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString('XmlXCAF'))
    app.NewDocument(TCollection_ExtendedString('MDTV-XCAF'), doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    for shape, name in parts:
        label = tool.AddShape(shape, False)
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(name))
    writer = STEPCAFControl_Writer()
    writer.Transfer(doc, STEPControl_AsIs)
    assert writer.Write(path) == IFSelect_ReturnStatus.IFSelect_RetDone


def _gltf_json(path):
    data = open(path, 'rb').read()
    magic, _version, _length = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF'
    chunk_len, chunk_type = struct.unpack('<I4s', data[12:20])
    assert chunk_type == b'JSON'
    return json.loads(data[20:20 + chunk_len])


def test_glb_keeps_part_names(tmp_path):
    step = tmp_path / 'asm.step'
    plate = BRepPrimAPI_MakeBox(80, 60, 6).Shape()
    screw = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(10, 10, 6), gp_Dir(0, 0, 1)), 1.5, 8).Shape()
    _write_named(str(step), [(plate, 'Base plate'), (screw, 'SBH-M3-0.5 x 8')])
    glb = tmp_path / 'asm.glb'
    report = step_to_glb(str(step), str(glb))
    assert report['bytes'] > 1000
    names = {node.get('name') for node in _gltf_json(str(glb))['nodes']}
    assert {'Base plate', 'SBH-M3-0.5 x 8'} <= names
