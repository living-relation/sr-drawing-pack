"""Title-block formats: edit the boxes, keep a logo, one template per sheet size."""
import os
import sys

from sheet2d.commands import execute
from sheet2d.formats import (
    SIZES, add_box, attach_template, default_template, field_text, label_rect, load_template,
    move_box, remove_box, resize_box, save_template, set_logo, template_for, template_svg,
    value_place,
)
from sheet2d.model import DrawingDocument, size_of
from sheet2d.render import render_sheets

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dev'))
from title_editor import Editor  # noqa: E402


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def test_values_sit_clear_of_labels():
    info = {
        'project': 'Spark Robotic / Rig 4', 'title': 'BRACKET', 'pn': 'SR-14',
        'rev': 'A', 'material': 'AL 6061', 'scale': '1:2', 'units': 'mm',
        'size': 'B', 'date': '2026-11-26', 'drawn': 'DL', 'source': 'FUSION',
    }
    for size in SIZES:
        tpl = default_template(size)
        for box in tpl['boxes']:
            if box['field'] in ('angle', 'tol'):
                continue
            value = field_text(box['field'], info, 1, 1, box.get('text') or '')
            place = value_place(box['w'], box['h'], value, 4.6 if box['field'] == 'title' else 3.2, False)
            assert place is not None, box['id']
            assert not _overlap(label_rect(box['w'], box['h'], box['label']), place['rect']), box['id']
    sheet = next(b for b in default_template('B')['boxes'] if b['id'] == 'sheet')
    place = value_place(sheet['w'], sheet['h'], '1 OF 1', 3.2, False)
    label = label_rect(sheet['w'], sheet['h'], 'SHEET')
    assert place['rect'][1] + place['rect'][3] <= label[1]


def test_sizes_include_ansi_and_metric():
    for name in ('A', 'B', 'C', 'D', 'A4', 'A3', 'A2', 'A1', 'A0'):
        assert name in SIZES
    doc = DrawingDocument()
    assert size_of(doc, 'A3')['width'] == 420.0
    assert size_of(doc, 'D')['height'] == 558.8


def test_edit_boxes_logo_and_save(tmp_path):
    tpl = default_template('B')
    assert any(b['field'] == 'tol' for b in tpl['boxes'])
    assert any(b['label'] == 'COMPANY / PROJECT' for b in tpl['boxes'])
    tpl = move_box(tpl, 'tol', 30, 12)
    tpl = resize_box(tpl, 'tol', 80, 40)
    tol = next(b for b in tpl['boxes'] if b['id'] == 'tol')
    assert (tol['x'], tol['y'], tol['w'], tol['h']) == (30, 12, 80, 40)
    tpl = add_box(tpl, field='static', label='CAGE', text='1ABC2')
    assert any(b['label'] == 'CAGE' for b in tpl['boxes'])
    added = next(b for b in tpl['boxes'] if b['label'] == 'CAGE')
    tpl = remove_box(tpl, added['id'])
    assert all(b['label'] != 'CAGE' for b in tpl['boxes'])
    logo = set_logo(tpl, 'mark.svg', '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>')
    assert logo['logo']['kind'] == 'svg'
    path = tmp_path / 'B.json'
    save_template(logo, str(path))
    again = load_template(str(path))
    assert again['logo']['name'] == 'mark.svg'
    assert field_text('project', {'project': ''}) == ''
    assert field_text('project', {'project': 'Spark Robotic'}) == 'Spark Robotic'


def test_sheet_uses_the_template_for_its_size():
    doc = execute(None, 'add_sheet', {'id': 's1', 'size': 'B'})['document']
    tpl = add_box(default_template('B'), field='static', label='CAGE CODE', text='1ABC2')
    doc = attach_template(doc, tpl)
    # attach_template returns a dict; the document object needs the same formats.
    loaded = DrawingDocument.from_dict(doc)
    assert 'B' in loaded.formats
    texts = []
    for sh in render_sheets(loaded):
        texts.extend(it[3] for it in sh.items if it[0] == 'tx')
    blob = '\n'.join(texts)
    assert 'CAGE CODE' in blob and '1ABC2' in blob
    assert 'COMPANY / PROJECT' in blob
    assert template_for(loaded, 'A3')['size'] == 'A3'
    svg = template_svg(tpl, {'title': 'BRACKET'})
    assert 'data-box="tol"' in svg and 'BRACKET' in svg


def test_editor_moves_a_box_and_remembers_the_size(tmp_path):
    editor = Editor(str(tmp_path))
    body = editor.command('boot', {})
    assert body['template']['size'] == 'B'
    assert 'COMPANY / PROJECT' in body['svg']
    moved = editor.command('move', {'id': 'title', 'x': 40, 'y': 50})
    title = next(b for b in moved['template']['boxes'] if b['id'] == 'title')
    assert title['x'] == 40 and title['y'] == 50
    sized = editor.command('resize', {'id': 'title', 'w': 60, 'h': 18})
    title = next(b for b in sized['template']['boxes'] if b['id'] == 'title')
    assert title['w'] == 60 and title['h'] == 18
    editor.command('add', {'field': 'static', 'label': 'CAGE'})
    editor.command('save', {})
    fresh = Editor(str(tmp_path))
    loaded = fresh.command('size', {'size': 'B'})
    assert any(b['label'] == 'CAGE' for b in loaded['template']['boxes'])
    other = fresh.command('size', {'size': 'A3'})
    assert other['template']['size'] == 'A3'
    assert all(b['label'] != 'CAGE' for b in other['template']['boxes'])
