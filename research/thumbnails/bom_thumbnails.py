"""BOM thumbnails with the F3D viewer: one shaded picture per BOM row of the test assembly (ADR-003).

Usage:  python bom_thumbnails.py <assembly.step> <out_dir>
Needs:  F3D_EXE = path to f3d.exe (F3D 4.x, https://f3d.app; BSD 3-Clause), and a Python with build123d
        and matplotlib (the handbuilt-cad clone's Python has both).
Reads the STEP tree, writes one small STEP per distinct BOM row, asks F3D's command line for a picture of
each, and lays the pictures out beside the BOM fields in one page (PNG + PDF). Test only: the BOM fields
come from research/assembly-test/model_data.py; in the product they come from the Fusion data file (ADR-028).
"""
import os, subprocess, sys, time, json, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assembly-test"))
import model_data as D
from check_step_tree import read_tree
from build123d import Compound, export_step
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

F3D = os.environ.get("F3D_EXE")
if not F3D or not os.path.isfile(F3D): raise SystemExit("Set F3D_EXE to f3d.exe")
STEP, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
PX = 420

def rows(node, prefix=""):
    """Indented BOM rows in first-seen order: (item number, name, quantity, first node)."""
    seen = {}
    for k in node["children"]: seen.setdefault(k["name"], []).append(k)
    out = []
    for i, (name, ks) in enumerate(seen.items(), 1):
        item = f"{prefix}{i}"; out.append((item, name, len(ks), ks[0])); out += rows(ks[0], item + ".")
    return out

def thumbnail(shape, png):
    """Shaded trimetric picture of one part or sub-assembly, in its own position (not where it sits in the assembly)."""
    part = os.path.splitext(png)[0] + ".step"
    inv = shape.location.inverse()                       # undo the placement, so a part shows the way it was modelled
    export_step(Compound([s.moved(inv) for s in shape.solids()]), part)
    t = time.perf_counter()
    r = subprocess.run([F3D, part, "--output", png, f"--resolution={PX},{PX}", "--no-background", "--grid=false", "--axis=false",
                        "--filename=false", "--edges", "--up=+Z", "--camera-direction=-1,1.55,-1.15", "--camera-orthographic"],
                       capture_output=True, encoding='utf-8', errors='replace')
    os.remove(part)
    if r.returncode or not os.path.isfile(png): raise RuntimeError(f"F3D failed on {part}: {r.stderr[-300:]}")
    return time.perf_counter() - t

root, _ = read_tree(STEP); bom = rows(root); times = {}
for item, name, qty, node in bom:
    times[item] = round(thumbnail(node["shape"], os.path.join(OUT, f"thumb_{item.replace('.', '_')}.png")), 2)

# one page: picture, item, qty, part number, description, material
n = len(bom); rh = 1.0
fig = plt.figure(figsize=(11, 1.2 + n * rh)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 11); ax.set_ylim(0, 1.2 + n * rh); ax.axis("off")
cols = [("", 0.2), ("ITEM", 1.5), ("QTY", 2.2), ("PART NUMBER", 2.8), ("DESCRIPTION", 5.4), ("MATERIAL / SPEC", 8.7)]
top = 0.6 + n * rh
ax.text(0.2, top + 0.3, f"BILL OF MATERIALS WITH THUMBNAILS  -  {root['name']}", fontsize=11, fontweight="bold", va="center")
for label, x in cols: ax.text(x, top, label, fontsize=8, fontweight="bold", va="center")
ax.plot([0.2, 10.8], [top - 0.15] * 2, color="k", lw=0.8)
for i, (item, name, qty, node) in enumerate(bom):
    y = top - 0.15 - (i + 0.5) * rh; p = D.PARTS.get(name, {})
    img = plt.imread(os.path.join(OUT, f"thumb_{item.replace('.', '_')}.png"))
    ax.imshow(img, extent=(0.25, 0.25 + rh * 0.95, y - rh * 0.475, y + rh * 0.475), aspect="auto", zorder=2)
    indent = 0.15 * item.count(".")
    for text, x in ((item, 1.5 + indent), (str(qty), 2.2), (name, 2.8), (textwrap.fill(p.get("desc", ""), 40), 5.4), (p.get("mat", ""), 8.7)):
        ax.text(x, y, text, fontsize=7.5, va="center")
    ax.plot([0.2, 10.8], [y - rh / 2] * 2, color="0.6", lw=0.4)
ax.set_xlim(0, 11); ax.set_ylim(0, 1.2 + n * rh)
fig.savefig(os.path.join(OUT, "bom_thumbnails.png"), dpi=130); fig.savefig(os.path.join(OUT, "bom_thumbnails.pdf")); plt.close(fig)

res = dict(rows=len(bom), seconds_per_thumbnail=times, total_seconds=round(sum(times.values()), 2), pixels=PX)
json.dump(res, open(os.path.join(OUT, "bom_thumbnails.json"), "w"), indent=1); print(json.dumps(res, indent=1))
