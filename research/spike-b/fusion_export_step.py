"""Spike B, Fusion side: build the test plate in a new unsaved design, export STEP, close without saving.

Run inside Fusion through its built-in MCP script tool. Set OUT_STEP to a path under
research/_local/out/spike-b/ in your clone before running. Touches no existing document.
"""
import adsk.core, adsk.fusion, time, os

OUT_STEP = os.environ.get("SRDP_SPIKE_B_STEP", "")

def run(_context: str):
    if not OUT_STEP: raise RuntimeError("Set OUT_STEP (or SRDP_SPIKE_B_STEP) to the STEP path to write")
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    root = des.rootComponent
    P = adsk.core.Point3D.create; V = adsk.core.ValueInput.createByReal     # API lengths are centimetres
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addCenterPointRectangle(P(0, 0, 0), P(4, 2.5, 0))
    for x in (-3, 3):
        for y in (-1.5, 1.5):
            sk.sketchCurves.sketchCircles.addByCenterRadius(P(x, y, 0), 0.3)
    prof = max([sk.profiles.item(i) for i in range(sk.profiles.count)], key=lambda p: p.areaProperties().area)
    root.features.extrudeFeatures.addSimple(prof, V(1.0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    sk2 = root.sketches.add(root.xYConstructionPlane)
    sk2.sketchCurves.sketchLines.addCenterPointRectangle(P(0, 0, 0), P(1, 1, 0))
    root.features.extrudeFeatures.addSimple(sk2.profiles.item(0), V(0.4), adsk.fusion.FeatureOperations.CutFeatureOperation)
    body = root.bRepBodies.item(0)
    t = time.time(); em = des.exportManager
    ok = em.execute(em.createSTEPExportOptions(OUT_STEP, root))
    print("export ok", ok, "seconds", round(time.time() - t, 2), "bytes", os.path.getsize(OUT_STEP))
    print("faces", body.faces.count, "edges", body.edges.count, "volume_cm3", round(body.volume, 4))
    doc.close(False)
