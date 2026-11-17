"""In-Fusion smoke test for SR Drawing PDF. Run from Fusion (Scripts and Add-Ins, or a Python bridge).
Opens a NEW scratch design, loads the script module, and checks that run() is present. A full PDF
export still needs the New Drawing confirmation dialog, so this smoke test does not click through
that dialog. The scratch design is closed WITHOUT saving.
"""
import importlib.util
import json
import os
import sys

import adsk.core
import adsk.fusion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else os.environ['SRDRAWINGPDF_ROOT']


def main():
    script = os.path.join(ROOT, 'SRDrawingPDF')
    if script not in sys.path:
        sys.path.insert(0, script)
    if 'SRDrawingPDF' in sys.modules:
        del sys.modules['SRDrawingPDF']
    path = os.path.join(script, 'SRDrawingPDF.py')
    spec = importlib.util.spec_from_file_location('SRDrawingPDF', path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['SRDrawingPDF'] = mod
    spec.loader.exec_module(mod)
    app = adsk.core.Application.get()
    res = {
        'has_run': callable(getattr(mod, 'run', None)),
        'has_setup_drawing': callable(getattr(mod, 'setup_drawing', None)),
        'has_add_dimensions': callable(getattr(mod, 'add_dimensions', None)),
    }
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    try:
        des = adsk.fusion.Design.cast(app.activeProduct)
        root = des.rootComponent
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(0, 0, 0),
                                                          adsk.core.Point3D.create(2, 1, 0))
        root.features.extrudeFeatures.addSimple(sk.profiles.item(0), adsk.core.ValueInput.createByReal(1),
                                                adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        res['scratch_design'] = True
        res['active_is_design'] = bool(des)
    finally:
        doc.close(False)
    print(json.dumps(res, indent=1, default=str))
    return res


def run(context):
    try:
        res = main()
        adsk.core.Application.get().userInterface.messageBox(json.dumps(res, indent=1, default=str)[:3000])
    except Exception:
        import traceback
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


if __name__ == '__main__' and 'SRDRAWINGPDF_ROOT' in os.environ:
    main()
