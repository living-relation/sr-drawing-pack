import sys, zipfile, os
import os as _os
ROOT = _os.environ.get("SRDP_ROOT")  # path to your sr-drawing-pack clone; differs per PC
if not ROOT:
    raise RuntimeError("Set SRDP_ROOT to your sr-drawing-pack clone")
from pathlib import Path
sys.path.insert(0, _os.path.join(ROOT, r"research\_local\refs\ants2"))
import core.app_config as cfg
cfg.FUSION_PATH = Path(os.environ["LOCALAPPDATA"]) / "Autodesk" / "Autodesk Fusion 360"
cfg.OUTPUT_DIR = Path(_os.path.join(ROOT, r"research\_local\out"))
import core.fusion_scan as fs, core.drawing_extract as de
fs.FUSION_PATH = cfg.FUSION_PATH; de.OUTPUT_DIR = cfg.OUTPUT_DIR
found = fs.find_drawings()
print("f2d found on Windows cache:", len(found))
for d in found[:5]: print(" ", d["name"], d["path"][-60:])
mine = [d for d in found if "DT_TestPlate" in d["name"]] or found[:1]
if mine:
    with zipfile.ZipFile(mine[0]["path"]) as z: print("zip entries:", [n for n in z.namelist() if n.lower().endswith((".dwg", ".png"))][:6])
    print("extracted:", de.extract_dwg(mine[0]["path"], "ANTS_" + mine[0]["name"].replace(" ", "_")))
