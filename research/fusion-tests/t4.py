import adsk.core, adsk.fusion
app = adsk.core.Application.get()
P = adsk.core.Point3D.create
projs = app.data.dataHubs.item(0).dataProjects
proj = [projs.item(i) for i in range(projs.count) if projs.item(i).name == "Default Project"][0]
root = proj.rootFolder
tmp = root.dataFolders.itemByName("_drawtest_tmp") or root.dataFolders.add("_drawtest_tmp")
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
des = adsk.fusion.Design.cast(app.activeProduct)
des.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
rc = des.rootComponent
sk = rc.sketches.add(rc.xYConstructionPlane)
sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0, 0), P(8, 5, 0))
ext = rc.features.extrudeFeatures.addSimple(sk.profiles.item(0), adsk.core.ValueInput.createByReal(1.0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
top = [f for f in ext.endFaces][0]
sk2 = rc.sketches.add(top)
for x, y in ((1.2, 1.2), (6.8, 1.2), (1.2, 3.8), (6.8, 3.8)):
    sk2.sketchCurves.sketchCircles.addByCenterRadius(sk2.modelToSketchSpace(P(x, y, 1)), 0.3)
sk2.sketchCurves.sketchLines.addTwoPointRectangle(sk2.modelToSketchSpace(P(2.5, 1.5, 1)), sk2.modelToSketchSpace(P(5.5, 3.5, 1)))
profs = adsk.core.ObjectCollection.create()
for i in range(sk2.profiles.count):
    pr = sk2.profiles.item(i)
    a = pr.areaProperties().area
    if a < 0.5 or abs(a - 6.0) < 0.01: profs.add(pr)
cut = rc.features.extrudeFeatures.createInput(profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
cut.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-0.4))
rc.features.extrudeFeatures.add(cut)
rc.bRepBodies.item(0).name = "TestPlate"
ok = doc.saveAs("DT_TestPlate", tmp, "drawing tool test", "")
print("profiles cut:", profs.count, "saved:", ok, "faces:", rc.bRepBodies.item(0).faces.count)
