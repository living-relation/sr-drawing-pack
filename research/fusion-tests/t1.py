import adsk.core
app = adsk.core.Application.get()
hub = app.data.dataHubs.item(0)
found = []
def walk(f, path, depth=0):
    if depth > 3 or len(found) > 15: return
    for i in range(f.dataFiles.count):
        df = f.dataFiles.item(i)
        if df.fileExtension in ("f2d",):
            found.append((path + "/" + df.name, df.fileExtension, df.dateModified, df.id))
    for i in range(f.dataFolders.count):
        walk(f.dataFolders.item(i), path + "/" + f.dataFolders.item(i).name, depth + 1)
projs = hub.dataProjects
print("projects:", [projs.item(i).name for i in range(projs.count)])
print("project deleteMe?", hasattr(projs.item(0), "deleteMe"))
for i in range(projs.count):
    p = projs.item(i)
    walk(p.rootFolder, p.name)
for x in found: print(x)
