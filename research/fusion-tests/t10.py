import adsk.core, adsk.drawing, os, time
import os as _os
ROOT = _os.environ.get("SRDP_ROOT")  # path to your sr-drawing-pack clone; differs per PC
if not ROOT:
    raise RuntimeError("Set SRDP_ROOT to your sr-drawing-pack clone")
app = adsk.core.Application.get(); ui = app.userInterface
T = _os.path.join(ROOT, r"research\_local\logs")
print("log:", open(os.path.join(T, "gf_cmd.log")).read() if os.path.exists(os.path.join(T, "gf_cmd.log")) else "none")
d = app.activeDocument; df = d.dataFile
print("save:", d.save("gf cmd test"))
time.sleep(5); adsk.doEvents()
# Safety: only ever close a scratch document this test opened. Never the user's work.
if not d.name.startswith("SRDP_SCRATCH"):
    raise RuntimeError("Active document is not an SRDP_SCRATCH test doc; refusing to close it.")
d.close(False)
app.documents.open(df); adsk.doEvents(); time.sleep(3)
dr = adsk.drawing.DrawingDocument.cast(app.activeDocument).drawing
em = dr.exportManager
print("reopened:", app.activeDocument.name, em.execute(em.createDXFExportOptions(os.path.join(T, "out", "GF_cmd_reopened.dxf"))))
cd = ui.commandDefinitions.itemById("drawtest_gf")
if cd: cd.deleteMe()
