"""Title-block project comes from the design, env, or local.toml. Unknown stays blank."""
import json
import os

from sheet2d import settings as S
from sheet2d.commands import execute
from fusion_read import design_fields


def test_neutral_defaults_without_local_toml(tmp_path):
    assert S.title_defaults(str(tmp_path), environ={}) == {'project': ''}


def test_local_toml_then_env(tmp_path):
    (tmp_path / 'local.toml').write_text('[drawing]\nproject = "ACME RIG"\n')
    assert S.title_defaults(str(tmp_path), environ={}) == {'project': 'ACME RIG'}
    d = S.title_defaults(str(tmp_path), environ={'DRAWING_PROJECT': 'OTHER'})
    assert d == {'project': 'OTHER'}


def test_company_and_project_are_copied_and_never_invented():
    assert S.company_project('', '') == ''
    assert S.company_project('Spark Robotic', '') == 'Spark Robotic'
    assert S.company_project('', 'Rig 4') == 'Rig 4'
    assert S.company_project('Spark Robotic', 'Rig 4') == 'Spark Robotic / Rig 4'
    assert S.company_project('Rig 4', 'rig 4') == 'Rig 4'
    assert design_fields({}, '') == {'company': '', 'project': ''}
    assert design_fields({'Company': 'Spark Robotic', 'document': 'Bracket v3'}) == {
        'company': 'Spark Robotic', 'project': '',
    }
    assert design_fields({}, hub_project='Rig 4')['project'] == 'Rig 4'
    # A file name is not a project, even when an attribute is named like one and empty.
    assert design_fields({'project': '  ', 'name': 'Bracket v3'}, '')['project'] == ''


def test_title_block_stays_blank_when_the_design_has_no_project(tmp_path):
    doc = execute(None, 'add_sheet', {'id': 's1'})['document']
    doc = execute(doc, 'set_title', {'field': 'project', 'value': S.company_project('', '')})['document']
    shown = execute(doc, 'title_block', {'sheet': 's1'})['result']['project']
    assert shown == ''
    doc = execute(doc, 'set_title', {
        'field': 'project', 'value': S.company_project('Spark Robotic', 'Rig 4'),
    })['document']
    assert execute(doc, 'title_block', {'sheet': 's1'})['result']['project'] == 'Spark Robotic / Rig 4'
    del tmp_path


def test_dump_keeps_company_and_project_and_leaves_them_blank(tmp_path):
    from sheet2d.meshparts import load_fusion_dump
    folder = tmp_path / 'dump'
    folder.mkdir()
    (folder / 'occurrences.json').write_text(json.dumps({
        'document': 'Bracket v3', 'units': 'mm', 'bodies': [], 'placements': [],
    }), encoding='utf-8')
    _parts, info = load_fusion_dump(str(folder))
    assert info['document'] == 'Bracket v3'
    assert info['company'] == '' and info['project'] == ''
    (folder / 'occurrences.json').write_text(json.dumps({
        'document': 'Bracket v3', 'company': 'Spark Robotic', 'project': 'Rig 4',
        'units': 'mm', 'bodies': [], 'placements': [],
    }), encoding='utf-8')
    _parts, info = load_fusion_dump(str(folder))
    assert S.company_project(info['company'], info['project']) == 'Spark Robotic / Rig 4'


def test_spec_values_win(tmp_path):
    (tmp_path / 'local.toml').write_text('[drawing]\nproject = "ACME RIG"\n')
    info = S.title_info({'title': 'T', 'project': 'JOB X', 'drawn': None}, str(tmp_path), environ={})
    assert info['project'] == 'JOB X' and ('drawn' not in info or not info['drawn']) and info['title'] == 'T'


def test_sheet2d_has_no_hardcoded_product_names():
    root = os.path.join(os.path.dirname(__file__), '..', 'SRDrawingPDF', 'sheet2d')
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith('.py'):
                continue
            src = open(os.path.join(dirpath, name), encoding='utf-8').read()
            assert 'SteveCAD' not in src and 'ST185' not in src, name
