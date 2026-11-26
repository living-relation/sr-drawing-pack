"""The sheet job: short Fusion steps, then a background process. No Fusion."""
import json
import os

from generate_sheet import build_drawing, component_rows, editor_script, generate
from sheet_job import STEP_LIMIT_S, fresh_state, one_step, spawn_background


class _Reader(object):
    def __init__(self, mesh_calls=1):
        self.mesh_calls = mesh_calls
        self.calls = []

    def list_step(self, out_dir):
        self.calls.append(('list', out_dir))
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'occurrences.json'), 'w', encoding='utf-8') as handle:
            json.dump(_occurrences(), handle)
        return {'bodies': 1, 'placements': 2, 'seconds': 0.01}

    def mesh_step(self, out_dir, start=0, budget=3.0, quality='low'):
        self.calls.append(('mesh', start, budget))
        done = len([c for c in self.calls if c[0] == 'mesh']) >= self.mesh_calls
        return {'next': start + 1, 'done': done, 'seconds': 0.02, 'total': self.mesh_calls}


def _occurrences():
    return {
        'document': 'Bracket v3',
        'company': 'Spark Robotic',
        'project': 'Rig 4',
        'units': 'mm',
        'bodies': [{'key': 'a', 'name': 'Bracket'}],
        'placements': [
            {'key': 'a', 'occ': 'Assy:1+Bracket:1'},
            {'key': 'a', 'occ': 'Assy:1+Bracket:2'},
            {'key': 'b', 'occ': 'Assy:1+Lid:1'},
        ],
    }


def test_steps_stay_short_and_do_not_loop_inside_one_call(tmp_path):
    reader = _Reader(mesh_calls=2)
    state = fresh_state()
    state, result = one_step(state, str(tmp_path), reader)
    assert result['step'] == 'list' and state['phase'] == 'mesh'
    state, result = one_step(state, str(tmp_path), reader)
    assert result['step'] == 'mesh' and result['done'] is False and state['phase'] == 'mesh'
    state, result = one_step(state, str(tmp_path), reader)
    assert result['done'] is True and state['phase'] == 'ready'
    try:
        one_step(state, str(tmp_path), reader)
    except ValueError as exc:
        assert 'finished' in str(exc)
    else:
        raise AssertionError('a finished read must not start another step')


def test_a_long_step_is_refused(tmp_path):
    class Slow(object):
        def list_step(self, out_dir):
            return {'seconds': STEP_LIMIT_S}

    try:
        one_step(fresh_state(), str(tmp_path), Slow())
    except RuntimeError as exc:
        assert 'limit' in str(exc)
    else:
        raise AssertionError('a 5 second step must fail')
    try:
        one_step(fresh_state(), str(tmp_path), _Reader(), budget=STEP_LIMIT_S)
    except ValueError as exc:
        assert 'under' in str(exc)
    else:
        raise AssertionError('budget must stay under 5 seconds')


def test_background_process_is_started_and_not_waited_on(tmp_path):
    seen = {}

    class Proc(object):
        def __init__(self, args):
            seen['args'] = args
            self.pid = 99

        def wait(self):
            raise AssertionError('Fusion must not wait')

    proc = spawn_background(str(tmp_path), popen=Proc)
    assert proc.pid == 99
    assert seen['args'][1].endswith('generate_sheet.py')
    assert seen['args'][2] == str(tmp_path)
    assert not hasattr(spawn_background, 'wait')


def test_job_sources_do_not_sleep_or_wait():
    root = os.path.join(os.path.dirname(__file__), '..', 'SRDrawingPDF')
    for name in ('sheet_job.py', 'generate_sheet.py', 'sheet_command.py'):
        text = open(os.path.join(root, name), encoding='utf-8').read()
        assert 'sleep(' not in text, name
        assert '.wait(' not in text, name
        assert 'communicate(' not in text, name


def test_generate_writes_a_sheet_from_the_read_folder(tmp_path):
    with open(os.path.join(str(tmp_path), 'occurrences.json'), 'w', encoding='utf-8') as handle:
        json.dump(_occurrences(), handle)
    result = generate(str(tmp_path), open_editor=False)
    assert os.path.isfile(result['pdf']) and os.path.getsize(result['pdf']) > 100
    doc = json.load(open(result['json'], encoding='utf-8'))
    assert doc['properties']['project'] == 'Spark Robotic / Rig 4'
    assert doc['properties']['title'] == 'BRACKET V3'
    rows = {(r['desc'], r['qty'], r['pn']) for r in doc['bom']}
    assert rows == {('Bracket', 2, ''), ('Lid', 1, '')}
    labels = [el.get('label') for el in doc['sheets'][0]['elements'] if el.get('type') == 'view']
    assert 'TRIMETRIC' in labels and 'FRONT' in labels
    assert result['editor'] is None


def test_blank_design_names_stay_blank(tmp_path):
    data = _occurrences()
    data['company'] = ''
    data['project'] = ''
    with open(os.path.join(str(tmp_path), 'occurrences.json'), 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    doc = build_drawing(str(tmp_path))
    assert doc['properties']['project'] == ''


def test_component_rows_skip_nameless_placements():
    rows = component_rows({'placements': [{'occ': '', 'key': 'x'}], 'bodies': []})
    assert rows == []


def test_editor_script_is_the_local_page():
    path = editor_script()
    assert path and path.endswith(os.path.join('dev', 'sheet_demo.py'))
