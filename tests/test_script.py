"""Checks for the SR Drawing PDF add-in that do not need Fusion."""
import json
import os
import re
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDIN = os.path.join(ROOT, 'SRDrawingPDF')


def test_manifest_valid():
    with open(os.path.join(ADDIN, 'SRDrawingPDF.manifest'), encoding='utf-8') as f:
        m = json.load(f)
    assert m['type'] == 'addin' and m['autodeskProduct'] == 'Fusion'
    assert m['author'] == 'Spark Robotic'
    assert 'SR Drawing PDF' in m['description']['']
    assert m.get('runOnStartup') is True


def test_script_is_cleaned_and_renamed():
    src = open(os.path.join(ADDIN, 'SRDrawingPDF.py'), encoding='utf-8').read()
    assert src.count('def run(') == 1
    assert 'is the active Document.' not in src
    assert 'ActiveDesignToPDF' not in src
    assert 'SR Drawing PDF' in src
    assert 'def setup_drawing(' in src
    assert 'def add_dimensions(' in src
    assert 'def start_export(' in src
    assert "CMD_ID = 'srDrawingPdfCmd'" in src
    assert 'Your code goes here' not in src


def test_no_machine_paths_in_script_tree():
    banned = re.compile(r'[A-Za-z]:\\?Users\\?[A-Za-z]', re.I)
    for dirpath, _, files in os.walk(ADDIN):
        for name in files:
            if name.endswith(('.png', '.svg', '.pyc', '.pyo')) or name == '.DS_Store':
                continue
            try:
                text = open(os.path.join(dirpath, name), encoding='utf-8').read()
            except UnicodeDecodeError:
                continue
            assert not banned.search(text), name


def _png_size(path):
    with open(path, 'rb') as f:
        assert f.read(8) == b'\x89PNG\r\n\x1a\n'
        length, typ = struct.unpack('>I4s', f.read(8))
        assert typ == b'IHDR'
        w, h = struct.unpack('>II', f.read(8))
        return w, h


def test_icons_present():
    d = os.path.join(ADDIN, 'resources', 'icon')
    for name, n in (('16x16', 16), ('32x32', 32)):
        assert _png_size(os.path.join(d, name + '.png')) == (n, n)
