"""Test assembly SRDP-T-100: every number the model and the drawing use, in one place.

TEST DATA. The SRDP-T-1xx part numbers and the plate / handle materials are made up for this test.
The PDM issues real numbers (ADR-019). All dimensions are millimetres.
"""

# ---- socket head cap screws -------------------------------------------------------------------
# Source: ISO 4762:2004 Table 1 (dk max, k max, s nominal, t min), as stored in the sr-fastener
# catalog (SRFastener/data/catalog.json, family SSH-M, source keys iso4762 and hk_m_shcs).
# build_assembly.py re-checks these against that catalog when SRFASTENER_ROOT is set.
# The solid is the same simple shape sr-fastener builds: head cylinder, shank cylinder at the
# nominal thread diameter, hex socket. No thread form, no chamfers (none are sourced).
SHCS = {
    "M4": dict(d=4.0, pitch=0.7, dk=7.0, k=4.0, s=3.0, t=2.0),
    "M5": dict(d=5.0, pitch=0.8, dk=8.5, k=5.0, s=4.0, t=2.5),
}
# Part number, description and material exactly as sr-fastener's bom_fields() writes them
# (family SSH-M, finish ALLOY-BO). Also re-checked when SRFASTENER_ROOT is set.
SCREW_DESC = {"M4": "Socket Head Screw, M4 x 0.7, Alloy Steel Black Oxide",
              "M5": "Socket Head Screw, M5 x 0.8, Alloy Steel Black Oxide"}
SCREW_MAT = "Alloy Steel Black Oxide"
def screw_pn(size, length): return "SSH-%s-%g x %d ALLOY-BO" % (size, SHCS[size]["pitch"], length)

# ---- holes --------------------------------------------------------------------------------------
# Tap drills: the handbuilt-cad engine's own table (drawing/part.py TAP): 3.3 for M4x0.7, 4.2 for M5x0.8.
# The engine names a thread from the modelled tap-drill diameter, so the model must use these.
TAP_DRILL = {"M4": 3.3, "M5": 4.2}
# Clearance holes: 4.5 for M4, 5.5 for M5. A fastener supplier's chart lists these as the ISO 273
# "normal" fit (see README). ISO 273 itself was not read: TBD against the standard.
CLEARANCE = {"M4": 4.5, "M5": 5.5}
# Counterbore for an M4 socket head: design values for this test. They clear the sourced head
# (dk 7.0, k 4.0) by 0.5 on the radius and 0.6 in depth. Not taken from a counterbore standard: TBD.
CBORE_D, CBORE_DEPTH = 8.0, 4.6
# Blind M4 holes in the base: drill 10 deep, thread 8 deep (design values for this test).
# The thread is not modelled, so its depth lives here and goes to the drawing spec as thread_depth.
BLIND_DRILL_DEPTH, BLIND_THREAD_DEPTH = 10.0, 8.0

# ---- hole positions (x, y) ------------------------------------------------------------------------
M5_XY = [(-45, -25), (-45, 25), (5, -25), (5, 25)]      # cover to base
HANDLE_XY = [(-20, -25), (-20, 25)]                     # handle to cover (inside the sub-assembly)
STOP_XY = [(40, -25), (40, 25)]                         # stop block to base

# ---- plates: x0, x1, y0, y1, z0, z1 -----------------------------------------------------------
BASE = (-60, 60, -40, 40, 0, 12)
COVER = (-55, 15, -35, 35, 12, 20)
HANDLE = (-26, -14, -33, 33, 20, 36)
STOP = (32, 48, -35, 35, 12, 26)

# ---- part table: STEP label (= part number) -> description, material, kind -----------------------
# kind: 'asm' (has children), 'made' (machined here), 'fastener' (bought).
ASM_PN, SUB_PN = "SRDP-T-100", "SRDP-T-110"
BASE_PN, COVER_PN, HANDLE_PN, STOP_PN = "SRDP-T-101", "SRDP-T-111", "SRDP-T-112", "SRDP-T-103"
M5X16, M4X16, M4X12 = screw_pn("M5", 16), screw_pn("M4", 16), screw_pn("M4", 12)
PARTS = {
    ASM_PN: dict(desc="TEST ASSEMBLY", mat="", kind="asm"),
    SUB_PN: dict(desc="COVER SUB-ASSEMBLY", mat="SEE ITEMS 2.1 TO 2.3", kind="asm"),
    BASE_PN: dict(desc="BASE PLATE", mat="6061-T6 AL (TEST)", kind="made"),
    COVER_PN: dict(desc="COVER PLATE", mat="6061-T6 AL (TEST)", kind="made"),
    HANDLE_PN: dict(desc="HANDLE", mat="ACETAL (TEST)", kind="made"),
    STOP_PN: dict(desc="STOP BLOCK", mat="6061-T6 AL (TEST)", kind="made"),
    M5X16: dict(desc=SCREW_DESC["M5"].upper(), mat=SCREW_MAT.upper(), kind="fastener"),
    M4X16: dict(desc=SCREW_DESC["M4"].upper(), mat=SCREW_MAT.upper(), kind="fastener"),
    M4X12: dict(desc=SCREW_DESC["M4"].upper(), mat=SCREW_MAT.upper(), kind="fastener"),
}
# The tree build_assembly.py makes, written out by hand so check_step_tree.py has something
# independent to count against: (label, quantity, children).
EXPECTED_TREE = (ASM_PN, 1, [
    (BASE_PN, 1, []),
    (SUB_PN, 1, [(COVER_PN, 1, []), (HANDLE_PN, 1, []), (M4X12, 2, [])]),
    (STOP_PN, 1, []),
    (M5X16, 4, []),
    (M4X16, 2, []),
])
