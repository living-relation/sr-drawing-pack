"""STEP to GLB for the 3D model viewer (ADR-066).

GLB is the binary glTF file web pages show. The part tree and part names from
the STEP are kept, so the viewer can list, hide, show and explode parts.
Colors come from the STEP when it has them.

    python -m vieweng.glb model.step model.glb [--fine]

Needs OCP (cadquery-ocp). No Fusion import.
"""
import math
import os
import sys
import time


def _read(path):
    from OCP.IFSelect import IFSelect_ReturnStatus
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFApp import XCAFApp_Application
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString('XmlXCAF'))
    app.NewDocument(TCollection_ExtendedString('MDTV-XCAF'), doc)
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    reader.SetLayerMode(False)
    if reader.ReadFile(path) != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise RuntimeError('could not read STEP: %s' % path)
    if not reader.Transfer(doc):
        raise RuntimeError('could not transfer STEP: %s' % path)
    return doc


def _free_shapes(doc):
    from OCP.collections import Sequence_TDF_Label
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = Sequence_TDF_Label()
    tool.GetFreeShapes(labels)
    return tool, [labels.Value(i) for i in range(1, labels.Length() + 1)]


def _mesh(doc, fine=False):
    """Mesh every free shape. Deflection scales with the model size."""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    tool, labels = _free_shapes(doc)
    box = Bnd_Box()
    shapes = [tool.GetShape_s(label) for label in labels]
    for shape in shapes:
        BRepBndLib.Add_s(shape, box)
    if box.IsVoid():
        raise RuntimeError('STEP has no geometry')
    lo, hi = box.CornerMin(), box.CornerMax()
    diag = lo.Distance(hi)
    linear = diag * (0.0002 if fine else 0.001)
    angular = 0.2 if fine else 0.5
    for shape in shapes:
        BRepMesh_IncrementalMesh(shape, linear, False, angular, True)
    return diag


def step_to_glb(step_path, glb_path, fine=False):
    """Write glb_path from step_path. Returns a small report dict."""
    from OCP.Message import Message_ProgressRange
    from OCP.RWGltf import RWGltf_CafWriter
    from OCP.RWMesh import RWMesh_CoordinateSystem, RWMesh_NameFormat
    from OCP.TCollection import TCollection_AsciiString
    from OCP.collections import IndexedDataMap_TCollection_AsciiString_TCollection_AsciiString as _Info
    start = time.time()
    doc = _read(step_path)
    read_s = time.time() - start
    diag = _mesh(doc, fine)
    mesh_s = time.time() - start - read_s
    writer = RWGltf_CafWriter(TCollection_AsciiString(glb_path), True)
    # STEP is Z up in mm; glTF is Y up in metres. The viewer reads the file as is.
    converter = writer.ChangeCoordinateSystemConverter()
    converter.SetInputLengthUnit(0.001)
    converter.SetInputCoordinateSystem(RWMesh_CoordinateSystem.RWMesh_CoordinateSystem_Zup)
    converter.SetOutputCoordinateSystem(RWMesh_CoordinateSystem.RWMesh_CoordinateSystem_glTF)
    writer.SetNodeNameFormat(RWMesh_NameFormat.RWMesh_NameFormat_ProductOrInstance)
    writer.SetMeshNameFormat(RWMesh_NameFormat.RWMesh_NameFormat_Product)
    writer.SetMergeFaces(True)
    writer.SetParallel(True)
    if not writer.Perform(doc, _Info(), Message_ProgressRange()):
        raise RuntimeError('could not write GLB: %s' % glb_path)
    return {
        'glb': glb_path,
        'bytes': os.path.getsize(glb_path),
        'model_size_mm': round(diag, 1),
        'read_s': round(read_s, 2),
        'mesh_s': round(mesh_s, 2),
        'total_s': round(time.time() - start, 2),
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    fine = '--fine' in args
    args = [a for a in args if a != '--fine']
    if len(args) != 2:
        print(__doc__)
        return 2
    print(step_to_glb(args[0], args[1], fine=fine))
    return 0


if __name__ == '__main__':
    sys.exit(main())
