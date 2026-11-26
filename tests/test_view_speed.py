"""Large-assembly views must finish. Hidden lines are never drawn.

The timed path is the exact-edge engine (XQ), not the retired mesh-line projector.
"""
from sheet2d.project import VIEW_LIMIT_S, build_benchmark_assembly, part_count, project_view


def test_benchmark_assembly_has_several_hundred_parts():
    assert part_count(build_benchmark_assembly()) >= 400


def test_xq_view_set_finishes_within_two_minutes(tmp_path):
    from sheet2d.engines import get_engine
    from vieweng.stepbench import write_benchmark

    step = tmp_path / 'bench.step'
    assert write_benchmark(str(step)) >= 400
    engine = get_engine('xq')
    ok, why = engine.available()
    assert ok, why
    names = ('front', 'top', 'right', 'trimetric')
    views, timing = engine.project_views(names, step=str(step), mode='exact')
    assert timing['total_s'] < VIEW_LIMIT_S, timing
    assert list(views) == list(names)
    for name in names:
        view = views[name]
        assert view['seconds'] < VIEW_LIMIT_S
        assert view['lines']
        assert all(line['style'] != 'hid' for line in view['lines'])
    assert any(line['kind'] == 'circle' for line in views['top']['lines'])


def test_a_round_part_is_not_drawn_as_a_mesh():
    part = [('cyl', 0.0, 0.0, 0.0, 5.0, 12.0, 2)]
    top = project_view(part, 'top')
    assert any(line['kind'] == 'circle' for line in top['lines'])
    assert any(line['style'] == 'ctr' for line in top['lines'])
    assert len(top['lines']) < 8
    side = project_view(part, 'front')
    assert 'hid' not in side['style_counts']
    assert side['style_counts'].get('vis', 0) <= 4
