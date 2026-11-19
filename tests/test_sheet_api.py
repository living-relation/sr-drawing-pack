"""Command API: sheets, linked titles, revs, BOM split, balloons, PDF."""
import ast
import json
import os

import pytest

from sheet2d import canvas as D
from sheet2d.commands import execute
from sheet2d.sample import build_sample

ADDIN = os.path.join(os.path.dirname(__file__), '..', 'SRDrawingPDF')


def _go(doc, command, **args):
    out = execute(doc, command, args)
    return out['document'], out['result']


def test_add_remove_reorder_sheets_and_size():
    doc, info = _go(None, 'add_sheet', id='s1', name='First')
    assert info['size'] == 'B' and info['index'] == 0
    doc, again = _go(doc, 'add_sheet', id='s1', name='Ignored')
    assert again['name'] == 'First' and len(doc['sheets']) == 1
    doc, _info = _go(doc, 'add_sheet', id='s2')
    doc, _info = _go(doc, 'add_sheet', id='s3')
    doc, order = _go(doc, 'reorder_sheets', order=['s3', 's1', 's2'])
    assert order['order'] == ['s3', 's1', 's2']
    assert [s['id'] for s in doc['sheets']] == ['s3', 's1', 's2']
    doc, gone = _go(doc, 'remove_sheet', id='s1')
    assert gone['removed'] is True
    doc, gone = _go(doc, 'remove_sheet', id='s1')
    assert gone['removed'] is False
    assert [s['id'] for s in doc['sheets']] == ['s3', 's2']
    doc, spec = _go(doc, 'add_sheet_size', name='C', width=254, height=127, label='C (test)', zones=[4, 2])
    assert spec['size']['width'] == 254
    doc, info = _go(doc, 'add_sheet', id='wide', size='C')
    assert info['size'] == 'C'
    block = execute(doc, 'title_block', {'sheet': 'wide'})['result']
    assert block['size'] == 'C (test)'


def test_title_fields_bind_across_sheets():
    doc, _info = _go(None, 'add_sheet', id='s1')
    doc, _info = _go(doc, 'add_sheet', id='s2', scale='AS SHOWN')
    before = json.dumps(doc)
    doc, _info = _go(doc, 'set_title', field='project', value='ALPHA')
    doc, _info = _go(doc, 'set_title', field='title', value='BRACKET')
    doc, _info = _go(doc, 'set_title', field='scale', value='1:2')
    assert json.loads(before)['properties']['project'] == ''
    a = execute(doc, 'title_block', {'sheet': 's1'})['result']
    b = execute(doc, 'title_block', {'sheet': 's2'})['result']
    assert a['project'] == b['project'] == 'ALPHA'
    assert a['title'] == b['title'] == 'BRACKET'
    assert a['sheet'] == '1 OF 2' and b['sheet'] == '2 OF 2'
    assert a['scale'] == '1:2' and b['scale'] == 'AS SHOWN'
    assert a['size'] == 'B (11x17)'
    doc, _info = _go(doc, 'reorder_sheets', order=['s2', 's1'])
    assert execute(doc, 'title_block', {'sheet': 's1'})['result']['sheet'] == '2 OF 2'
    doc, _info = _go(doc, 'set_title', field='project', value='BETA')
    assert execute(doc, 'title_block', {'sheet': 's2'})['result']['project'] == 'BETA'
    assert execute(doc, 'title_block', {'sheet': 's1'})['result']['project'] == 'BETA'
    doc, _info = _go(doc, 'remove_sheet', id='s2')
    assert execute(doc, 'title_block', {'sheet': 's1'})['result']['sheet'] == '1 OF 1'


def test_revision_letters_clerical_draft_and_drawn():
    doc, _info = _go(None, 'add_sheet', id='s1')
    doc, row = _go(doc, 'add_revision', rev='A', desc='nope', by='dg', date='2026-11-01')
    assert row['rows'][0]['desc'] == 'Initial'
    assert row['drawn'] == 'DG'
    doc, row = _go(doc, 'add_revision', rev='B', desc='second', by='JD', date='2026-11-02')
    assert doc['properties']['rev'] == 'B'
    assert doc['properties']['drawn'] == 'DG'
    doc, _info = _go(doc, 'set_title', field='rev', value='b.01')
    assert doc['properties']['rev'] == 'B.01'
    assert [r['rev'] for r in doc['revlog']] == ['A', 'B']
    with pytest.raises(ValueError):
        execute(doc, 'add_revision', {'rev': 'B.01', 'desc': 'x', 'by': 'DG', 'date': '2026-11-03'})
    log = list(doc['revlog'])
    rev = doc['properties']['rev']
    doc, draft = _go(doc, 'set_draft', n=2)
    assert draft['draft'] == 2
    assert doc['properties']['rev'] == rev and doc['revlog'] == log
    block = execute(doc, 'title_block', {'sheet': 's1'})['result']
    assert block['mark'] == 'DRAFT 2, NOT RELEASED'
    assert block['rev'] == 'B.01'
    doc, cleared = _go(doc, 'set_draft', n=None)
    assert cleared['draft'] is None


def test_revision_table_window_drops_old_and_clerical():
    doc, _info = _go(None, 'add_sheet', id='s1')
    letters = list('ABCDEFGH')
    doc['revlog'] = [
        {'rev': letter, 'desc': letter + ' change', 'by': 'DG', 'date': '01/11/26'} for letter in letters
    ]
    doc['revlog'].append({'rev': 'C.01', 'desc': 'typo', 'by': 'DG', 'date': '02/11/26'})
    rows = execute(doc, 'revision_table', {})['result']['rows']
    assert [r['rev'] for r in rows] == list('CDEFGH')
    assert all(r['rev'] != 'C.01' for r in rows)


def test_revlog_file_roundtrip(tmp_path):
    doc, _info = _go(None, 'add_sheet', id='s1')
    doc, _info = _go(doc, 'add_revision', rev='A', desc='x', by='DG', date='2026-11-01')
    path = str(tmp_path / 'REVLOG.md')
    doc, _info = _go(doc, 'save_revlog', path=path, title='SAMPLE')
    fresh, _info = _go(None, 'add_sheet', id='s1')
    fresh, loaded = _go(fresh, 'load_revlog', path=path)
    assert loaded['rev'] == 'A' and loaded['drawn'] == 'DG'
    assert fresh['revlog'][0]['desc'] == 'Initial'


def test_bom_splits_across_sheets_and_balloons_follow_renumber():
    doc, _info = _go(None, 'add_sheet', id='s1')
    doc, _info = _go(doc, 'add_sheet', id='s2')
    for i in range(1, 6):
        doc, _info = _go(doc, 'add_bom_row', key='k%d' % i, pn='P-%d' % i, desc='PART', mat='AL', qty=1)
    h = 2.0
    colw = D.BOM_COLS
    hh, _wrapped = D.bom_row_height(['1', '1', 'P-1', 'PART', 'AL'], colw, h)
    header = D.bom_header_height(h, False)
    doc, placed = _go(
        doc, 'place_bom', id='bom1', sheet='s1', x1=400, ytop=200,
        max_height=header + 2 * hh, text_h=h)
    assert placed['segment']['rows'] == ['k1', 'k2']
    assert placed['segment']['continued'] is False
    assert placed['overflow'] == ['k3', 'k4', 'k5']
    doc, placed = _go(
        doc, 'place_bom', id='bom2', sheet='s2', x1=400, ytop=220,
        max_height=80, text_h=h)
    assert placed['segment']['continued'] is True
    assert placed['segment']['rows'] == ['k3', 'k4', 'k5']
    assert placed['overflow'] == []
    doc, _info = _go(doc, 'place_balloon', id='bal', sheet='s1', bom_key='k2', x=10, y=10, ax=20, ay=20)
    marks = execute(doc, 'sheet_marks', {'sheet': 's1'})['result']
    assert marks['balloons'][0]['item'] == 2
    doc, _info = _go(doc, 'renumber_bom', start=10)
    marks = execute(doc, 'sheet_marks', {'sheet': 's1'})['result']
    assert marks['balloons'][0]['item'] == 11
    assert marks['balloons'][0]['bom_key'] == 'k2'
    doc, again = _go(doc, 'place_balloon', id='bal', sheet='s1', bom_key='k2', x=12, y=12, ax=22, ay=22)
    assert again['item'] == 11
    assert len(execute(doc, 'sheet_marks', {'sheet': 's1'})['result']['balloons']) == 1


def test_note_flags_follow_note_numbers():
    doc, _info = _go(None, 'add_sheet', id='s1')
    doc, _info = _go(doc, 'add_note', key='n1', text='First')
    doc, _info = _go(doc, 'add_note', key='n2', text='Second')
    doc, flag = _go(doc, 'place_note_flag', id='f1', sheet='s1', note_key='n2', x=5, y=5, ax=8, ay=8)
    assert flag['number'] == 2
    doc, _info = _go(doc, 'delete_note', key='n1')
    marks = execute(doc, 'sheet_marks', {'sheet': 's1'})['result']
    assert marks['note_flags'][0]['number'] == 1
    doc, _info = _go(doc, 'delete_note_flag', id='f1')
    doc, gone = _go(doc, 'delete_note_flag', id='f1')
    assert gone['removed'] is False


def test_csv_and_component_rows(tmp_path):
    text = 'item,qty,part number,description,material,shown\n1,2,AA-1,WIDGET,STEEL,yes\n2,1,AA-2,HIDDEN,BRASS,no\n'
    doc, loaded = _go(None, 'load_bom_csv', text=text, replace=True)
    # load_bom_csv on a brand new document still needs the command to create the doc.
    # execute(None) starts empty, then adds rows. There is no sheet yet. That is fine.
    assert loaded['count'] == 2
    assert doc['bom'][1]['shown'] is False
    assert doc['bom'][0]['pn'] == 'AA-1'
    path = tmp_path / 'bom.csv'
    path.write_text(text)
    doc, loaded = _go(doc, 'load_bom_csv', path=str(path), replace=True)
    assert loaded['count'] == 2
    doc, loaded = _go(doc, 'load_bom_components', replace=True, components=[
        {'part_number': 'BB-1', 'description': 'BLOCK', 'material': 'AL', 'qty': 3},
    ])
    assert loaded['count'] == 1 and doc['bom'][0]['pn'] == 'BB-1' and doc['bom'][0]['qty'] == 3


def test_save_load_roundtrip(tmp_path):
    doc = build_sample()
    path = str(tmp_path / 'drawing.json')
    execute(doc, 'save', {'path': path})
    loaded = execute(None, 'load', {'path': path})['document']
    assert loaded['properties']['pn'] == 'SR-SAMPLE-100'
    assert len(loaded['sheets']) == 2
    assert loaded['revlog'][-1]['rev'] == 'C'


def test_frame_has_zones_title_and_draft_mark():
    sh = D.Sheet()
    info = {
        'project': 'ALPHA', 'title': 'BRACKET', 'pn': 'N-1', 'rev': 'C',
        'material': 'SEE BOM', 'scale': '1:2', 'units': 'mm', 'date': '2026-11-19',
        'drawn': 'DG', 'source': 'part.step', 'size_label': 'B (11x17)',
        'revlog': [], 'draft': 3,
    }
    D.draw_frame(sh, info, 1, 2)
    texts = [it[3] for it in sh.items if it[0] == 'tx']
    assert 'ALPHA' in texts and 'BRACKET' in texts and '3RD ANGLE' in texts
    assert '1 OF 2' in texts and 'B (11x17)' in texts and 'DRAFT 3, NOT RELEASED' in texts
    assert '8' in texts and 'D' in texts and 'REVISIONS' in texts
    assert any(it[0] == 'wm' for it in sh.items)
    border = [it for it in sh.items if it[0] == 'pl' and it[2] == 'border'][0]
    assert border[1][0] == (10.0, 10.0)
    assert border[1][2] == (D.PW - 10, D.PH - 10)


def test_sample_pdf_is_two_size_b_sheets(tmp_path):
    doc = build_sample()
    layout = execute(doc, 'layout_bom', {})['result']
    assert layout['overflow'] == []
    assert layout['segments'][0]['rows'] and layout['segments'][1]['continued']
    assert layout['segments'][1]['sheet'] == 's2'
    path = str(tmp_path / 'sample.pdf')
    result = execute(doc, 'export_pdf', {'path': path})['result']
    assert result['pages'] == 2
    assert result['warnings'] == []
    raw = open(path, 'rb').read()
    assert b'/MediaBox [0 0 1224.00 792.00]' in raw
    assert b'SAMPLE BRACKET ASSEMBLY' in raw
    assert b'SR-SAMPLE-100' in raw
    assert b'3RD ANGLE' in raw
    assert b'REVISIONS' in raw
    assert b'NOT SHOWN' in raw
    assert b'CONT.' in raw
    assert b'NOTES:' in raw
    assert b'ASME Y14.5-2018' in raw
    assert b'DRAFT' not in raw
    assert b'/BaseFont /Helvetica' in raw


def test_draft_pdf_marks_every_page(tmp_path):
    doc = build_sample()
    doc, _info = _go(doc, 'set_draft', n=2)
    path = str(tmp_path / 'draft.pdf')
    execute(doc, 'export_pdf', {'path': path})
    raw = open(path, 'rb').read()
    assert raw.count(b'DRAFT 2, NOT RELEASED') >= 2


def test_custom_size_page_box(tmp_path):
    doc, _info = _go(None, 'add_sheet_size', name='C', width=254, height=127, label='C (test)')
    doc, _info = _go(doc, 'add_sheet', id='s1', size='C')
    path = str(tmp_path / 'c.pdf')
    execute(doc, 'export_pdf', {'path': path})
    raw = open(path, 'rb').read()
    assert b'/MediaBox [0 0 720.00 360.00]' in raw


def test_sheet2d_imports_nothing_fusion_cannot_bundle():
    banned_roots = {
        'adsk', 'build123d', 'OCP', 'matplotlib', 'shapely', 'scipy', 'numpy',
        'ezdxf', 'reportlab', 'fpdf', 'PIL',
    }
    root = os.path.join(ADDIN, 'sheet2d')
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith('.py'):
                continue
            path = os.path.join(dirpath, name)
            tree = ast.parse(open(path, encoding='utf-8').read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name.split('.')[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [(node.module or '').split('.')[0]]
                else:
                    continue
                assert not (set(mods) & banned_roots), (name, mods)


def test_commands_return_json():
    doc = build_sample()
    out = execute(doc, 'list_commands', {})
    json.dumps(out)
    names = [item['name'] for item in out['result']['commands']]
    assert 'export_pdf' in names and 'set_draft' in names and 'place_balloon' in names
    assert execute(doc, 'set_title', {'field': 'title', 'value': 'Z'})['document'] is not doc
