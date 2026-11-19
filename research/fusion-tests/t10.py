import adsk.core, adsk.drawing, os, time
app = adsk.core.Application.get(); ui = app.userInterface
T = r"C:\projects\active\sr-drawing-pack\research\_local\logs"
print("log:", open(os.path.join(T, "gf_cmd.log")).read() if os.path.exists(os.path.join(T, "gf_cmd.log")) else "none")
d = app.activeDocument; df = d.dataFile
print("save:", d.save("gf cmd test"))
time.sleep(5); adsk.doEvents()
d.close(False)
app.documents.open(df); adsk.doEvents(); time.sleep(3)
dr = adsk.drawing.DrawingDocument.cast(app.activeDocument).drawing
em = dr.exportManager
print("reopened:", app.activeDocument.name, em.execute(em.createDXFExportOptions(os.path.join(T, "out", "GF_cmd_reopened.dxf"))))
cd = ui.commandDefinitions.itemById("drawtest_gf")
if cd: cd.deleteMe()
