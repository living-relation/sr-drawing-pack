"""STEP -> one drawing sheet (PDF + DXF + PNG) with the XQ render modes (ADR-051, ADR-052). Research, not the app.

Sheet 1: front, top and right (third angle) and the iso view, laid out like research/real-test/fast_sheet.py, in the
handbuilt-cad sheet frame and title block. Lines come from xq_render.run(): exact B-rep edges with visibility from the
GPU depth buffer. The DXF carries polylines (the engine writes polylines only); true ARC entities need the engine.

Also writes <name>.sparkcad.json, the hand-over record sparkCAD stores per item (BACKLOG 2026-11-24): kind, part
number, description, rev and the file names. Nothing is uploaded.

Usage:  python xq_sheet.py <model.step> <out_dir> [--mode exact|quick] [--pn PN] [--desc TEXT] [--rev A] [--kind ASY]
Needs:  HBCAD_ROOT (handbuilt-cad clone, read-only) and the packages of xq_render.py. Timings in <out_dir>/xq_sheet.json.
"""
import os, sys, json, time, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import xq_render as XQ
KINDS = ("PRT", "SUB", "ASY", "CBL", "WIR")                      # sparkCAD item kinds


PAPER_STEP = 0.1          # mm on paper between kept points on a curve (sagitta under 0.001 mm for radii over 1 mm)


def thin_for_paper(L, scale=None):
    """Keep about one point per PAPER_STEP on paper along each polyline (both ends and turn-backs kept). XQ samples
    curves at depth-buffer pixel spacing, far finer than a printed line needs."""
    out = {}
    for v, (vis, tan, cru) in L.items():
        def thin(p, step):
            if len(p) < 4: return p
            d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
            keep = np.r_[True, np.diff(np.floor(d / step)) > 0]; keep[-1] = True
            a, b, c = p[:-2], p[1:-1], p[2:]; keep[1:-1] |= ((b - a) * (c - b)).sum(1) <= 0
            return p[keep]
        step = PAPER_STEP / (scale or 1.0)
        out[v] = ([thin(p, step) for p in vis], [thin(p, step) for p in tan], cru)
    return out


def _scale_guess(dwg, L):
    """Sheet scale before layout (same rule as build_sheet), for point thinning."""
    ext = {v: np.ptp(np.vstack(vis), axis=0) if vis else np.zeros(2) for v, (vis, tan, cru) in L.items()}
    return XQ.pick_scale(min((262 - 28) / (ext["front"][0] + ext["right"][0]), (172 - 24) / (ext["front"][1] + ext["top"][1])))


def _dxf_lines(dxf, lines, layers):
    """Add the view polylines to a DXF the engine wrote (frame and text). Runs in its own process."""
    import ezdxf
    doc = ezdxf.readfile(dxf); msp = doc.modelspace()
    for sty, pl in lines.items():
        at = {"layer": layers[sty][0]}
        for p in pl: msp.add_lwpolyline(p.tolist(), format="xy", dxfattribs=at)
    doc.saveas(dxf)


def render_fast(dwg, sh, base, png=False):
    """PDF, DXF (and PNG) of one sheet. The engine draws every polyline with its own plot call (about 25 s for 50,000
    lines); here each line style of the views is one call, lines joined by NaN breaks (same look), and the DXF view
    lines are written by a second process while the PDF renders. Frame, title block and text still come from the
    engine. Candidate change for handbuilt-cad dwg.render (BACKLOG 2026-11-25)."""
    import multiprocessing as mp, tempfile
    view_sty = ("vis", "tan")
    rest = [it for it in sh.items if not (it[0] == "pl" and it[2] in view_sty)]
    lines = {k: [it[1] for it in sh.items if it[0] == "pl" and it[2] == k] for k in view_sty}
    tmp = tempfile.mkdtemp(); fr = dwg.Sheet(); fr.items = rest
    dwg.render([fr], os.path.join(tmp, "frame.pdf"), base + ".dxf", None)          # frame + text DXF (small)
    proc = mp.get_context("spawn").Process(target=_dxf_lines, args=(base + ".dxf", lines, dwg.DXF_LAYER)); proc.start()
    pdf = dwg.Sheet(); pdf.items = list(rest)
    for k, pl in lines.items():
        if pl: pdf.items.append(("pl", np.vstack([np.vstack([p, [[np.nan, np.nan]]]) for p in pl])[:-1], k, False))
    dwg.render([pdf], base + ".pdf", None, base if png else None)
    proc.join()
    if proc.exitcode: raise RuntimeError("DXF writer failed")


def build_sheet(dwg, L, info):
    """Sheet 1 from {view: (vis, tan, (c, r, u))}: third angle, no view labels (ADR-026), as fast_sheet.py. Returns
    (sheet, sheet scale)."""
    V = {v: dwg.View(None, v, 1.0, polys=(vis, [], cru, tan), name=v) for v, (vis, tan, cru) in L.items()}
    gx, gy = 28, 24
    smax = min((262 - gx) / (V["front"].w + V["right"].w), (172 - gy) / (V["front"].h + V["top"].h)); s = XQ.pick_scale(smax)
    for v in V.values(): v.scale = s; v.w = (v.umax - v.umin) * s; v.h = (v.vmax - v.vmin) * s
    f, tp, rt, iso = V["front"], V["top"], V["right"], V["iso"]
    x0, y0 = 24, 86
    f.place(x0 + f.w / 2, y0 + f.h / 2); tp.place(f.cx, y0 + f.h + gy + tp.h / 2); rt.place(x0 + f.w + gx + rt.w / 2, f.cy)
    k = XQ.pick_scale(s * min(1.0, 118 / max(iso.w, 1e-9), 120 / max(iso.h, 1e-9))) / s
    iso.scale = s * k; iso.w *= k; iso.h *= k; iso.place(352, 168)
    sh = dwg.Sheet()
    for v in V.values(): v.draw(sh)
    if abs(iso.scale - s) > 1e-9: sh.txt(iso.cx, iso.cy - iso.h / 2 - 4, f"SCALE {dwg.scale_str(iso.scale)}", h=3.0, va="top")
    dwg.frame(sh, dict(info, scale=dwg.scale_str(s)), 1, 1)
    return sh, s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("step"); ap.add_argument("out")
    ap.add_argument("--mode", choices=sorted(XQ.MODES), default="exact")
    ap.add_argument("--pn", default="-"); ap.add_argument("--desc", default=""); ap.add_argument("--rev", default="-")
    ap.add_argument("--kind", choices=KINDS, default="ASY"); ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--png", action="store_true", help="also write <name>_sh1.png (for review)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); t0 = time.perf_counter()
    name = os.path.splitext(os.path.basename(a.step))[0]

    T, L = XQ.run(a.step, a.out, a.mode, workers=a.workers or None, png=False, title=name)
    t = time.perf_counter()
    sys.path.insert(0, os.path.join(os.environ["HBCAD_ROOT"], "drawing"))
    import dwg
    sh, s = build_sheet(dwg, thin_for_paper(L, _scale_guess(dwg, L)), dict(title=(a.desc or name).upper()[:60], pn=a.pn, rev=a.rev, material="SEE BOM",
                        source=os.path.basename(a.step), drawn="-", project=f"{XQ.MODES[a.mode].upper()} - NOT A RELEASED DRAWING"))
    base = os.path.join(a.out, name)
    render_fast(dwg, sh, base, a.png)
    T["sheet_s"] = round(time.perf_counter() - t, 2); T["scale"] = dwg.scale_str(s)

    # ---- sparkCAD hand-over record (no upload)
    rec = dict(kind=a.kind, part_number=a.pn, description=a.desc or name, rev=a.rev, render_mode=XQ.MODES[a.mode],
               drawing_pdf=name + ".pdf", drawing_dxf=name + ".dxf", step=os.path.basename(a.step))
    json.dump(rec, open(base + ".sparkcad.json", "w"), indent=1)
    T["sheet_total_s"] = round(time.perf_counter() - t0, 2)
    json.dump(T, open(os.path.join(a.out, "xq_sheet.json"), "w"), indent=1)
    print(json.dumps({k: T[k] for k in ("mode", "load_s", "total_s", "sheet_s", "sheet_total_s", "scale")}))


if __name__ == "__main__":
    main()
