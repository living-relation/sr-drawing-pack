"""Editor slice, document rules: sheets, placed views and the projected-view link rules from docs/SPEC.md.

Plain Python, no CAD library. The server and the tests both use this module, so the rules live in one place.
Extends the View / Drawing classes of research/spike-b/editor_model.py (copied, not imported):
views get an id, a camera and a scale, and the whole drawing turns into JSON and back.
Page units are millimetres, origin at the bottom left of the sheet, y up (the engine's convention).
"""
import math

SIZES = {"B": (431.8, 279.4)}                       # 11x17 landscape, the only size in the slice
SCALES = [10, 8, 5, 4, 3, 2, 1.5, 1, 2 / 3, 0.5, 0.4, 1 / 3, 0.25, 0.2, 0.1]     # same list as the engine's STD_SCALES
SIDES = ("left", "right", "top", "bottom")
GAP = 25.0                                          # clear space between a parent and a new projected view, page mm
# camera direction (from the model toward the eye) and up vector; the same table as the engine's VIEWDIR.
# "trimetric" is the engine's "iso" camera.
STANDARD = {"front": ((0, -1, 0), (0, 0, 1)), "top": ((0, 0, 1), (0, 1, 0)), "right": ((1, 0, 0), (0, 0, 1)),
            "left": ((-1, 0, 0), (0, 0, 1)), "back": ((0, 1, 0), (0, 0, 1)), "bottom": ((0, 0, -1), (0, -1, 0)),
            "trimetric": ((1, -1.55, 1.15), (0, 0, 1))}

def _unit(a):
    n = math.sqrt(sum(x * x for x in a))
    if n < 1e-12: raise ValueError("zero-length vector")
    return tuple(x / n for x in a)
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _neg(a): return tuple(-x for x in a)
def _clean(a): return tuple(round(x, 9) + 0.0 for x in a)      # + 0.0 turns -0.0 into 0.0

def basis(cam, up):
    """(c, r, u): toward the eye, right on the page, up on the page. Same maths as the engine's basis()."""
    c = _unit(cam); f = _neg(c); r = _unit(_cross(f, up)); u = _cross(r, f)
    return c, r, u

def child_camera(cam, up, side):
    """Third-angle projection: the view placed on `side` of a parent looks at the model FROM that side.
    Right of front is the right view, above front is the top view. Works for any parent orientation."""
    c, r, u = basis(cam, up)
    cam2, up2 = {"right": (r, u), "left": (_neg(r), u), "top": (u, _neg(c)), "bottom": (_neg(u), c)}[side]
    return _clean(cam2), _clean(up2)

def standard_name(cam, up):
    """Name of the standard view with this camera, or None."""
    c, _, u = basis(cam, up)
    for name, (cam2, up2) in STANDARD.items():
        c2, _, u2 = basis(cam2, up2)
        if max(abs(a - b) for a, b in zip(c + u, c2 + u2)) < 1e-6: return name
    return None

def check_scale(scale):
    for s in SCALES:
        if abs(s - float(scale)) < 1e-6: return s
    raise ValueError(f"not a standard scale: {scale}")

class View:
    """A placed view. A projected view is a child: it follows its parent and slides on one axis only."""
    FIELDS = ("id", "name", "cam", "up", "x", "y", "scale", "parent", "side", "linked")
    def __init__(s, id, name, cam, up, x, y, scale=None, parent=None, side=None, linked=False):
        s.id, s.name, s.cam, s.up = int(id), str(name), _clean(map(float, cam)), _clean(map(float, up))
        s.x, s.y = round(float(x), 3), round(float(y), 3)
        s.scale = None if scale is None else check_scale(scale)       # None = use the sheet scale
        s.parent, s.side, s.linked = parent, side, bool(linked)
        basis(s.cam, s.up)                                            # refuses a camera that cannot be used
        if side is not None and side not in SIDES: raise ValueError(f"bad side: {side}")
    @property
    def label(s): return "TRIMETRIC VIEW" if s.name == "trimetric" else s.name.upper()
    def to_dict(s):
        d = {k: getattr(s, k) for k in s.FIELDS}; d["cam"], d["up"], d["label"] = list(s.cam), list(s.up), s.label
        return d

class Sheet:
    def __init__(s, kind, scale=1, views=()): s.kind, s.scale, s.views = kind, check_scale(scale), list(views)
    def to_dict(s): return {"kind": s.kind, "scale": s.scale, "views": [v.to_dict() for v in s.views]}

class Document:
    """Sheets share one size. Exactly one sheet (sheet 1) carries the full title block; it cannot be removed.
    size_of, when given, is a function (cam, up) -> (width, height) of that view in model mm. The server passes
    one that asks the CAD engine; with it, new projected views are spaced by their real size and a scale change
    keeps the gaps between linked views. Without it the rules still work, with a fixed 60 mm spacing."""
    def __init__(s, size="B", size_of=None):
        if size not in SIZES: raise ValueError(f"unknown sheet size: {size}")
        s.size, s.sheets, s.next_id, s.size_of = size, [Sheet("first")], 1, size_of

    # ---- JSON ----
    def to_dict(s): return {"size": s.size, "next_id": s.next_id, "sheets": [sh.to_dict() for sh in s.sheets]}
    @classmethod
    def from_dict(cls, d, size_of=None):
        doc = cls(d.get("size", "B"), size_of); doc.sheets = []
        for i, sd in enumerate(d["sheets"]):
            kind = "first" if i == 0 else "continuation"              # the position decides, never the file
            doc.sheets.append(Sheet(kind, sd.get("scale", 1), [View(**{k: vd.get(k) for k in View.FIELDS}) for vd in sd.get("views", [])]))
        if not doc.sheets: raise ValueError("a drawing needs at least one sheet")
        ids = [v.id for sh in doc.sheets for v in sh.views]
        if len(ids) != len(set(ids)): raise ValueError("two views share an id")
        for sh in doc.sheets:
            here = {v.id for v in sh.views}
            for v in sh.views:
                if v.parent is not None and (v.parent not in here or v.parent == v.id or v.side not in SIDES):
                    raise ValueError(f"view {v.id}: bad parent or side")
                if v.parent is None: v.side, v.linked = None, False
        doc.next_id = max([int(d.get("next_id", 1))] + [i + 1 for i in ids])
        return doc

    # ---- look-ups ----
    def sheet(s, i):
        if not isinstance(i, int) or not 0 <= i < len(s.sheets): raise ValueError(f"no sheet {i}")
        return s.sheets[i]
    def find(s, vid):
        for sh in s.sheets:
            for v in sh.views:
                if v.id == vid: return sh, v
        raise ValueError(f"no view {vid}")
    def children(s, vid):
        sh, _ = s.find(vid); return [v for v in sh.views if v.parent == vid]
    def view_scale(s, vid):
        sh, v = s.find(vid); return v.scale if v.scale is not None else sh.scale

    # ---- view rules ----
    def place(s, sheet, name, x, y):
        """Drop a standard view on a sheet. It takes the sheet scale."""
        if name not in STANDARD: raise ValueError(f"unknown view: {name}")
        cam, up = STANDARD[name]; v = View(s.next_id, name, cam, up, x, y); s.next_id += 1
        s.sheet(sheet).views.append(v); return v
    def _reach(s, p, cam, up, side):
        """Half the parent plus half the child along the projection axis, in model mm."""
        i = 0 if side in ("left", "right") else 1
        return (s.size_of(p.cam, p.up)[i] + s.size_of(cam, up)[i]) / 2
    def project(s, vid, side, distance=None):
        """Make a projected child on `side` of view vid, `distance` mm from its centre
        (default: clear of the parent by GAP when the view sizes are known, else 60 mm)."""
        if side not in SIDES: raise ValueError(f"bad side: {side}")
        sh, p = s.find(vid); cam, up = child_camera(p.cam, p.up, side)
        if distance is None: distance = s._reach(p, cam, up, side) * s.view_scale(vid) + GAP if s.size_of else 60.0
        dx, dy = {"left": (-distance, 0), "right": (distance, 0), "top": (0, distance), "bottom": (0, -distance)}[side]
        v = View(s.next_id, standard_name(cam, up) or f"{p.name}/{side}", cam, up, p.x + dx, p.y + dy, p.scale, p.id, side, True)
        s.next_id += 1; sh.views.append(v); return v
    def drag(s, vid, dx, dy):
        """Move a view. A linked child only slides toward or away from its parent. Linked children follow."""
        _, v = s.find(vid); dx, dy = float(dx), float(dy)
        if v.linked:
            if v.side in ("left", "right"): dy = 0.0
            else: dx = 0.0
        s._move(v, dx, dy); return v
    def _move(s, v, dx, dy):
        v.x, v.y = round(v.x + dx, 3), round(v.y + dy, 3)
        for c in s.children(v.id):
            if c.linked: s._move(c, dx, dy)
    def break_link(s, vid):
        _, v = s.find(vid); v.linked = False; return v
    def delete(s, vid):
        """Remove a view. Its children stay on the sheet as free views."""
        sh, v = s.find(vid)
        for c in s.children(vid): c.parent, c.side, c.linked = None, None, False
        sh.views.remove(v)

    # ---- sheet rules ----
    def set_scale(s, sheet, scale):
        """Change a sheet's scale. Views resize about their centres. When the view sizes are known, each linked
        child is pushed out or pulled in so the gap to its parent stays the same."""
        sh = s.sheet(sheet); old, new = sh.scale, check_scale(scale); sh.scale = new
        if not s.size_of or old == new: return
        def respace(p):                                  # parents first, so a grandchild moves with its parent, then adjusts
            for c in s.children(p.id):
                if c.linked and c.scale is None and p.scale is None:
                    d = s._reach(p, c.cam, c.up, c.side) * (new - old)
                    dx, dy = {"left": (-d, 0), "right": (d, 0), "top": (0, d), "bottom": (0, -d)}[c.side]
                    s._move(c, dx, dy)
                respace(c)
        for v in [v for v in sh.views if v.parent is None]: respace(v)
    def add_sheet(s): s.sheets.append(Sheet("continuation", s.sheets[0].scale)); return len(s.sheets) - 1
    def remove_sheet(s, i):
        if s.sheet(i).kind == "first": raise ValueError("the sheet with the full title block cannot be removed")
        s.sheets.pop(i)

    # ---- one entry point for the page ----
    def apply(s, op):
        """Run one command given as a dict, for example {"op": "drag", "id": 3, "dx": 5, "dy": 0}.
        Returns the id of a view it made, the index of a sheet it added, or None."""
        k = op.get("op")
        if k == "place": return s.place(op["sheet"], op["name"], op["x"], op["y"]).id
        if k == "project": return s.project(op["id"], op["side"], op.get("distance")).id
        if k == "drag": s.drag(op["id"], op["dx"], op["dy"]); return None
        if k == "break_link": s.break_link(op["id"]); return None
        if k == "delete": s.delete(op["id"]); return None
        if k == "set_scale": s.set_scale(op["sheet"], op["scale"]); return None
        if k == "add_sheet": return s.add_sheet()
        if k == "remove_sheet": s.remove_sheet(op["sheet"]); return None
        raise ValueError(f"unknown op: {k}")

class Editor:
    """A document plus undo. Every command that works leaves one snapshot behind; a failed one leaves nothing."""
    def __init__(s, doc=None, depth=50): s.doc, s.undo_stack, s.depth = doc or Document(), [], depth
    def do(s, op):
        before = s.doc.to_dict()
        try: made = s.doc.apply(op)
        except (KeyError, TypeError, ValueError) as e:
            s.doc = Document.from_dict(before, s.doc.size_of); raise ValueError(f"{type(e).__name__}: {e}")
        s._push(before); return made
    def replace(s, d):
        new = Document.from_dict(d, s.doc.size_of); s._push(s.doc.to_dict()); s.doc = new
    def undo(s):
        if not s.undo_stack: return False
        s.doc = Document.from_dict(s.undo_stack.pop(), s.doc.size_of); return True
    def _push(s, snap): s.undo_stack.append(snap); del s.undo_stack[:-s.depth]
