"""Write the speed-check assembly to a temporary STEP file.

The file is for timing only. It is not a design to commit. The public repo
does not keep STEP files.
"""
def write_benchmark(path, blocks=320, fasteners=100):
    """Build the several-hundred-part assembly and write it as STEP. Returns the part count."""
    from OCP.BRep import BRep_Builder
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopoDS import TopoDS_Compound
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from sheet2d.project import build_benchmark_assembly, part_count

    parts = build_benchmark_assembly(blocks, fasteners)
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for part in parts:
        if part[0] == 'box':
            _kind, x, y, z, sx, sy, sz = part
            shape = BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), sx, sy, sz).Shape()
        else:
            _kind, x, y, z, radius, height, _sides = part
            axis = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(0, 0, 1))
            shape = BRepPrimAPI_MakeCylinder(axis, radius, height).Shape()
        builder.Add(compound, shape)
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    if writer.Write(path) != 1:
        raise RuntimeError('the benchmark STEP file was not written')
    return part_count(parts)
