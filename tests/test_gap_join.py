"""Joining silhouette pieces must match the old scan, and stay fast."""
import numpy as np
import math
import random
import time

from sheet2d.engines.curves import bridge_gaps


def _slow(polylines, tol):
    def near(a, b):
        return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol

    unused = [list(p) for p in polylines if len(p) >= 2]
    used = [False] * len(unused)
    out = []
    for i, pts in enumerate(unused):
        if used[i]:
            continue
        used[i] = True
        grew = True
        while grew:
            grew = False
            for j, other in enumerate(unused):
                if used[j]:
                    continue
                if near(pts[-1], other[0]):
                    pts.extend(other[1:])
                elif near(pts[-1], other[-1]):
                    pts.extend(reversed(other[:-1]))
                elif near(pts[0], other[-1]):
                    pts[:0] = other[:-1]
                elif near(pts[0], other[0]):
                    pts[:0] = list(reversed(other[1:]))
                else:
                    continue
                used[j] = True
                grew = True
                break
        if near(pts[0], pts[-1]) and len(pts) > 2:
            pts[-1] = pts[0]
        out.append(pts)
    return out


def test_the_fast_join_matches_the_old_scan_on_random_pieces():
    rng = random.Random(0)
    for _trial in range(50):
        lines = []
        for _k in range(rng.randint(1, 40)):
            x, y = rng.uniform(-20, 20), rng.uniform(-20, 20)
            lines.append([
                (x, y),
                (x + rng.uniform(-2, 2), y + rng.uniform(-2, 2)),
            ])
        # A few pieces that should actually meet.
        if lines:
            end = lines[0][-1]
            lines.append([(end[0] + 0.01, end[1]), (end[0] + 1, end[1] + 1)])
        tol = rng.choice((0.05, 0.2, 1.0))
        assert bridge_gaps(lines, tol) == _slow(lines, tol)


def test_a_long_chain_of_pieces_joins_without_a_quadratic_wait():
    lines = []
    for i in range(4000):
        lines.append([(i * 1.0, 0.0), ((i + 1) * 1.0, 0.0)])
    started = time.perf_counter()
    joined = bridge_gaps(lines, 0.01)
    elapsed = time.perf_counter() - started
    assert len(joined) == 1
    assert joined[0][0] == (0.0, 0.0)
    assert joined[0][-1] == (4000.0, 0.0)
    assert elapsed < 2.0
    assert len(joined[0]) == 4001


def test_many_edges_densify_like_one_edge_at_a_time():
    import sheet2d.engines  # noqa: F401
    from vieweng.xq import _densify, _densify_many
    rng = np.random.default_rng(0)
    chunks = [np.cumsum(rng.normal(size=(rng.integers(2, 6), 3)), axis=0) for _ in range(12)]
    chunks.append(np.array([[0.0, 0.0, 0.0]]))
    dense, counts = _densify_many(chunks, 0.4)
    alone = [_densify(chunk, 0.4) for chunk in chunks]
    assert list(counts) == [len(chunk) for chunk in alone]
    got = np.split(dense, np.cumsum(counts)[:-1])
    for left, right in zip(got, alone):
        assert np.allclose(left, right)


def test_chain_uses_the_first_matching_end():
    import numpy as np
    import sheet2d.engines  # noqa: F401  (loads xq without a circular import)
    from vieweng.xq import _chain

    projected = np.array([
        [[0.0, 0.0], [1.0, 0.0]],
        [[1.0, 0.0], [2.0, 0.0]],
        [[2.0, 0.0], [2.0, 1.0]],
    ])
    segs = np.array([
        [[0.0, 0.0, 10.0], [1.0, 0.0, 11.0]],
        [[1.0, 0.0, 11.0], [2.0, 0.0, 12.0]],
        [[2.0, 0.0, 12.0], [2.0, 1.0, 13.0]],
    ])
    chains = _chain(projected, segs, 1e-6)
    assert len(chains) == 1
    zs = [point[2] for point in chains[0]]
    assert zs == [10.0, 11.0, 12.0, 13.0]
    assert math.isclose(chains[0][-1][1], 1.0)
