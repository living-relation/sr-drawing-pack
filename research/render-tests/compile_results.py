"""Compile every render-test run into one comparison table (H52, 2026-11-24).

Usage:  python compile_results.py <render-tests out dir>   (default: research/_local/out/render-tests)
Reads <out>/<model>/render_modes.json written by render_modes.py and prints a Markdown table plus a JSON summary
(<out>/summary.json). Times and sizes are the "after" (anti-aliasing fixes) runs, four views each.
"""
import json, os, sys

MODES = ("UHQ", "HQ", "DRAFT", "FAST")


def model_row(d):
    p = d.get("prep", {})
    row = {"model": d.get("model"), "step_mb": d.get("step_mb"), "solids": p.get("solids"), "faces": p.get("faces"),
           "import_s": round((p.get("import_s") or 0) + (p.get("cache_s") or 0), 1)}
    files = d.get("files", {})
    for m in MODES:
        views = d.get("table", {}).get(m + "_after", {})
        ok = [v for v in views.values() if v.get("status") == "ok"]
        row[m] = {"views_ok": len(ok), "views": len(views),
                  "s": round(sum(v.get("seconds") or 0 for v in ok), 1),
                  "lines": sum((v.get("lines") or 0) for v in ok),
                  "arcs": sum((v.get("arcs") or 0) + (v.get("circles") or 0) + (v.get("true_arcs") or 0) for v in ok),
                  "dxf_kb": (files.get(m + "_after") or {}).get("dxf_kb")}
    return row


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "_local", "out", "render-tests")
    rows = []
    for name in sorted(os.listdir(out)):
        f = os.path.join(out, name, "render_modes.json")
        if os.path.isfile(f):
            rows.append(model_row(json.load(open(f))))
    rows.sort(key=lambda r: r["faces"] or 0)
    print("| Model | Solids | Faces | STEP MB | " + " | ".join(f"{m} s (views) | {m} DXF kB" for m in MODES) + " |")
    print("|---" * (4 + 2 * len(MODES)) + "|")
    for r in rows:
        cells = [f"{r[m]['s']} ({r[m]['views_ok']}/{r[m]['views']}) | {r[m]['dxf_kb']}" for m in MODES]
        print(f"| {r['model']} | {r['solids']} | {r['faces']} | {r['step_mb']} | " + " | ".join(cells) + " |")
    json.dump(rows, open(os.path.join(out, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
