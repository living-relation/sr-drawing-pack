"""Editor slice, local server: serves the editor page, view geometry, the drawing document and PDF export.

Usage:  python server.py [--port 8791] [--step model.step] [--doc drawing.json] [--out out_dir]
Needs:  HBCAD_ROOT = path to a handbuilt-cad clone (read-only, never edited), run with that clone's Python.
Standard library only, bound to 127.0.0.1. With no --step it builds the spike test plate
(80 x 50 x 10 mm, four 6 mm holes, 20 x 20 x 4 mm pocket in the bottom face).
The document and the exports go under research/_local/editor-slice/ (git-ignored) unless told otherwise.
"""
import argparse, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HB = os.environ.get("HBCAD_ROOT")
if not HB: raise SystemExit("Set HBCAD_ROOT to your handbuilt-cad clone")
sys.path.insert(0, os.path.join(HB, "drawing"))
import dwg                                   # the engine, imported read-only
import numpy as np
from build123d import Box, Cylinder, Pos, import_step

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import docmodel as dm

STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/editor.js": ("editor.js", "application/javascript; charset=utf-8")}
LOCAL = os.path.normpath(os.path.join(HERE, "..", "_local", "editor-slice"))
LOCK = threading.Lock()

def plate():
    p = Box(80, 50, 10)
    for x in (-30, 30):
        for y in (-15, 15):
            p -= Pos(x, y, 0) * Cylinder(3, 10)
    return p - Pos(0, 0, -3) * Box(20, 20, 4)

class Model:
    """The 3D model and its 2D views. One hidden-line run per camera, then cached."""
    def __init__(s, shape, source): s.shape, s.source, s.cache = shape, source, {}
    def polys(s, cam, up):
        """Engine projection: (visible, [], basis, tangent). The engine returns no hidden lines at all,
        and tangent edges only for a pictorial camera."""
        key = tuple(round(float(x), 6) for x in tuple(cam) + tuple(up))
        if key not in s.cache:
            s.cache[key] = dwg.project(s.shape, (tuple(cam), tuple(up)), defl=0.02, return_tangent=True)
        return s.cache[key]
    def bbox(s, cam, up):
        vis = s.polys(cam, up)[0]; allp = np.vstack(vis) if vis else np.zeros((1, 2))
        return [float(x) for x in (*allp.min(0), *allp.max(0))]             # umin, vmin, umax, vmax in model mm
    def size(s, cam, up): b = s.bbox(cam, up); return (b[2] - b[0], b[3] - b[1])
    def view_json(s, cam, up):
        vis, hid, _, tan = s.polys(cam, up)
        assert not hid, "the engine must not return hidden lines"
        rnd = lambda lines: [[[round(float(x), 3), round(float(y), 3)] for x, y in p] for p in lines if len(p) > 1]
        return {"cam": list(cam), "up": list(up), "name": dm.standard_name(cam, up), "pictorial": bool(dwg.is_pictorial((cam, up))),
                "units": "mm", "bbox": [round(x, 3) for x in s.bbox(cam, up)], "visible": rnd(vis), "tangent": rnd(tan)}

class App:
    """Everything the handler needs: the model, the document with undo, and where files go."""
    def __init__(s, model, doc_path, out_dir):
        s.model, s.doc_path, s.out_dir = model, doc_path, out_dir
        s.new()
        if os.path.isfile(doc_path):
            with open(doc_path, encoding="utf-8") as f: s.ed = dm.Editor(dm.Document.from_dict(json.load(f), model.size))
    def new(s): s.ed = dm.Editor(dm.Document(size_of=s.model.size))      # empty drawing; view sizes come from the engine
    def state(s, made=None): return {"doc": s.ed.doc.to_dict(), "can_undo": bool(s.ed.undo_stack), "made": made}
    def meta(s):
        w, h = dm.SIZES[s.ed.doc.size]
        return {"size": {"name": s.ed.doc.size, "w": w, "h": h}, "views": list(dm.STANDARD), "sides": list(dm.SIDES),
                "scales": [{"value": v, "label": dwg.scale_str(v)} for v in dm.SCALES], "source": s.model.source}
    def op(s, op): return s.state(s.ed.do(op))
    def save(s, d=None):
        if d is not None and dm.Document.from_dict(d).to_dict() != s.ed.doc.to_dict(): s.ed.replace(d)   # no undo step for a plain save
        os.makedirs(os.path.dirname(s.doc_path), exist_ok=True)
        with open(s.doc_path, "w", encoding="utf-8") as f: json.dump(s.ed.doc.to_dict(), f, indent=1)
        return s.state()
    def export_pdf(s):
        """Every sheet through the engine: frame, then each placed view at its position and scale."""
        doc, sheets = s.ed.doc, []
        os.makedirs(s.out_dir, exist_ok=True)
        for i, sd in enumerate(doc.sheets):
            sh = dwg.Sheet()
            dwg.frame(sh, dict(title="EDITOR SLICE TEST", pn="SRDP-EDITOR-SLICE", rev="", material="", drawn="",
                               scale=dwg.scale_str(sd.scale), source=s.model.source), i + 1, len(doc.sheets))
            for v in sd.views:
                k = v.scale if v.scale is not None else sd.scale
                ev = dwg.View(None, (v.cam, v.up), k, polys=s.model.polys(v.cam, v.up)).place(v.x, v.y)
                ev.draw(sh, label=v.label, label_scale=(k != sd.scale))
            sheets.append(sh)
        pdf = os.path.join(s.out_dir, "editor_slice.pdf")
        dwg.render(sheets, pdf, None, os.path.join(s.out_dir, "editor_slice"))
        return pdf

def _vec(text):
    v = tuple(float(x) for x in text.split(","))
    if len(v) != 3: raise ValueError("a vector needs three numbers")
    return v

def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(s, *a): pass
        def _send(s, code, body, ctype="application/json"):
            if not isinstance(body, bytes): body = json.dumps(body).encode("utf-8")
            s.send_response(code); s.send_header("Content-Type", ctype); s.send_header("Content-Length", str(len(body)))
            s.send_header("Cache-Control", "no-store"); s.end_headers(); s.wfile.write(body)
        def _body(s):
            n = int(s.headers.get("Content-Length") or 0)
            return json.loads(s.rfile.read(n).decode("utf-8")) if n else None
        def _run(s, fn, ctype="application/json"):
            try:
                with LOCK: out = fn()                                # one engine or document call at a time
            except (KeyError, TypeError, ValueError) as e: return s._send(400, {"error": f"{type(e).__name__}: {e}"})
            s._send(200, out, ctype)
        def do_GET(s):
            u = urlparse(s.path); q = parse_qs(u.query)
            if u.path in STATIC:
                name, ctype = STATIC[u.path]
                with open(os.path.join(HERE, "static", name), "rb") as f: return s._send(200, f.read(), ctype)
            if u.path == "/api/meta": return s._run(app.meta)
            if u.path == "/api/doc": return s._run(app.state)
            if u.path == "/api/view":
                def view():
                    if "name" in q: cam, up = dm.STANDARD[q["name"][0]]
                    else: cam, up = _vec(q["cam"][0]), _vec(q["up"][0]); dm.basis(cam, up)
                    return app.model.view_json(cam, up)
                return s._run(view)
            if u.path == "/api/export.pdf":
                def pdf():
                    with open(app.export_pdf(), "rb") as f: return f.read()
                return s._run(pdf, "application/pdf")
            s._send(404, {"error": "not found"})
        def do_POST(s):
            p = urlparse(s.path).path
            if p == "/api/op": return s._run(lambda: app.op(s._body() or {}))
            if p == "/api/undo": return s._run(lambda: (app.ed.undo(), app.state())[1])
            if p == "/api/doc": return s._run(lambda: app.save(s._body()))
            s._send(404, {"error": "not found"})
    return Handler

class Server(ThreadingHTTPServer):
    allow_reuse_address = False              # on Windows "reuse" lets two servers share a port; fail loudly instead
    daemon_threads = True

def make_server(port=8791, step=None, doc_path=None, out_dir=None):
    """Build the model and return a server ready for serve_forever(). port 0 picks a free port (tests)."""
    if step: model = Model(import_step(step), os.path.basename(step))
    else: model = Model(plate(), "built-in test plate")
    app = App(model, doc_path or os.path.join(LOCAL, "drawing.json"), out_dir or os.path.join(LOCAL, "out"))
    srv = Server(("127.0.0.1", port), make_handler(app)); srv.app = app
    return srv

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Editor slice server")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--step", help="STEP file to draw instead of the built-in test plate")
    ap.add_argument("--doc", help="drawing document (JSON) to load and save")
    ap.add_argument("--out", help="folder for exported PDF / PNG")
    a = ap.parse_args()
    srv = make_server(a.port, a.step, a.doc, a.out)
    print(f"Editor slice on http://127.0.0.1:{srv.server_address[1]}/  (Ctrl+C to stop)", flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
