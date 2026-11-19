import adsk.core, adsk.drawing, os
import os as _os
ROOT = _os.environ.get("SRDP_ROOT")  # path to your sr-drawing-pack clone; differs per PC
if not ROOT:
    raise RuntimeError("Set SRDP_ROOT to your sr-drawing-pack clone")
app = adsk.core.Application.get(); ui = app.userInterface
T = _os.path.join(ROOT, r"research\_local\logs")
scr = os.path.join(T, "gf_test2.scr")
with open(scr, "w", encoding="ascii") as f:
    f.write('(entmake (list (cons 0 "TEXT") (cons 1 "GF CMD TEST") (cons 10 (list 1.0 1.5 0.0)) (cons 40 0.15) (cons 50 0.0)))\n')
_gf_h = globals().setdefault("_gf_h", [])
class Destroy(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            app.executeTextCommand('FusionDoc.ExecuteAcadCommand _.SCRIPT "' + scr.replace("\\", "/") + '"')
            open(os.path.join(T, "gf_cmd.log"), "w").write("ran\n")
        except Exception as e:
            open(os.path.join(T, "gf_cmd.log"), "w").write("err " + str(e))
class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        h = Destroy(); args.command.destroy.add(h); _gf_h.append(h)
        args.command.isAutoExecute = True if hasattr(args.command, "isAutoExecute") else None
cd = ui.commandDefinitions.itemById("drawtest_gf") or ui.commandDefinitions.addButtonDefinition("drawtest_gf", "drawtest gf", "")
c = Created(); cd.commandCreated.add(c); _gf_h.append(c)
cd.execute()
print("command launched")
