"""Build the test assembly SRDP-T-100 with build123d and export one assembly STEP.

Usage:  python build_assembly.py <out_dir>
Needs:  a Python with build123d (the handbuilt-cad clone's Python has it).
Optional: SRFASTENER_ROOT = path to an sr-fastener clone. When set, the screw sizes, part numbers
        and descriptions in model_data.py are checked against its catalog before anything is built.
sr-cadlib is not used: it is a helper for scripts that run inside Fusion (it needs the adsk
modules), so it cannot build a model outside Fusion. The parts here are plain build123d solids.
Holes for threads are modelled at tap-drill diameter. No thread form is modelled.
"""
import copy, json, os, sys
from build123d import Box, Compound, Cylinder, Location, Pos, RegularPolygon, extrude, export_step
import model_data as D


def check_against_sr_fastener(root):
    sys.path.insert(0, os.path.join(root, "SRFastener"))
    import fastener_core as fc
    cat = fc.load_catalog(); fam = fc.family(cat, "SSH-M"); n = 0
    for size, v in D.SHCS.items():
        row = fc.size_row(fam, size)
        got = dict(d=row["d"], pitch=row["pitch"], **row["dims"])
        assert got == v, f"{size}: model_data {v} != sr-fastener catalog {got}"
        n += 1
    for size, length in (("M5", 16), ("M4", 16), ("M4", 12)):
        row = fc.size_row(fam, size); b = fc.bom_fields(cat, fam, row, length, "ALLOY-BO")
        assert length in row["lengths"], f"{size} x {length} is not a listed length"
        assert b["part_number"] == D.screw_pn(size, length) and b["description"] == D.SCREW_DESC[size] and b["material"] == D.SCREW_MAT, b
        n += 1
    return n


def plate(b):
    x0, x1, y0, y1, z0, z1 = b
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)

def bore(x, y, dia, z0, z1):
    """Cutter for a hole of diameter dia from z0 to z1. Ends that leave the part run 1 mm past it."""
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(dia / 2, z1 - z0)

def base():
    p = plate(D.BASE); z0, z1 = D.BASE[4:]
    for x, y in D.M5_XY: p -= bore(x, y, D.TAP_DRILL["M5"], z0 - 1, z1 + 1)              # M5 tapped, through
    for x, y in D.STOP_XY: p -= bore(x, y, D.TAP_DRILL["M4"], z1 - D.BLIND_DRILL_DEPTH, z1 + 1)  # M4 tapped, blind, flat bottom
    return p

def cover():
    p = plate(D.COVER); z0, z1 = D.COVER[4:]
    for x, y in D.M5_XY: p -= bore(x, y, D.CLEARANCE["M5"], z0 - 1, z1 + 1)
    for x, y in D.HANDLE_XY:
        p -= bore(x, y, D.CLEARANCE["M4"], z0 - 1, z1 + 1)
        p -= bore(x, y, D.CBORE_D, z0 - 1, z0 + D.CBORE_DEPTH)                            # counterbore from the underside
    return p

def handle():
    p = plate(D.HANDLE); z0, z1 = D.HANDLE[4:]
    for x, y in D.HANDLE_XY: p -= bore(x, y, D.TAP_DRILL["M4"], z0 - 1, z1 + 1)          # M4 tapped, through
    return p

def stop():
    p = plate(D.STOP); z0, z1 = D.STOP[4:]
    for x, y in D.STOP_XY:
        p -= bore(x, y, D.CLEARANCE["M4"], z0 - 1, z1 + 1)
        p -= bore(x, y, D.CBORE_D, z1 - D.CBORE_DEPTH, z1 + 1)                            # counterbore from the top
    return p

def shcs(size, length):
    """Socket head cap screw, seat plane at z=0, head up (+z), shank down. Same shape as sr-fastener's."""
    v = D.SHCS[size]
    s = Pos(0, 0, v["k"] / 2) * Cylinder(v["dk"] / 2, v["k"]) + Pos(0, 0, -length / 2) * Cylinder(v["d"] / 2, length)
    hexr = v["s"] / 2 / 0.8660254037844386                                               # across flats -> circumradius
    return s - Pos(0, 0, v["k"] - v["t"]) * extrude(RegularPolygon(hexr, 6), v["t"] + 1)

def instance(proto, label, loc):
    c = copy.copy(proto); c.label = label; c.location = loc
    return c

def build():
    """Returns the top Compound. One solid per part; repeated screws share one shape and differ by location."""
    def part(shape, pn):
        s = shape.solid() if hasattr(shape, "solid") else shape
        s.label = pn
        return s
    b, c, h, st = part(base(), D.BASE_PN), part(cover(), D.COVER_PN), part(handle(), D.HANDLE_PN), part(stop(), D.STOP_PN)
    m5, m4a, m4b = part(shcs("M5", 16), D.M5X16), part(shcs("M4", 16), D.M4X16), part(shcs("M4", 12), D.M4X12)
    zc = D.COVER[4] + D.CBORE_DEPTH                     # seat of the handle screws: counterbore floor, head points down
    sub = Compound(label=D.SUB_PN, children=[c, h] + [instance(m4b, D.M4X12, Location((x, y, zc), (180, 0, 0))) for x, y in D.HANDLE_XY])
    zs = D.STOP[5] - D.CBORE_DEPTH                      # seat of the stop block screws: counterbore floor
    return Compound(label=D.ASM_PN, children=[b, sub, st]
                    + [instance(m5, D.M5X16, Location((x, y, D.COVER[5]))) for x, y in D.M5_XY]
                    + [instance(m4a, D.M4X16, Location((x, y, zs))) for x, y in D.STOP_XY])


if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    root = os.environ.get("SRFASTENER_ROOT")
    checked = check_against_sr_fastener(root) if root else None
    asm = build(); bb = asm.bounding_box()
    step = os.path.join(out, D.ASM_PN + ".step")
    export_step(asm, step)
    print(json.dumps(dict(step=os.path.basename(step), solids=len(asm.solids()),
                          size=[round(v, 3) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
                          sr_fastener_rows_checked=checked if root else "skipped (SRFASTENER_ROOT not set)"), indent=1))
