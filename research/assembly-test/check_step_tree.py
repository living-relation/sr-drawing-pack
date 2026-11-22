"""Read the assembly STEP back and report what survives: tree, names, instance counts, positions,
whether the BOM can be rebuilt from the STEP alone, and hidden-line time per view.

Usage:  python check_step_tree.py <out_dir>        (the folder build_assembly.py wrote into)
Needs:  HBCAD_ROOT = path to a handbuilt-cad clone (read-only), run with that clone's Python.
Prints one JSON object. Exit code 1 when a check fails.
"""
import json, os, re, sys, time
from collections import Counter
from build123d import Compound, import_step
import model_data as D


def step_names(path):
    """Product names as written in the STEP text (the importer changes some characters)."""
    t = open(path, encoding="utf-8", errors="replace").read()
    names = [re.sub(r"\s*\n\s*", "", m) for m in re.findall(r"=\s*PRODUCT\(\s*'((?:[^']|'')*)'", t)]
    counts = dict(products=len(names), instances=len(re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\(", t)),
                  solid_breps=len(re.findall(r"MANIFOLD_SOLID_BREP\(", t)),
                  schema=(re.findall(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']*)'", t) or ["?"])[0])
    return names, counts

def mangle(name): return re.sub(r"[^A-Za-z0-9\-]", "_", name)

def read_tree(path):
    """(root node, counts). A node: dict(label, name, shape, children). name = the STEP product name."""
    names, counts = step_names(path); back = {mangle(n): n for n in names}
    def node(c): return dict(label=c.label, name=back.get(c.label, c.label), shape=c, children=[node(k) for k in c.children])
    return node(import_step(path)), counts

def bom(node):
    """(name, qty, child rows) per distinct child, in first-seen order. Quantity = how many times it is placed."""
    seen = {}
    for k in node["children"]: seen.setdefault(k["name"], []).append(k)
    return [(n, len(ks), bom(ks[0])) for n, ks in seen.items()]

def leaves(node, out=None):
    out = [] if out is None else out
    if node["children"]:
        for k in node["children"]: leaves(k, out)
    else: out.append(node)
    return out

def box(s):
    b = s.bounding_box(); return (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z)


if __name__ == "__main__":
    out = sys.argv[1]; step = os.path.join(out, D.ASM_PN + ".step")
    root, counts = read_tree(step)
    got = (root["name"], 1, bom(root))
    lv = leaves(root)
    # positions: every leaf of the STEP against the same leaf of a freshly built model (bounding box and volume)
    import build_assembly
    fresh = build_assembly.build()
    def fresh_leaves(c, o):
        if c.children:
            for k in c.children: fresh_leaves(k, o)
        else: o.append(c)
        return o
    fl = fresh_leaves(fresh, [])
    dpos = max(abs(a - b) for x, y in zip(lv, fl) for a, b in zip(box(x["shape"]), box(y))) if len(lv) == len(fl) else None
    dvol = max(abs(x["shape"].volume - y.volume) for x, y in zip(lv, fl)) if len(lv) == len(fl) else None
    changed = sorted({n["name"] for n in lv + [root] if n["label"] != n["name"]})
    res = dict(
        step=os.path.basename(step), schema=counts["schema"],
        tree_survives=got == D.EXPECTED_TREE,
        tree=got,
        names_in_step_text_ok=sorted(step_names(step)[0]) == sorted(D.PARTS),
        names_changed_by_importer=changed,
        products=counts["products"], instances=counts["instances"], solid_breps=counts["solid_breps"],
        instances_expected=len(lv) + 1, shared_shapes=counts["solid_breps"] == len({n["name"] for n in lv}),
        leaf_solids=len(lv), max_position_error_mm=None if dpos is None else round(dpos, 6),
        max_volume_error_mm3=None if dvol is None else round(dvol, 6),
        bom_from_step=dict(rows_and_quantities=got == D.EXPECTED_TREE, part_numbers=True,
                           description=False, material=False,
                           note="The STEP carries one name per component. Description and material are not in it; they come from the spec table."),
    )
    hb = os.environ.get("HBCAD_ROOT")
    if hb:
        sys.path.insert(0, os.path.join(hb, "drawing")); import dwg
        comp = Compound([n["shape"] for n in lv]); t = {}
        for v in ("front", "top", "right", "iso"):
            t0 = time.perf_counter(); dwg.View(comp, v, 1.0); t[v] = round(time.perf_counter() - t0, 2)
        res["hidden_line_seconds"] = t
    else: res["hidden_line_seconds"] = "skipped (HBCAD_ROOT not set)"
    res["ok"] = bool(res["tree_survives"] and res["names_in_step_text_ok"] and res["instances"] == res["instances_expected"]
                     and dpos is not None and dpos < 1e-4 and dvol < 1e-3)
    json.dump(res, open(os.path.join(out, "step_tree_check.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["ok"] else 1)
