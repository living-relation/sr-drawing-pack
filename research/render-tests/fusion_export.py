"""Fusion side of the render tests: export the open design's STEP and sr-export's <name>.bom.json (ADR-028, ADR-029).

Run inside local desktop Fusion (ADR-042) through the Fusion MCP `script` call, on a design opened by file id.
Fusion scripts do not see the shell's environment, so the caller puts three lines in front of this file:
    SREXPORT_DIR = r'<sr-export clone>/SRExport'
    OUT = r'<SRDP_ROOT>/research/_local/out/render-tests/<slug>'
    NAME = '<design name>'
Only reads the design: nothing is changed or saved. `fusion_info.json` records isModified before and after; close the
document without saving only when both are false. Big assemblies: run with STEP=True then SIDECAR=True as two calls
(the sidecar took 419 s on 1,117 occurrences, longer than one MCP call waits).
"""
import adsk.core, adsk.fusion, os, sys, time, json

SREXPORT_DIR = globals().get("SREXPORT_DIR", os.environ.get("SREXPORT_DIR", ""))
OUT = globals().get("OUT", "")
NAME = globals().get("NAME", "model")
STEP = globals().get("STEP", True)
SIDECAR = globals().get("SIDECAR", True)


def run(_context: str):
    app = adsk.core.Application.get(); doc = app.activeDocument
    design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    os.makedirs(OUT, exist_ok=True); p = os.path.join(OUT, "fusion_info.json"); step = os.path.join(OUT, NAME + ".step")
    info = json.load(open(p)) if os.path.isfile(p) else {}
    r = design.rootComponent; oc = r.allOccurrences
    comps = [oc.item(i).component for i in range(oc.count)] + [r]           # per occurrence: instance counts
    info.update(modified_before=doc.isModified, occ=oc.count, bodies=sum(c.bRepBodies.count for c in comps),
                meshbodies=sum(c.meshBodies.count for c in comps),
                faces=sum(c.bRepBodies.item(j).faces.count for c in comps for j in range(c.bRepBodies.count)))
    if STEP:
        em = design.exportManager; t = time.perf_counter()
        info["step_ok"] = em.execute(em.createSTEPExportOptions(step, r)); info["step_s"] = round(time.perf_counter() - t, 2)
    if SIDECAR:
        if SREXPORT_DIR not in sys.path: sys.path.insert(0, SREXPORT_DIR)
        import sidecar_ops
        t = time.perf_counter(); sidecar_ops.write_sidecar(design, step, thumbnails=False, assembly_thumb=False)
        info["json_s"] = round(time.perf_counter() - t, 2)
    info["modified_after"] = doc.isModified
    json.dump(info, open(p, "w"), indent=1)
