import math
from types import SimpleNamespace

import numpy as np
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
    for result in results:
        assert isinstance(result, algorithms.ColourShiftResult)
        assert len(result.rgb) == 3
        assert all(0.0 <= channel <= 1.0 for channel in result.rgb)
        assert math.isfinite(result.delta_e)


@pytest.mark.parametrize("fixed_as_base", [True, False])
def test_find_extreme_shift_colors_returns_finite_candidates(fixed_as_base):
    config = Config(rgb_grid_points=2, min_delta=0.0, max_candidates=2)

    results = algorithms.find_extreme_shift_colors(
        [0.59, 0.26, 0.0],
        fixed_as_base=fixed_as_base,
        config=config,
    )

    assert 1 <= len(results) <= 2
    for result in results:
        assert isinstance(result, algorithms.ColourShiftResult)
        assert len(result.rgb) == 3
        assert all(0.0 <= channel <= 1.0 for channel in result.rgb)
        assert math.isfinite(result.delta_e)


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


def test_legacy_engine_preserves_historical_positional_parameter_mapping(monkeypatch):
    captured = {}

    def fake_ciecam02(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(J=50.0, M=20.0, h=30.0)

    monkeypatch.setattr(algorithms, "XYZ_to_CIECAM02", fake_ciecam02)
    monkeypatch.setattr(algorithms, "JMh_CIECAM02_to_CAM02UCS", np.asarray)

    config = Config(background_luminance=12.0, adapting_luminance=34.0)
    algorithms._cam02_ucs((1.0, 2.0, 3.0), (4.0, 5.0, 6.0), config)

    assert captured["args"][:2] == ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert captured["args"][2:] == (12.0, 34.0)
    assert set(captured["kwargs"]) == {"surround"}


def test_corrected_engine_maps_config_to_explicit_ciecam02_parameters(monkeypatch):
    captured = {}

    def fake_ciecam02(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(J=50.0, M=20.0, h=30.0)

    monkeypatch.setattr(algorithms, "XYZ_to_CIECAM02", fake_ciecam02)
    monkeypatch.setattr(algorithms, "JMh_CIECAM02_to_CAM02UCS", np.asarray)

    config = Config(background_luminance=12.0, adapting_luminance=34.0)
    algorithms._cam02_ucs_corrected(
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
        config,
    )

    assert captured["XYZ"] == (1.0, 2.0, 3.0)
    assert captured["XYZ_w"] == (4.0, 5.0, 6.0)
    assert captured["L_A"] == 34.0
    assert captured["Y_b"] == 12.0
    assert captured["surround"] is algorithms._viewing_condition(config)


def test_chromatic_objective_changes_candidate_ranking(monkeypatch):
    reference_surround = (0.5, 0.5, 0.5)
    high_total = (1.0, 0.0, 0.0)
    high_chromatic = (0.0, 1.0, 0.0)
    appearances = {
        reference_surround: np.asarray((0.0, 0.0, 0.0)),
        high_total: np.asarray((10.0, 0.0, 1.0)),
        high_chromatic: np.asarray((0.0, 2.0, 0.0)),
    }

    monkeypatch.setattr(algorithms, "rgb_to_XYZ", lambda rgb: tuple(rgb))
    monkeypatch.setattr(
        algorithms,
        "_rgb_grid",
        lambda _points: [list(high_total), list(high_chromatic)],
    )
    monkeypatch.setattr(
        algorithms,
        "_appearance_function",
        lambda _engine: lambda _stimulus, surround, _config: appearances[tuple(surround)],
    )

    config = Config(rgb_grid_points=2, min_delta=0.0, max_candidates=1)
    total = algorithms.compute_appearance_difference(
        (0.2, 0.2, 0.2),
        reference_surround,
        config=config,
        objective=algorithms.OBJECTIVE_TOTAL,
    )
    chromatic = algorithms.compute_appearance_difference(
        (0.2, 0.2, 0.2),
        reference_surround,
        config=config,
        objective=algorithms.OBJECTIVE_CHROMATIC,
    )

    assert total[0].rgb == list(high_total)
    assert chromatic[0].rgb == list(high_chromatic)
    assert chromatic[0].delta_e == pytest.approx(2.0)
    assert chromatic[0].chromatic_delta == pytest.approx(2.0)


def test_compare_appearance_engines_labels_each_result_group(monkeypatch):
    candidate = algorithms.ColourShiftResult(
        rgb=[0.1, 0.2, 0.3],
        delta_e=4.0,
        chromatic_delta=3.0,
    )
    calls = []

    def fake_compute(*args, **kwargs):
        calls.append(kwargs)
        return [candidate]

    monkeypatch.setattr(algorithms, "compute_appearance_difference", fake_compute)

    groups = algorithms.compare_appearance_engines(
        (0.4, 0.5, 0.6),
        (0.7, 0.8, 0.9),
        objective=algorithms.OBJECTIVE_CHROMATIC,
    )

    assert [group.engine for group in groups] == [
        algorithms.ENGINE_LEGACY,
        algorithms.ENGINE_CORRECTED,
    ]
    assert all(group.objective == algorithms.OBJECTIVE_CHROMATIC for group in groups)
    assert all(group.candidates == [candidate] for group in groups)
    assert [call["engine"] for call in calls] == [
        algorithms.ENGINE_LEGACY,
        algorithms.ENGINE_CORRECTED,
    ]


def test_chromatic_filter_rejects_candidates_separated_only_by_lightness():
    candidates = [
        ([1.0, 0.0, 0.0], 30.0, np.asarray((0.0, 0.0, 0.0))),
        ([0.0, 1.0, 0.0], 29.0, np.asarray((100.0, 1.0, 1.0))),
        ([0.0, 0.0, 1.0], 28.0, np.asarray((0.0, 20.0, 0.0))),
    ]

    total = algorithms._filter_separated_candidates(
        candidates,
        min_delta=10.0,
        max_candidates=2,
        objective=algorithms.OBJECTIVE_TOTAL,
    )
    chromatic = algorithms._filter_separated_candidates(
        candidates,
        min_delta=10.0,
        max_candidates=2,
        objective=algorithms.OBJECTIVE_CHROMATIC,
    )

    assert [item[0] for item in total] == [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    assert [item[0] for item in chromatic] == [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ]


def test_compare_extreme_shift_engines_propagates_engine_and_objective(monkeypatch):
    candidate = algorithms.ColourShiftResult(
        rgb=[0.1, 0.2, 0.3],
        delta_e=4.0,
        chromatic_delta=3.0,
    )
    calls = []

    def fake_find(*args, **kwargs):
        calls.append((args, kwargs))
        return [candidate]

    monkeypatch.setattr(algorithms, "find_extreme_shift_colors", fake_find)

    groups = algorithms.compare_extreme_shift_engines(
        (0.4, 0.5, 0.6),
        fixed_as_base=True,
        objective=algorithms.OBJECTIVE_CHROMATIC,
    )

    assert [group.engine for group in groups] == [
        algorithms.ENGINE_LEGACY,
        algorithms.ENGINE_CORRECTED,
    ]
    assert all(group.objective == algorithms.OBJECTIVE_CHROMATIC for group in groups)
    assert all(args[1] is True for args, _kwargs in calls)
    assert [kwargs["engine"] for _args, kwargs in calls] == [
        algorithms.ENGINE_LEGACY,
        algorithms.ENGINE_CORRECTED,
    ]
    assert all(kwargs["objective"] == algorithms.OBJECTIVE_CHROMATIC for _args, kwargs in calls)
