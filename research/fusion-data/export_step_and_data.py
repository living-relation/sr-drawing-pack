"""RETIRED (ADR-029): use sr-export's <name>.bom.json instead. Kept as the record of the ADR-028 test.

Fusion side of ADR-028: export a STEP, an f3d and a data file from one design in one go.

Run inside Fusion through its built-in MCP script tool. Set SRDP_FUSION_DATA_OUT to an output folder
(for example research/_local/out/fusion-data in your clone). The script builds its own scratch design
(two plates, tapped and plain holes, part numbers, material, one part used twice), exports, and closes
the design without saving. It touches no existing document.

The data file holds what a STEP cannot carry: the BOM fields and the hole / thread definitions.
"""
import adsk.core, adsk.fusion, time, os, json

OUT = os.environ.get("SRDP_FUSION_DATA_OUT", "")

def comp_row(c):
    b = c.bRepBodies
    mat = b.item(0).material.name if b.count and b.item(0).material else (c.material.name if c.material else "")
    return dict(name=c.name, part_number=c.partNumber, description=c.description, material=mat, id=c.id, bodies=b.count)

def tree(occs, level=0):
    """Indented BOM: one row per component per level, with its quantity at that level."""
    counts = {}
    for i in range(occs.count):
        o = occs.item(i); c = o.component
        e = counts.setdefault(c.id, dict(comp_row(c), qty=0, level=level, children=tree(o.childOccurrences, level + 1)))
        e["qty"] += 1
    return list(counts.values())

def hole_rows(c):
    TT = adsk.fusion.HoleTapTypes
    names = {TT.SimpleHoleTapType: "simple", TT.ClearanceHoleTapType: "clearance", TT.TappedHoleTapType: "tapped", TT.TaperTappedHoleTapType: "taper"}
    rows = []; hf = c.features.holeFeatures
    for i in range(hf.count):
        h = hf.item(i); ext = h.extentDefinition
        r = dict(name=h.name, diameter_mm=round(h.holeDiameter.value * 10, 4), position_mm=[round(v * 10, 4) for v in h.position.asArray()],
                 direction=[round(v, 4) for v in h.direction.asArray()], through=ext.objectType.endswith("AllExtentDefinition"),
                 tap_type=names.get(h.holeTapType, str(h.holeTapType)))
        if hasattr(ext, "distance"): r["depth_mm"] = round(ext.distance.value * 10, 4)
        ti = h.tappedHoleInfo
        if ti:
            r.update(thread=ti.threadDesignation, thread_class=ti.threadClass, thread_type=ti.threadType, pitch_mm=round(ti.threadPitch * 10, 4),
                     major_mm=round(ti.majorDiameter * 10, 4), minor_mm=round(ti.minorDiameter * 10, 4))
            th = h.thread
            if th: r.update(thread_full_length=th.isFullLength, thread_length_mm=round(th.threadLength.value * 10, 4), thread_modeled=th.isModeled)
        rows.append(r)
    return rows

def run(_context: str):
    if not OUT: raise RuntimeError("Set SRDP_FUSION_DATA_OUT to the output folder")
    os.makedirs(OUT, exist_ok=True)
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    root = des.rootComponent
    P = adsk.core.Point3D.create; V = adsk.core.ValueInput.createByReal          # API lengths are centimetres
    lib = app.materialLibraries.itemByName("Fusion Material Library")
    alu = lib.materials.itemByName("Aluminum 6061") if lib else None

    def new_comp(name, pn, desc, tz):
        m = adsk.core.Matrix3D.create(); m.translation = adsk.core.Vector3D.create(0, 0, tz)
        c = root.occurrences.addNewComponent(m).component
        c.name = name; c.partNumber = pn; c.description = desc
        return c

    def plate(c, w, d, t):
        sk = c.sketches.add(c.xYConstructionPlane)
        sk.sketchCurves.sketchLines.addCenterPointRectangle(P(0, 0, 0), P(w / 2, d / 2, 0))
        body = c.features.extrudeFeatures.addSimple(sk.profiles.item(0), V(t), adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
        if alu: body.material = alu
        return max([body.faces.item(i) for i in range(body.faces.count)], key=lambda f: f.boundingBox.maxPoint.z + f.boundingBox.minPoint.z)

    # base plate 120 x 80 x 12: four M5 tapped through holes, two M4 tapped blind holes (thread 8, drill 10)
    base = new_comp("Base Plate", "SRDP-T-201", "BASE PLATE", 0); top = plate(base, 12, 8, 1.2)
    m5 = adsk.fusion.ThreadInfo.create(False, True, "ISO Metric profile", "M5x0.8", "6H", True)
    m4 = adsk.fusion.ThreadInfo.create(False, True, "ISO Metric profile", "M4x0.7", "6H", True)
    holes = base.features.holeFeatures
    for x, y in ((-5, -3), (5, -3), (-5, 3), (5, 3)):
        hi = holes.createSimpleInput(V(0.42)); hi.setPositionByPoint(top, P(x, y, 1.2))
        hi.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection); hi.setToTappedHole(m5); holes.add(hi)
    for x in (-2, 2):
        hi = holes.createSimpleInput(V(0.33)); hi.setPositionByPoint(top, P(x, 0, 1.2))
        hi.setDistanceExtent(V(1.0)); hi.setToTappedHole(m4); hi.setLengthAndOffset(V(0.8), V(0)); holes.add(hi)

    # cover plate 100 x 60 x 8: four plain 5.5 through holes; placed twice to prove quantities
    cover = new_comp("Cover Plate", "SRDP-T-202", "COVER PLATE", 1.2); top2 = plate(cover, 10, 6, 0.8)
    ch = cover.features.holeFeatures
    for x, y in ((-4, -2), (4, -2), (-4, 2), (4, 2)):
        hi = ch.createSimpleInput(V(0.55)); hi.setPositionByPoint(top2, P(x, y, 0.8))
        hi.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection); ch.add(hi)
    m = adsk.core.Matrix3D.create(); m.translation = adsk.core.Vector3D.create(0, 0, 2.0)
    root.occurrences.addExistingComponent(cover, m)

    data = dict(schema="srdp-fusion-data/0", fusion_version=app.version, document=doc.name, units=des.unitsManager.defaultLengthUnits,
                bom=tree(root.occurrences), holes={c.partNumber: hole_rows(c) for c in (base, cover)},
                named_views=[des.namedViews.item(i).name for i in range(des.namedViews.count)])
    em = des.exportManager; t0 = time.time()
    ok_step = em.execute(em.createSTEPExportOptions(os.path.join(OUT, "fusion_test_asm.step"), root)); t1 = time.time()
    ok_f3d = em.execute(em.createFusionArchiveExportOptions(os.path.join(OUT, "fusion_test_asm.f3d"), root)); t2 = time.time()
    json.dump(data, open(os.path.join(OUT, "fusion_test_asm.data.json"), "w"), indent=1)
    print("step", ok_step, round(t1 - t0, 2), "s  f3d", ok_f3d, round(t2 - t1, 2), "s")
    doc.close(False)
