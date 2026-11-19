import adsk.core, logging, types, time
app = adsk.core.Application.get()
src = open(r"C:\projects\active\sr-drawing-pack\research\_local\refs\nvsdef_fusion360-mcp\addon\server\render_drawing.py", encoding="utf-8").read()
src = src.replace("from . import get_logger", "get_logger = lambda n: __import__('logging').getLogger(n)")
mod = types.ModuleType("nv_rd"); exec(compile(src, "render_drawing.py", "exec"), mod.__dict__)
class H(mod.RenderDrawingMixin):
    def __init__(self): self.app = app
d = app.activeDocument
print("active:", d.name, "dataFile:", bool(d.dataFile), "upload:", d.dataFile.isComplete if d.dataFile else None)
t = time.time()
res = H().create_drawing(standard="ASME", units="mm", sheet_size="BASME", dimension_strategy="automatic", center_marks=False, open_drawing=True)
print("result:", res, "secs:", round(time.time() - t, 1))
print("now active:", app.activeDocument.name)
