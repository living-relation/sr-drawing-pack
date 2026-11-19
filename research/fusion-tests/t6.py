import adsk.core, adsk.drawing, ast, os, time
app = adsk.core.Application.get()
T = r"C:\projects\active\sr-drawing-pack\research\_local\out"
os.makedirs(T, exist_ok=True)
dd = adsk.drawing.DrawingDocument.cast(app.activeDocument)
dr = dd.drawing
sh = dr.sheets if hasattr(dr, "sheets") else None
print("sheets:", sh.count if sh else "n/a")
if sh:
    for i in range(sh.count):
        s = sh.item(i)
        info = {a: getattr(s, a).count for a in ("drawingViews", "dimensions", "drawingSymbols", "customTables", "tables") if hasattr(s, a) and hasattr(getattr(s, a), "count")}
        print(" sheet", i, s.name if hasattr(s, "name") else "", info)
# fusion-export: pull export_drawing() verbatim from its source
src = open(r"C:\projects\active\sr-drawing-pack\research\_local\refs\nofuturekid_fusion-export\FusionExport\FusionExport.py", encoding="utf-8").read()
fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "export_drawing"][0]
g = {"os": os, "adsk": adsk}; exec(compile(ast.Module([fn], []), "fe", "exec"), g)
t = time.time()
print("fusion-export:", g["export_drawing"](dr, T, "FE_TestPlate", ["pdf", "dwg"], lambda s: None), round(time.time() - t, 1), "s")
# Exporter-X: same calls as its folderExport2D command
em = dr.exportManager
for ext, mk in (("dxf", em.createDXFExportOptions), ("dwg", em.createDWGExportOptions)):
    t = time.time(); ok = em.execute(mk(os.path.join(T, "EX_TestPlate." + ext))); print("exporter-x", ext, ok, round(time.time() - t, 1), "s")
for f in sorted(os.listdir(T)): print(f, os.path.getsize(os.path.join(T, f)))
