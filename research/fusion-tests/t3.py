import adsk.core
app = adsk.core.Application.get()
projs = app.data.dataHubs.item(0).dataProjects
print([projs.item(i).name for i in range(projs.count)])
f = projs.item(0).rootFolder
print("folder deleteMe:", hasattr(f, "deleteMe"), "folders.add:", hasattr(f.dataFolders, "add"))
