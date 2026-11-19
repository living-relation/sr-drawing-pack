import adsk.core, adsk.drawing, os, time
import os as _os
ROOT = _os.environ.get("SRDP_ROOT")  # path to your sr-drawing-pack clone; differs per PC
if not ROOT:
    raise RuntimeError("Set SRDP_ROOT to your sr-drawing-pack clone")
app = adsk.core.Application.get()
T = _os.path.join(ROOT, r"research\_local\logs")
d = app.activeDocument
df = d.dataFile
print("closing:", d.name, "versions:", df.versionNumber)
# Safety: only ever close a scratch document this test opened. Never the user's work.
if not d.name.startswith("SRDP_SCRATCH"):
    raise RuntimeError("Active document is not an SRDP_SCRATCH test doc; refusing to close it.")
d.close(False)
d2 = app.documents.open(df.parentFolder.dataFiles.itemById(df.id) if hasattr(df.parentFolder.dataFiles, "itemById") else df)
adsk.doEvents(); time.sleep(3)
dr = adsk.drawing.DrawingDocument.cast(app.activeDocument).drawing
em = dr.exportManager
print("reopened:", app.activeDocument.name, em.execute(em.createDXFExportOptions(os.path.join(T, "out", "GF_reopened.dxf"))))
print("tmp folder files:", [(df.parentFolder.dataFiles.item(i).name, df.parentFolder.dataFiles.item(i).fileExtension) for i in range(df.parentFolder.dataFiles.count)])
