"""Spike B, editor data model: the view, sheet and BOM rules from docs/SPEC.md as plain Python.

Usage:  python editor_model.py     (prints OK when every rule below holds)
No Fusion, no CAD library. This sizes the rule logic only; it draws nothing.
"""

class View:
    """A placed view. A projected view is a child: it follows its parent and slides on one axis only."""
    def __init__(s, name, x, y, parent=None, side=None):
        s.name, s.x, s.y, s.parent, s.side, s.children = name, x, y, parent, side, []
        s.linked = parent is not None
        if parent: parent.children.append(s)
    def project(s, side, gap=60):
        dx, dy = {"left": (-gap, 0), "right": (gap, 0), "top": (0, gap), "bottom": (0, -gap)}[side]
        return View(f"{s.name}/{side}", s.x + dx, s.y + dy, s, side)
    def drag(s, dx, dy):
        if s.linked:                                   # a linked child only slides toward or away from its parent
            if s.side in ("left", "right"): dy = 0
            else: dx = 0
        s._move(dx, dy)
    def _move(s, dx, dy):
        s.x += dx; s.y += dy
        for c in s.children:
            if c.linked: c._move(dx, dy)
    def break_link(s): s.linked = False

class Drawing:
    """Sheets share one size. Exactly one sheet carries the full title block and revision table."""
    def __init__(s, size="B"): s.size = size; s.sheets = ["first"]
    def add_sheet(s): s.sheets.append("continuation")
    def remove_sheet(s, i):
        if s.sheets[i] == "first": raise ValueError("the sheet with the full title block cannot be removed")
        s.sheets.pop(i)
    def set_size(s, size): s.size = size               # one field, so every sheet changes together

class Bom:
    """Parent BOM: rows come from the model and are never edited by visibility."""
    def __init__(s, rows): s.rows = dict(rows)         # item -> qty, straight from the model
    def copy(s): return BomCopy(s)

class BomCopy:
    """Linked copy: read-only, except rows can be left out. Quantities always come from the parent."""
    def __init__(s, parent): s.parent = parent; s.left_out = set()
    def leave_out(s, item):
        if item not in s.parent.rows: raise KeyError(item)
        s.left_out.add(item)
    @property
    def rows(s): return {k: q for k, q in s.parent.rows.items() if k not in s.left_out}
    def set_qty(s, item, qty): raise PermissionError("a BOM copy is read-only")

def check():
    front = View("front", 100, 100); top = front.project("top"); right = front.project("right")
    front.drag(10, 5);  assert (top.x, top.y) == (110, 165) and (right.x, right.y) == (170, 105)   # children follow
    right.drag(7, 9);   assert (right.x, right.y) == (177, 105)                                    # left/right only
    top.drag(7, 9);     assert (top.x, top.y) == (110, 174)                                        # up/down only
    right.break_link(); right.drag(1, 1); assert (right.x, right.y) == (178, 106)                  # freed child
    front.drag(-10, 0); assert right.x == 178 and top.x == 100                                     # freed child stays
    sub = right.project("bottom"); right.drag(0, 4); assert sub.y == right.y - 60                  # freed child projects

    d = Drawing(); d.add_sheet(); d.add_sheet(); assert d.sheets == ["first", "continuation", "continuation"]
    d.remove_sheet(1); d.set_size("D"); assert d.sheets.count("first") == 1 and d.size == "D"
    try: d.remove_sheet(0); raise AssertionError
    except ValueError: pass

    bom = Bom({"plate": 1, "screw": 4, "bracket": 2}); c = bom.copy(); c.leave_out("screw")
    assert c.rows == {"plate": 1, "bracket": 2} and bom.rows["screw"] == 4                         # parent untouched
    bom.rows["bracket"] = 3; assert c.rows["bracket"] == 3                                         # copy stays linked
    try: c.set_qty("plate", 9); raise AssertionError
    except PermissionError: pass
    print("OK")

if __name__ == "__main__": check()
