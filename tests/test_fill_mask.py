"""The fastener fill mask matches a plain every-cell test (fast path keeps the same answer)."""
import numpy as np

from vieweng.xq import _fill_holes, _fill_mask


def _reference(tri2, n=64):
    flat = tri2.reshape(-1, 2)
    lo, hi = flat.min(0), flat.max(0)
    cell = float(max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)) / n
    xs = lo[0] + (np.arange(n) + 0.5) * cell
    ys = lo[1] + (np.arange(n) + 0.5) * cell
    xx, yy = np.meshgrid(xs, ys)
    pts = np.stack([xx.ravel(), yy.ravel()], axis=1)
    covered = np.zeros(len(pts), np.uint8)
    for t in tri2:
        v0, v1 = t[2] - t[0], t[1] - t[0]
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12:
            continue
        rel = pts - t[0]
        a = (rel[:, 0] * v1[1] - v1[0] * rel[:, 1]) / den
        b = (v0[0] * rel[:, 1] - rel[:, 0] * v0[1]) / den
        covered[(a >= -1e-6) & (b >= -1e-6) & (a + b <= 1 + 1e-6)] = 1
    return lo, cell, _fill_holes(covered.reshape(n, n))


def test_fill_mask_matches_every_cell_test():
    rng = np.random.default_rng(7)
    for k in range(40):
        m = int(rng.integers(1, 400))
        tri = rng.normal(size=(m, 1, 2)) * rng.uniform(0.1, 5) + rng.normal(size=(m, 3, 2)) * rng.uniform(0.01, 2)
        if k % 5 == 0:
            tri[:3] = tri[:1]
        lo, cell, grid = _fill_mask(tri)
        rlo, rcell, rgrid = _reference(tri)
        assert np.allclose(lo, rlo) and cell == rcell
        assert (grid == rgrid).all()


def test_fill_mask_empty():
    assert _fill_mask(np.zeros((0, 3, 2))) is None
