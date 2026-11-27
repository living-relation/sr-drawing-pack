"""Time exact-edge views of an assembly and write a PNG.

From the repo folder (needs OCP and VTK: pip install cadquery-ocp vtk):

  python dev/time_views.py views.png

A real assembly exported from Fusion as STEP:

  python dev/time_views.py views.png --step assembly.step

Keep STEP files outside this public repo. VTK draws the depth picture offscreen.
"""
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, 'SRDrawingPDF'))
sys.path.insert(0, os.path.join(_ROOT, 'dev'))

from sheet2d.project import VIEW_LIMIT_S, VIEW_NAMES  # noqa: E402


def main(argv):
    args = argv[1:]
    step = None
    if '--step' in args:
        i = args.index('--step')
        if i + 1 >= len(args):
            print('usage: python dev/time_views.py views.png [--step assembly.step]')
            return 2
        step = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print('usage: python dev/time_views.py views.png [--step assembly.step]')
        return 2
    from vieweng.xq import XqEngine
    engine = XqEngine()
    ok, why = engine.available()
    if not ok:
        print(why)
        return 1
    cleanup = None
    if not step:
        from vieweng.stepbench import write_benchmark
        handle = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
        handle.close()
        step = handle.name
        cleanup = step
        count = write_benchmark(step)
        print('benchmark parts %d' % count)
    views, timing = engine.project_views(VIEW_NAMES, step=step, mode='exact')
    if cleanup:
        os.remove(cleanup)
    from compare_engines import write_png
    write_png(args[0], {'xq': views}, VIEW_NAMES)
    total = timing['total_s']
    for name in VIEW_NAMES:
        view = views[name]
        print('%s %.3f s  lines %d' % (name, view['seconds'], len(view['lines'])))
    print('read %.3f s  mesh %.3f s  edges %.3f s' % (
        timing['read_s'], timing['mesh_s'], timing['edges_s']))
    print('total %.3f s  limit %.0f s  %s' % (total, VIEW_LIMIT_S, 'PASS' if total < VIEW_LIMIT_S else 'FAIL'))
    print(args[0])
    return 0 if total < VIEW_LIMIT_S else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
