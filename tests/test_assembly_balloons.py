"""BOM rows from a component list, and balloons on one view."""
import math

from sheet2d.callouts import CLEAR, _hits_rect
from sheet2d.canvas import TOL_W, PW
from sheet2d.commands import execute
from sheet2d.model import DrawingDocument
from sheet2d.render import render_sheets


def _go(doc, command, **args):
    out = execute(doc, command, args)
    return out['document'], out['result']


def _components():
    return [
        {'part_number': 'M3-8', 'description': 'SCREW, M3', 'at': [0.3, 0.6]},
        {'part_number': 'M3-8', 'description': 'SCREW, M3', 'at': [0.7, 0.4]},
        {'name': 'LID'},
        {'part_number': '', 'description': ''},
    ]


def _sheet():
    doc, _res = _go(None, 'add_sheet', id='s1')
    doc, _res = _go(doc, 'place_view', id='v_front', sheet='s1', x=30, y=140, w=80, h=50, label='FRONT')
    doc, _res = _go(doc, 'place_view', id='v_trimetric', sheet='s1', x=200, y=120, w=110, h=70, label='TRIMETRIC')
    return doc


def _balloons(doc):
    return [el for el in doc['sheets'][0]['elements'] if el.get('type') == 'balloon']


def _inside(el, view):
    return view['x'] <= el['ax'] <= view['x'] + view['w'] and view['y'] <= el['ay'] <= view['y'] + view['h']


def test_component_list_rolls_up_and_anchors_bottom_left():
    doc = _sheet()
    doc, res = _go(doc, 'bom_from_components', sheet='s1', components=_components())
    rows = doc['bom']
    assert [(r['item'], r['qty'], r['pn'], r['desc']) for r in rows] == [
        (1, 2, 'M3-8', 'SCREW, M3'),
        (2, 1, '', 'LID'),
        (3, 1, '', ''),
    ]
    assert res['anchor'] == 'bottom_left'
    assert res['segment']['anchor'] == 'bottom_left'
    assert abs(res['segment']['bottom'] - 10.0) < 1e-6


def test_above_title_is_the_other_anchor():
    doc = _sheet()
    doc, res = _go(doc, 'bom_from_components', sheet='s1', anchor='above_title', components=_components()[:1])
    assert res['anchor'] == 'above_title'
    assert res['segment']['x1'] == PW - 10.0


def test_balloons_land_on_the_trimetric_view_and_match_the_bom():
    doc = _sheet()
    doc, _res = _go(doc, 'bom_from_components', sheet='s1', components=_components())
    doc, res = _go(doc, 'auto_balloons', sheet='s1', components=_components(), layout='top')
    assert res['view'] == 'v_trimetric'
    balloons = _balloons(doc)
    assert len(balloons) == 3  # one per part, not one per screw
    view = next(el for el in doc['sheets'][0]['elements'] if el['id'] == 'v_trimetric')
    front = next(el for el in doc['sheets'][0]['elements'] if el['id'] == 'v_front')
    by_item = {b['item']: b for b in res['balloons']}
    assert [by_item[n]['id'] for n in (1, 2, 3)]
    assert by_item[1]['item'] == 1 and by_item[2]['item'] == 2
    for el in balloons:
        assert _inside(el, view)
        assert not _inside(el, front)
    keys = {b['bom_key']: b for b in balloons}
    assert abs(keys['pn:M3-8']['ax'] - (200 + 0.3 * 110)) < 1e-6
    texts = [it[3] for sh in render_sheets(DrawingDocument.from_dict(doc)) for it in sh.items if it[0] == 'tx']
    assert 'M3-8' in texts and 'SCREW, M3' in texts and 'LID' in texts
    assert '1' in texts and '2' in texts


def test_every_balloon_stays_clear_of_the_others_and_the_title_block():
    doc = _sheet()
    doc, _res = _go(doc, 'bom_from_components', sheet='s1', components=[
        {'part_number': 'P%d' % i, 'description': 'PART %d' % i} for i in range(1, 7)
    ])
    doc, _res = _go(doc, 'auto_balloons', sheet='s1', layout='square')
    balloons = _balloons(doc)
    assert len(balloons) == 6
    for i, a in enumerate(balloons):
        for b in balloons[i + 1:]:
            assert math.hypot(a['x'] - b['x'], a['y'] - b['y']) >= 2.0 * CLEAR - 0.05
    title = (PW - 10.0 - 178.0 - TOL_W, 10.0, PW - 10.0, 62.0)
    view = next(el for el in doc['sheets'][0]['elements'] if el['id'] == 'v_trimetric')
    frame = (view['x'], view['y'], view['x'] + view['w'], view['y'] + view['h'])
    for el in balloons:
        assert not _hits_rect(el['x'], el['y'], CLEAR, title)
        assert not _hits_rect(el['x'], el['y'], CLEAR, frame)


def test_ignore_multiple_off_balloons_every_instance_with_the_same_number():
    doc = _sheet()
    doc, _res = _go(doc, 'bom_from_components', sheet='s1', components=_components())
    doc, res = _go(doc, 'auto_balloons', sheet='s1', components=_components(),
                   ignore_multiple=False, layout='right')
    items = sorted(b['item'] for b in res['balloons'])
    assert items == [1, 1, 2, 3]
    balloons = _balloons(doc)
    screw = [el for el in balloons if el['bom_key'] == 'pn:M3-8']
    assert len(screw) == 2
    assert {round(el['ax'], 3) for el in screw} == {200 + 0.3 * 110, 200 + 0.7 * 110}


def _xs(doc, result):
    found = {el['id']: el for el in _balloons(doc)}
    return [found[b['id']]['x'] for b in result['balloons']]


def test_reverse_and_magnetic_line():
    doc = _sheet()
    doc, _res = _go(doc, 'bom_from_components', sheet='s1', components=_components()[:3])
    doc, forward = _go(doc, 'auto_balloons', sheet='s1', layout='top', magnetic=True)
    assert forward['magnetic'] is True and len(forward['balloons']) == 2
    assert forward['lines']
    assert any(el.get('type') == 'magline' for el in doc['sheets'][0]['elements'])
    left_to_right = _xs(doc, forward)
    assert left_to_right[0] < left_to_right[1]
    doc, backward = _go(doc, 'auto_balloons', sheet='s1', layout='top', reverse=True, magnetic=True)
    assert backward['reverse'] is True
    swapped = _xs(doc, backward)
    assert swapped[0] > swapped[1]
    doc, circ = _go(doc, 'auto_balloons', sheet='s1', layout='circular', magnetic=True)
    assert circ['magnetic'] is False
    assert not any(el.get('type') == 'magline' for el in doc['sheets'][0]['elements'])


def test_drag_keeps_the_leader_end():
    from sheet2d.scene import build_scene
    doc = _sheet()
    doc, _res = _go(doc, 'bom_from_components', sheet='s1', components=_components()[:1])
    doc, res = _go(doc, 'auto_balloons', sheet='s1', layout='left')
    bid = res['balloons'][0]['id']
    el = next(b for b in _balloons(doc) if b['id'] == bid)
    doc, moved = _go(doc, 'move_balloon', id=bid, x=el['x'] + 12, y=el['y'] + 4)
    assert moved['item'] == 1
    again = next(b for b in _balloons(doc) if b['id'] == bid)
    assert again['x'] == el['x'] + 12 and again['y'] == el['y'] + 4
    assert again['ax'] == el['ax'] and again['ay'] == el['ay']
    svg = build_scene(doc)['svg']
    assert 'data-balloon="%s"' % bid in svg

    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dev'))
    from sheet_demo import Demo
    demo = Demo()
    before = demo.scene()
    assert 'data-balloon="b1"' in before['svg']
    scene = demo.command('move_balloon', {'id': 'b1', 'x': 40, 'y': 50, 'ax': 190, 'ay': 145})
    assert 'data-balloon="b1"' in scene['svg']
    found = next(el for el in demo.doc['sheets'][0]['elements'] if el.get('id') == 'b1')
    assert found['x'] == 40 and found['ax'] == 190 and found['ay'] == 145
