"""Checks for the SR Drawing PDF script that do not need Fusion."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'SRDrawingPDF')


def test_manifest_valid():
    with open(os.path.join(SCRIPT, 'SRDrawingPDF.manifest'), encoding='utf-8') as f:
        m = json.load(f)
    assert m['type'] == 'script' and m['autodeskProduct'] == 'Fusion'
    assert m['author'] == 'Spark Robotic'
    assert 'SR Drawing PDF' in m['description']['']
    assert m.get('iconFilename') == 'ScriptIcon.svg'
    assert os.path.isfile(os.path.join(SCRIPT, 'ScriptIcon.svg'))


def test_script_is_cleaned_and_renamed():
    src = open(os.path.join(SCRIPT, 'SRDrawingPDF.py'), encoding='utf-8').read()
    assert src.count('def run(') == 1
    assert 'is the active Document.' not in src
    assert 'ActiveDesignToPDF' not in src
    assert 'SR Drawing PDF' in src
    assert 'def setup_drawing(' in src
    assert 'def add_dimensions(' in src
    assert 'pdf_path=None' in src
    assert 'Your code goes here' not in src


def test_no_machine_paths_in_script_tree():
    banned = re.compile(r'[A-Za-z]:\\\\?Users\\\\?[A-Za-z]', re.I)
    for dirpath, _, files in os.walk(SCRIPT):
        for name in files:
            if name.endswith(('.png', '.svg')):
                continue
            text = open(os.path.join(dirpath, name), encoding='utf-8').read()
            assert not banned.search(text), name
