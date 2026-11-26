"""Build the sheet from a Fusion read folder, then open the editor.

This runs outside Fusion. It does not import Fusion and it does not sleep.
Views are frames. When the folder has meshes, the existing view builder fills
them. When it does not, the four view frames are empty.
"""
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from sheet2d.commands import execute  # noqa: E402
from sheet2d.meshparts import component_name  # noqa: E402
from sheet2d.model import DrawingDocument  # noqa: E402
from sheet2d.render import export_pdf  # noqa: E402
from sheet2d.settings import company_project  # noqa: E402

_VIEWS = (
    ('v_front', 'FRONT', 24.0, 150.0, 100.0, 60.0),
    ('v_top', 'TOP', 24.0, 220.0, 100.0, 40.0),
    ('v_right', 'RIGHT', 140.0, 150.0, 60.0, 60.0),
    ('v_trimetric', 'TRIMETRIC', 220.0, 160.0, 120.0, 80.0),
)


def editor_script():
    """dev/sheet_demo.py next to this add-in, following a junction. None if it is not there."""
    root = os.path.dirname(os.path.realpath(_HERE))
    path = os.path.join(root, 'dev', 'sheet_demo.py')
    return path if os.path.isfile(path) else None


def component_rows(occurrences):
    """One record per component name. qty is how many placements use that name.

    The part number stays blank: the read does not carry one unless a later
    field says so. The description is the component name, which is data.
    A placement with no name is skipped.
    """
    counts = {}
    order = []
    names = {b.get('key'): (b.get('name') or '') for b in occurrences.get('bodies') or []}
    for item in occurrences.get('placements') or []:
        name = component_name(item.get('occ') or '') or names.get(item.get('key')) or ''
        name = name.strip()
        if not name:
            continue
        if name not in counts:
            order.append(name)
            counts[name] = 0
        counts[name] += 1
    return [{'description': name, 'part_number': '', 'qty': counts[name]} for name in order]


def build_drawing(out_dir):
    """A drawing dict from the read folder. Does not need Fusion."""
    with open(os.path.join(out_dir, 'occurrences.json'), encoding='utf-8') as handle:
        occurrences = json.load(handle)
    parts = _parts(out_dir)
    title = (occurrences.get('document') or 'DRAWING').strip() or 'DRAWING'
    if parts:
        from sheet2d.viewsheet import build_view_sheet
        doc, _report = build_view_sheet(parts, title.upper(), source='%s (Fusion)' % title)
    else:
        doc = None
        doc = execute(doc, 'add_sheet', {'id': 's1', 'name': 'Sheet 1'})['document']
        doc = execute(doc, 'set_title', {'field': 'title', 'value': title.upper()})['document']
        doc = execute(doc, 'set_title', {'field': 'source', 'value': '%s (Fusion)' % title})['document']
        for vid, label, x, y, w, h in _VIEWS:
            doc = execute(doc, 'place_view', {
                'id': vid, 'sheet': 's1', 'x': x, 'y': y, 'w': w, 'h': h, 'label': label,
            })['document']
    project = company_project(occurrences.get('company') or '', occurrences.get('project') or '')
    doc = execute(doc, 'set_title', {'field': 'project', 'value': project})['document']
    rows = component_rows(occurrences)
    if rows:
        doc = execute(doc, 'load_bom_components', {'components': rows, 'replace': True})['document']
        doc = execute(doc, 'place_bom', {'id': 'bom', 'sheet': 's1', 'anchor': 'bottom_left'})['document']
    return doc


def _parts(out_dir):
    names = os.listdir(out_dir)
    if not any(name.startswith('mesh_') and name.endswith('.bin') for name in names):
        return []
    from sheet2d.meshparts import load_fusion_dump
    parts, _info = load_fusion_dump(out_dir)
    return parts


def write_outputs(out_dir, doc):
    """(json path, pdf path)."""
    json_path = os.path.join(out_dir, 'drawing.json')
    pdf_path = os.path.join(out_dir, 'sheet.pdf')
    with open(json_path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(doc, handle, indent=1)
        handle.write('\n')
    export_pdf(DrawingDocument.from_dict(doc), pdf_path)
    return json_path, pdf_path


def launch_editor(json_path, popen=None):
    """Start the local editor on this drawing. Returns the process, or None."""
    script = editor_script()
    if script is None:
        return None
    popen = popen or subprocess.Popen
    return popen([sys.executable, script, '--drawing', json_path])


def generate(out_dir, open_editor=False, popen=None):
    """Write drawing.json and sheet.pdf. Open the editor when asked. Do not wait."""
    doc = build_drawing(out_dir)
    json_path, pdf_path = write_outputs(out_dir, doc)
    editor = launch_editor(json_path, popen) if open_editor else None
    return {'json': json_path, 'pdf': pdf_path, 'editor': editor, 'project': doc['properties'].get('project') or ''}


def main(argv):
    if len(argv) != 2:
        print('usage: python generate_sheet.py READ_FOLDER')
        return 2
    generate(argv[1], open_editor=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
