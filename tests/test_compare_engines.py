"""Side-by-side engine report. No STEP file and no Fusion."""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, 'dev'))

from compare_engines import build_report, write_png  # noqa: E402


def test_unavailable_engines_are_recorded_and_the_picture_is_written(tmp_path):
    report, pictures = build_report(str(tmp_path / 'missing.step'))
    assert set(report['engines']) == {'xq', 'fusion'}
    assert 'mesh' not in report['engines']
    assert report['engines']['fusion']['available'] is False
    assert 'Fusion' in report['engines']['fusion']['reason']
    assert report['engines']['xq']['available'] is False or 'cold' in report['engines']['xq']
    png = tmp_path / 'engines.png'
    write_png(str(png), pictures, report['views'])
    data = png.read_bytes()
    assert data.startswith(b'\x89PNG') and len(data) > 100
    # The json shape keeps read time and view time apart when an engine runs.
    sample = {'read_s': 1.0, 'views_s': 2.0, 'total_s': 3.0, 'wall_s': 3.0, 'from_step': True}
    blob = {'engines': {'xq': {'available': True, 'cold': sample, 'cached': dict(sample, from_step=False)}}}
    json.dumps(blob)
