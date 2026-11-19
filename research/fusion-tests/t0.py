import adsk.core, adsk.fusion
app = adsk.core.Application.get()
print("version", app.version)
import adsk.drawing as d
print("drawing API names:", [n for n in dir(d) if "Export" in n or "Manager" in n or "Create" in n])
print("hubs:", [h.name for h in app.data.dataHubs])
p = app.data.activeProject
print("active project:", p.name if p else None)
