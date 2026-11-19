"""editor_api finds the command module already loaded in this process."""
import importlib.util
import os
import sys
import types

ADDIN = os.path.join(os.path.dirname(__file__), '..', 'SRDrawingPDF')


def _load_addin():
    adsk = sys.modules.get('adsk')
    if adsk is None:
        adsk = types.ModuleType('adsk')
        sys.modules['adsk'] = adsk
    for name in ('core', 'fusion', 'drawing'):
        if not hasattr(adsk, name):
            sub = types.ModuleType('adsk.' + name)
            setattr(adsk, name, sub)
            sys.modules['adsk.' + name] = sub

    class _H:
        def __init__(self, *a):
            pass

    adsk.core.CommandCreatedEventHandler = adsk.core.InputChangedEventHandler = _H
    adsk.core.CommandEventHandler = adsk.core.DocumentEventHandler = adsk.core.CustomEventHandler = _H
    spec = importlib.util.spec_from_file_location('srdp_editor_api_under_test', os.path.join(ADDIN, 'SRDrawingPDF.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_editor_api_reuses_sys_modules():
    from sheet2d import commands as commands
    mod = _load_addin()
    before = list(sys.path)
    first = mod.editor_api()
    second = mod.editor_api()
    assert first is commands
    assert second is first
    assert sys.modules['sheet2d.commands'] is commands
    assert sys.path == before


def test_button_module_does_not_import_sheet2d_at_load():
    src = open(os.path.join(ADDIN, 'SRDrawingPDF.py'), encoding='utf-8').read()
    head = src.split('def run(', 1)[0]
    assert 'import sheet2d' not in head
    assert 'def editor_api(' in src
    assert 'def start_export(' in src
