"""Hand the drawing to a background process so Fusion stays free.

Fusion calls one_step once per turn: first the body list, then mesh chunks.
Each step has to finish in under 5 seconds. This module never sleeps and
never polls. When the read is done, spawn_background starts another process
and returns at once. That process builds the sheet and opens the editor.
"""
import os
import subprocess
import sys

STEP_LIMIT_S = 5.0
MESH_BUDGET_S = 3.0


def fresh_state():
    """The read has not started."""
    return {'phase': 'list', 'start': 0}


def one_step(state, out_dir, reader, budget=MESH_BUDGET_S):
    """Run the next read step. Returns (new state, result).

    `reader` is fusion_read, or a stand-in with list_step and mesh_step.
    The new phase is 'mesh' after the list, and 'ready' when meshing is done.
    """
    if budget >= STEP_LIMIT_S:
        raise ValueError('a Fusion step must stay under %s seconds' % STEP_LIMIT_S)
    os.makedirs(out_dir, exist_ok=True)
    phase = state.get('phase')
    if phase == 'list':
        result = dict(reader.list_step(out_dir))
        result['step'] = 'list'
        nxt = {'phase': 'mesh', 'start': 0}
    elif phase == 'mesh':
        result = dict(reader.mesh_step(out_dir, state.get('start') or 0, budget=budget))
        result['step'] = 'mesh'
        nxt = {'phase': 'ready' if result.get('done') else 'mesh', 'start': result.get('next') or 0}
    else:
        raise ValueError('the read is already finished')
    seconds = float(result.get('seconds') or 0)
    if seconds >= STEP_LIMIT_S:
        raise RuntimeError('read step took %.2f s; the limit is %s s' % (seconds, STEP_LIMIT_S))
    result['phase'] = nxt['phase']
    return nxt, result


def background_command(out_dir, python=None):
    """The command line that builds the sheet. Fusion must not wait on it."""
    python = python or sys.executable
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generate_sheet.py')
    return [python, script, out_dir]


def spawn_background(out_dir, python=None, popen=None):
    """Start the sheet process and return it. Does not wait."""
    popen = popen or subprocess.Popen
    return popen(background_command(out_dir, python))
