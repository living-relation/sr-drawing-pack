import adsk.core, adsk.drawing, os, time
app = adsk.core.Application.get()
T = r"C:\projects\active\sr-drawing-pack\research\_local\logs"
print("active:", app.activeDocument.name)
scr = os.path.join(T, "gf_test.scr")
with open(scr, "w", encoding="ascii") as f:
    f.write('(entmake (list (cons 0 "TEXT") (cons 1 "4X DIA 6 THRU 4 DEEP - GF TEST") (cons 10 (list 1.0 1.2 0.0)) (cons 40 0.15) (cons 50 0.0)))\n')
    f.write('(command "_.LINE" "1,1" "4,1" "")\n')
r = app.executeTextCommand('FusionDoc.ExecuteAcadCommand _.SCRIPT "' + scr.replace("\\", "/") + '"')
print("script result:", repr(r)[:200])
time.sleep(2); adsk.doEvents()
dr = adsk.drawing.DrawingDocument.cast(app.activeDocument).drawing
em = dr.exportManager
ok = em.execute(em.createDXFExportOptions(os.path.join(T, "out", "GF_after.dxf")))
print("dxf after:", ok)
saved = app.activeDocument.save("ghostforge test")
print("drawing saved:", saved)
