import adsk.core, adsk.fusion
app = adsk.core.Application.get()
hub = app.data.dataHubs.item(0)
projs = hub.dataProjects
p0 = projs.item(0)
print("DataProject methods:", [m for m in dir(p0) if not m.startswith("_")][:60])
names = [projs.item(i).name for i in range(projs.count)]
print("n projects", len(names), "has tmp:", "_drawtest_tmp" in names)
