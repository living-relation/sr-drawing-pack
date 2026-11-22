"""Editor slice tests: the document rules, then the HTTP endpoints against a server started here.

Usage:  python -m unittest -v test_slice      (from this folder)
The rule tests need nothing. The server tests need HBCAD_ROOT and the handbuilt-cad Python; they are skipped without it.
"""
import json, os, re, sys, tempfile, threading, unittest, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docmodel as dm

def xy(doc, vid): v = doc.find(vid)[1]; return (v.x, v.y)

class Rules(unittest.TestCase):
    def setUp(s):
        s.d = dm.Document(); s.front = s.d.place(0, "front", 100, 100).id
        s.top = s.d.project(s.front, "top").id; s.right = s.d.project(s.front, "right").id

    def test_third_angle_from_front(s):
        for side, name in (("right", "right"), ("left", "left"), ("top", "top"), ("bottom", "bottom")):
            cam, up = dm.child_camera(*dm.STANDARD["front"], side)
            s.assertEqual(dm.standard_name(cam, up), name)
            s.assertEqual((cam, up), tuple(tuple(float(x) for x in v) for v in dm.STANDARD[name]))

    def test_third_angle_from_any_parent(s):
        cam, up = dm.child_camera(*dm.STANDARD["right"], "right"); s.assertEqual(dm.standard_name(cam, up), "back")
        cam, up = dm.child_camera(*dm.STANDARD["top"], "bottom"); s.assertEqual(dm.standard_name(cam, up), "front")
        cam, up = dm.child_camera(*dm.STANDARD["top"], "right")            # the right side, seen with the top view's up
        s.assertEqual(cam, (1.0, 0.0, 0.0)); s.assertIsNone(dm.standard_name(cam, up))
        for name in dm.STANDARD:                                           # there and back gives the parent again
            for side, back in (("left", "right"), ("right", "left"), ("top", "bottom"), ("bottom", "top")):
                c, u = dm.child_camera(*dm.child_camera(*dm.STANDARD[name], side), back)
                c0, _, u0 = dm.basis(*dm.STANDARD[name])
                for a, b in zip(c + u, c0 + u0): s.assertAlmostEqual(a, b, places=6)

    def test_projected_names_and_start(s):
        d = s.d
        s.assertEqual([d.find(i)[1].name for i in (s.top, s.right)], ["top", "right"])
        s.assertEqual((xy(d, s.top), xy(d, s.right)), ((100, 160), (160, 100)))
        s.assertTrue(d.find(s.top)[1].linked); s.assertEqual(d.find(s.top)[1].parent, s.front)

    def test_link_rules(s):
        d = s.d
        d.drag(s.front, 10, 5); s.assertEqual((xy(d, s.top), xy(d, s.right)), ((110, 165), (170, 105)))   # children follow
        d.drag(s.right, 7, 9); s.assertEqual(xy(d, s.right), (177, 105))                                   # left/right only
        d.drag(s.top, 7, 9); s.assertEqual(xy(d, s.top), (110, 174))                                       # up/down only
        d.break_link(s.right); d.drag(s.right, 1, 1); s.assertEqual(xy(d, s.right), (178, 106))            # freed child
        d.drag(s.front, -10, 0); s.assertEqual((xy(d, s.right)[0], xy(d, s.top)[0]), (178, 100))           # freed child stays
        sub = d.project(s.right, "bottom").id; d.drag(s.right, 0, 4)                                       # freed child projects
        s.assertEqual(xy(d, sub), (178, 110 - 60))

    def test_grandchildren_follow(s):
        d = s.d; g = d.project(s.right, "right").id
        d.drag(s.front, 5, 5); s.assertEqual(xy(d, g), (225, 105))
        d.drag(s.right, 3, 9); s.assertEqual((xy(d, s.right), xy(d, g)), ((168, 105), (228, 105)))

    def test_delete_frees_children(s):
        d = s.d; d.delete(s.front); t = d.find(s.top)[1]
        s.assertEqual((t.parent, t.side, t.linked), (None, None, False))
        d.drag(s.top, 3, 4); s.assertEqual(xy(d, s.top), (103, 164))
        s.assertRaises(ValueError, d.find, s.front)

    def test_sheets_and_scale(s):
        d = s.d; d.add_sheet(); d.add_sheet()
        s.assertEqual([sh.kind for sh in d.sheets], ["first", "continuation", "continuation"])
        d.remove_sheet(1); s.assertEqual(len(d.sheets), 2)
        s.assertRaises(ValueError, d.remove_sheet, 0); s.assertRaises(ValueError, d.remove_sheet, 5)
        d.set_scale(0, 2); s.assertEqual((d.sheets[0].scale, d.view_scale(s.front)), (2, 2))
        s.assertRaises(ValueError, d.set_scale, 0, 1.7)
        s.assertRaises(ValueError, d.place, 0, "sideways", 0, 0)

    def test_spacing_from_view_sizes(s):
        size = lambda cam, up: (80, 10) if abs(cam[1]) == 1 else ((50, 10) if abs(cam[0]) == 1 else (80, 50))   # the test plate
        d = dm.Document(size_of=size); f = d.place(0, "front", 100, 100).id
        r = d.project(f, "right").id; t = d.project(f, "top").id; b = d.project(r, "right").id            # b is the back view
        s.assertEqual((xy(d, r), xy(d, t), xy(d, b)), ((100 + 65 + dm.GAP, 100), (100, 100 + 30 + dm.GAP), (190 + 65 + dm.GAP, 100)))
        d.set_scale(0, 2)                                                                                 # same gaps at 2:1
        s.assertEqual((xy(d, f), xy(d, r), xy(d, t), xy(d, b)), ((100, 100), (255, 100), (100, 185), (410, 100)))
        d.break_link(t); d.set_scale(0, 1); s.assertEqual((xy(d, r), xy(d, t), xy(d, b)), ((190, 100), (100, 185), (280, 100)))

    def test_json_round_trip(s):
        d = s.d; d.add_sheet(); d.place(1, "trimetric", 200, 150); d.break_link(s.right)
        text = json.dumps(d.to_dict()); back = dm.Document.from_dict(json.loads(text))
        s.assertEqual(back.to_dict(), d.to_dict())
        s.assertEqual(back.place(0, "back", 0, 0).id, d.next_id)             # ids keep counting after a load
        bad = json.loads(text); bad["sheets"][0]["views"][1]["parent"] = 99
        s.assertRaises(ValueError, dm.Document.from_dict, bad)

    def test_undo(s):
        ed = dm.Editor(s.d); before = ed.doc.to_dict()
        ed.do({"op": "drag", "id": s.front, "dx": 10, "dy": 0}); ed.do({"op": "add_sheet"})
        s.assertRaises(ValueError, ed.do, {"op": "remove_sheet", "sheet": 0})   # a refused command leaves no undo step
        s.assertRaises(ValueError, ed.do, {"op": "drag", "id": 99, "dx": 1, "dy": 1})
        s.assertEqual(len(ed.undo_stack), 2)
        s.assertTrue(ed.undo()); s.assertTrue(ed.undo()); s.assertEqual(ed.doc.to_dict(), before); s.assertFalse(ed.undo())

@unittest.skipUnless(os.environ.get("HBCAD_ROOT"), "HBCAD_ROOT not set: server tests need the handbuilt-cad engine")
class Server(unittest.TestCase):
    @classmethod
    def setUpClass(c):
        import server
        c.server = server; c.tmp = tempfile.TemporaryDirectory()
        c.doc_path = os.path.join(c.tmp.name, "drawing.json"); c.out = os.path.join(c.tmp.name, "out")
        c.srv = server.make_server(0, None, c.doc_path, c.out)
        c.base = f"http://127.0.0.1:{c.srv.server_address[1]}"
        threading.Thread(target=c.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(c): c.srv.shutdown(); c.srv.server_close(); c.tmp.cleanup()
    def setUp(s): s.srv.app.new()                                            # every test starts with an empty drawing

    def get(s, path):
        with urllib.request.urlopen(s.base + path) as r: return r.status, r.headers.get("Content-Type"), r.read()
    def get_json(s, path): return json.loads(s.get(path)[2])
    def post(s, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(s.base + path, data=data or b"", method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r: return json.loads(r.read())
    def op(s, **kw): return s.post("/api/op", kw)

    def test_page(s):
        code, ctype, body = s.get("/"); s.assertEqual(code, 200); s.assertIn("text/html", ctype); s.assertIn(b"editor.js", body)
        s.assertIn("javascript", s.get("/editor.js")[1])
        with s.assertRaises(urllib.error.HTTPError) as e: s.get("/server.py")
        s.assertEqual(e.exception.code, 404)

    def test_tables_match_the_engine(s):
        dwg = s.server.dwg
        s.assertEqual(dm.SCALES, dwg.STD_SCALES); s.assertEqual(dm.SIZES["B"], (dwg.PW, dwg.PH))
        for name, cu in dm.STANDARD.items(): s.assertEqual(cu, dwg.VIEWDIR["iso" if name == "trimetric" else name])
        m = s.get_json("/api/meta"); s.assertEqual(m["views"], list(dm.STANDARD)); s.assertEqual(m["size"]["w"], 431.8)

    def test_views_visible_only(s):
        want = {"front": (4, 80, 10), "top": (8, 80, 50), "right": (4, 50, 10), "left": (4, 50, 10), "back": (4, 80, 10), "bottom": (12, 80, 50)}
        for name, (n, w, h) in want.items():                                 # plate: holes and pocket hidden from the sides
            v = s.get_json(f"/api/view?name={name}"); b = v["bbox"]
            s.assertEqual(len(v["visible"]), n, name); s.assertEqual(v["tangent"], [], name); s.assertFalse(v["pictorial"])
            s.assertAlmostEqual(b[2] - b[0], w, places=2); s.assertAlmostEqual(b[3] - b[1], h, places=2)
            s.assertNotIn("hidden", v)
        raw_vis, raw_hid = s.srv.app.model.shape.project_to_viewport((0, -5000, 0), (0, 0, 1), (0, 0, 0))
        s.assertEqual((len(raw_vis), len(raw_hid)), (4, 36))                 # the hidden lines exist; the endpoint leaves them out
        t = s.get_json("/api/view?name=trimetric")
        s.assertTrue(t["pictorial"]); s.assertEqual(t["name"], "trimetric"); s.assertGreater(len(t["visible"]), 10)
        by_cam = s.get_json("/api/view?cam=1,0,0&up=0,1,0"); s.assertIsNone(by_cam["name"]); s.assertEqual(len(by_cam["visible"]), 4)
        for bad in ("/api/view?name=sideways", "/api/view?cam=0,0,1&up=0,0,1", "/api/view"):
            with s.assertRaises(urllib.error.HTTPError) as e: s.get(bad)
            s.assertEqual(e.exception.code, 400)

    def test_ops_and_projection_spacing(s):
        f = s.op(op="place", sheet=0, name="front", x=120, y=120)["made"]
        r = s.op(op="project", id=f, side="right"); t = s.op(op="project", id=f, side="top")
        views = {v["id"]: v for v in t["doc"]["sheets"][0]["views"]}
        s.assertEqual((views[r["made"]]["name"], views[t["made"]]["name"]), ("right", "top"))
        s.assertAlmostEqual(views[r["made"]]["x"], 120 + (80 + 50) / 2 + dm.GAP)   # clear of the parent by GAP
        s.assertAlmostEqual(views[t["made"]]["y"], 120 + (10 + 50) / 2 + dm.GAP)
        z = {v["id"]: v for v in s.op(op="set_scale", sheet=0, scale=2)["doc"]["sheets"][0]["views"]}
        s.assertAlmostEqual(z[r["made"]]["x"], 120 + (80 + 50) + dm.GAP)           # bigger views, same gap
        s.assertAlmostEqual(z[t["made"]]["y"], 120 + (10 + 50) + dm.GAP); s.post("/api/undo")
        s.assertEqual(views[r["made"]]["y"], 120)
        d = s.op(op="drag", id=r["made"], dx=5, dy=50)["doc"]["sheets"][0]["views"][1]; s.assertEqual(d["y"], 120)
        with s.assertRaises(urllib.error.HTTPError) as e: s.op(op="remove_sheet", sheet=0)
        s.assertEqual(e.exception.code, 400)
        u = s.post("/api/undo"); s.assertAlmostEqual(u["doc"]["sheets"][0]["views"][1]["x"], views[r["made"]]["x"])

    def test_save_load_round_trip(s):
        f = s.op(op="place", sheet=0, name="front", x=100, y=150)["made"]; s.op(op="project", id=f, side="top")
        s.op(op="add_sheet"); s.op(op="place", sheet=1, name="trimetric", x=200, y=150); s.op(op="set_scale", sheet=1, scale=2)
        doc = s.get_json("/api/doc")["doc"]
        s.assertEqual(s.post("/api/doc", doc)["doc"], doc)
        with open(s.doc_path, encoding="utf-8") as fh: s.assertEqual(json.load(fh), doc)
        again = s.server.App(s.srv.app.model, s.doc_path, s.out)             # a new start reads the saved file
        s.assertEqual(again.ed.doc.to_dict(), doc)
        doc["sheets"][0]["views"][0]["x"] = 111.5                            # an edited document can be pushed back
        s.assertEqual(s.post("/api/doc", doc)["doc"]["sheets"][0]["views"][0]["x"], 111.5)
        with s.assertRaises(urllib.error.HTTPError) as e: s.post("/api/doc", {"sheets": []})
        s.assertEqual(e.exception.code, 400)

    def test_pdf_one_page_per_sheet(s):
        f = s.op(op="place", sheet=0, name="front", x=110, y=150)["made"]
        s.op(op="project", id=f, side="top"); s.op(op="project", id=f, side="right")
        s.op(op="place", sheet=0, name="trimetric", x=290, y=205)
        s.op(op="add_sheet"); s.op(op="place", sheet=1, name="bottom", x=200, y=150); s.op(op="add_sheet")
        code, ctype, body = s.get("/api/export.pdf")
        s.assertEqual((code, ctype), (200, "application/pdf")); s.assertTrue(body.startswith(b"%PDF")); s.assertGreater(len(body), 5000)
        s.assertEqual(len(re.findall(rb"/Type\s*/Page\b(?!s)", body)), 3)
        for i in (1, 2, 3): s.assertGreater(os.path.getsize(os.path.join(s.out, f"editor_slice_sh{i}.png")), 1000)

if __name__ == "__main__": unittest.main(verbosity=2)
