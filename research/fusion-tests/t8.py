import adsk.core, adsk.drawing, os, time
app = adsk.core.Application.get()
T = r"C:\projects\active\sr-drawing-pack\research\_local\logs"
d = app.activeDocument
df = d.dataFile
print("closing:", d.name, "versions:", df.versionNumber)
d.close(False)
d2 = app.documents.open(df.parentFolder.dataFiles.itemById(df.id) if hasattr(df.parentFolder.dataFiles, "itemById") else df)
adsk.doEvents(); time.sleep(3)
dr = adsk.drawing.DrawingDocument.cast(app.activeDocument).drawing
em = dr.exportManager
print("reopened:", app.activeDocument.name, em.execute(em.createDXFExportOptions(os.path.join(T, "out", "GF_reopened.dxf"))))
print("tmp folder files:", [(df.parentFolder.dataFiles.item(i).name, df.parentFolder.dataFiles.item(i).fileExtension) for i in range(df.parentFolder.dataFiles.count)])
