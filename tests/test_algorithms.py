import math

import pytest

from colourshift.core import algorithms
from colourshift.core.config import DEFAULT_CONFIG, Config


def test_default_config_preserves_small_search_defaults():
    assert DEFAULT_CONFIG.viewing_condition == "Average"
    assert DEFAULT_CONFIG.background_luminance == 20.0
    assert DEFAULT_CONFIG.adapting_luminance == 64.0
    assert DEFAULT_CONFIG.rgb_grid_points == 12
    assert DEFAULT_CONFIG.min_delta == 10.0
    assert DEFAULT_CONFIG.max_candidates == 3


def test_compute_appearance_difference_returns_finite_candidates():
    config = Config(rgb_grid_points=2, min_delta=0.0, max_candidates=2)

    results = algorithms.compute_appearance_difference(
        [0.58, 0.0, 0.0],
        [0.59, 0.26, 0.0],
        config=config,
    )

    assert 1 <= len(results) <= 2
    for rgb, delta in results:
        assert len(rgb) == 3
        assert all(0.0 <= channel <= 1.0 for channel in rgb)
        assert math.isfinite(delta)


@pytest.mark.parametrize("fixed_as_base", [True, False])
def test_find_extreme_shift_colors_returns_finite_candidates(fixed_as_base):
    config = Config(rgb_grid_points=2, min_delta=0.0, max_candidates=2)

    results = algorithms.find_extreme_shift_colors(
        [0.59, 0.26, 0.0],
        fixed_as_base=fixed_as_base,
        config=config,
    )

    assert 1 <= len(results) <= 2
    for rgb, delta in results:
        assert len(rgb) == 3
        assert all(0.0 <= channel <= 1.0 for channel in rgb)
        assert math.isfinite(delta)


def test_sensitive_base_reference_uses_candidate_base(monkeypatch):
    fixed_surround = (0.2, 0.3, 0.4)
    candidate_base = (0.7, 0.8, 0.9)
    delta_calls = []

    monkeypatch.setattr(algorithms, "_rgb_grid", lambda points: [list(candidate_base)])
    monkeypatch.setattr(algorithms, "rgb_to_XYZ", lambda rgb: tuple(rgb))
    monkeypatch.setattr(
        algorithms,
        "_cam02_ucs",
        lambda stimulus_XYZ, surround_XYZ, config: (tuple(stimulus_XYZ), tuple(surround_XYZ)),
    )

    def fake_delta(left, right):
        delta_calls.append((left, right))
        return 1.0

    monkeypatch.setattr(algorithms, "delta_E_CAM02UCS", fake_delta)

    algorithms.find_extreme_shift_colors(
        list(fixed_surround),
        fixed_as_base=False,
        config=Config(rgb_grid_points=1, min_delta=0.0, max_candidates=1),
    )

    shifted_appearance, reference_appearance = delta_calls[0]
    assert shifted_appearance == (candidate_base, fixed_surround)
    assert reference_appearance == (candidate_base, candidate_base)
