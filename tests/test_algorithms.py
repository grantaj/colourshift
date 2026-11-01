import math
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import numpy as np
import pytest

from colourshift.core import algorithms
from colourshift.core.config import DEFAULT_CONFIG, Config


def test_default_config_defines_the_numerical_search_contract():
    assert DEFAULT_CONFIG == Config()
    assert DEFAULT_CONFIG.background_luminous_factor == 20.0
    assert DEFAULT_CONFIG.adapting_luminance == 23.0
    assert DEFAULT_CONFIG.rgb_grid_points == 12
    with pytest.raises(FrozenInstanceError):
        DEFAULT_CONFIG.min_delta = 1.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rgb_grid_points": 1},
        {"min_delta": -1},
        {"max_candidates": 0},
        {"adapting_luminance": -1},
        {"background_luminous_factor": -1},
    ],
)
def test_config_rejects_invalid_search_settings(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_model_uses_fixed_d65_white_and_explicit_cam16_parameters(monkeypatch):
    captured = {}

    def fake_cam16(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(J=50.0, M=20.0, h=30.0)

    monkeypatch.setattr(algorithms, "XYZ_to_CAM16", fake_cam16)
    monkeypatch.setattr(algorithms, "JMh_CAM16_to_CAM16UCS", np.asarray)
    monkeypatch.setattr(algorithms, "rgb_to_XYZ", lambda _rgb: np.asarray((0.1, 0.2, 0.3)))
    config = Config(background_luminous_factor=12.0, adapting_luminance=34.0)
    algorithms._cam16_ucs((0.1, 0.2, 0.3), config)

    assert captured["XYZ"] == pytest.approx((10, 20, 30))
    assert captured["XYZ_w"] == pytest.approx(algorithms._d65_white_xyz())
    assert captured["XYZ_w"][1] == pytest.approx(100)
    assert captured["L_A"] == 34.0
    assert captured["Y_b"] == 12.0


def test_empirical_proxy_uses_surround_as_white_point_with_corrected_parameters(monkeypatch):
    captured = {}

    def fake_ciecam02(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(J=50.0, M=20.0, h=30.0)

    monkeypatch.setattr(algorithms, "XYZ_to_CIECAM02", fake_ciecam02)
    monkeypatch.setattr(algorithms, "JMh_CIECAM02_to_CAM02UCS", np.asarray)
    monkeypatch.setattr(algorithms, "rgb_to_XYZ", lambda rgb: rgb)
    config = Config(background_luminous_factor=12.0, adapting_luminance=34.0)

    algorithms._empirical_cam02_ucs((0.1, 0.2, 0.3), (0.4, 0.5, 0.6), config)

    assert captured["XYZ"] == pytest.approx((0.1, 0.2, 0.3))
    assert captured["XYZ_w"] == pytest.approx((0.4, 0.5, 0.6))
    assert captured["L_A"] == 34.0
    assert captured["Y_b"] == 12.0


def test_empirical_proxy_rejects_out_of_domain_ciecam02_correlates(monkeypatch):
    monkeypatch.setattr(
        algorithms,
        "XYZ_to_CIECAM02",
        lambda **_kwargs: SimpleNamespace(J=101.0, M=20.0, h=30.0),
    )
    monkeypatch.setattr(algorithms, "rgb_to_XYZ", lambda rgb: rgb)

    with pytest.raises(ValueError, match="outside the empirical CIECAM02 domain"):
        algorithms._empirical_cam02_ucs(
            (0.1, 0.2, 0.3),
            (0.4, 0.5, 0.6),
            Config(background_luminous_factor=12.0, adapting_luminance=34.0),
        )


def test_published_2019_correction_equations():
    delta = 20.0
    assert algorithms._lightness_contrast_correction(delta) == pytest.approx(
        16.0067 / (0.0837 + np.exp(-0.0240 * delta)) - 13.4455
    )
    assert algorithms._hue_contrast_correction(delta) == pytest.approx(
        0.4408 * delta * np.exp(-0.001 * delta**2)
    )


def test_contrast_coordinates_keep_chroma_and_apply_background_minus_target(monkeypatch):
    target = np.asarray((40.0, 20.0, 0.0))
    brighter_yellow_background = np.asarray((60.0, 0.0, 20.0))
    values = {
        (0.2, 0.2, 0.2): target,
        (0.8, 0.8, 0.2): brighter_yellow_background,
    }
    monkeypatch.setattr(algorithms, "_cam16_ucs", lambda rgb, _config: values[tuple(rgb)])

    predicted = np.asarray(algorithms.appearance_coordinates((0.2, 0.2, 0.2), (0.8, 0.8, 0.2)))
    expected_j = target[0] + algorithms._lightness_contrast_correction(20.0)
    assert predicted[0] == pytest.approx(expected_j)
    assert np.linalg.norm(predicted[1:]) == pytest.approx(np.linalg.norm(target[1:]))
    assert np.arctan2(predicted[2], predicted[1]) > 0


@pytest.mark.parametrize(
    ("operation", "args", "mode", "base", "surround"),
    [
        (
            algorithms.find_maximal_surround_shift,
            ([0.58, 0, 0], [0.59, 0.26, 0]),
            algorithms.MODE_MAXIMAL_SURROUND_SHIFT,
            (0.58, 0.0, 0.0),
            (0.59, 0.26, 0.0),
        ),
        (
            algorithms.find_strongest_surrounds,
            ([0.58, 0, 0],),
            algorithms.MODE_STRONGEST_SURROUNDS,
            (0.58, 0.0, 0.0),
            None,
        ),
        (
            algorithms.find_sensitive_bases,
            ([0.59, 0.26, 0],),
            algorithms.MODE_SENSITIVE_BASES,
            None,
            (0.59, 0.26, 0.0),
        ),
    ],
)
def test_named_searches_return_complete_immutable_snapshots(operation, args, mode, base, surround):
    config = Config(rgb_grid_points=2, min_delta=0, max_candidates=2)
    result = operation(*args, config=config)

    assert result.model == algorithms.MODEL_ID
    assert result.mode == mode
    assert result.config is config
    assert result.base_rgb == base
    assert result.surround_rgb == surround
    assert 1 <= len(result.candidates) <= 2
    assert isinstance(result.candidates, tuple)
    for candidate in result.candidates:
        assert isinstance(candidate, algorithms.ColourShiftCandidate)
        assert all(0 <= channel <= 1 for channel in candidate.rgb)
        assert math.isfinite(candidate.total_shift)
        assert math.isfinite(candidate.chromatic_shift)


def test_sensitive_base_reference_uses_each_candidate_as_its_own_surround(monkeypatch):
    fixed = (0.2, 0.3, 0.4)
    candidate = (0.7, 0.8, 0.9)
    calls = []
    monkeypatch.setattr(algorithms, "_rgb_grid", lambda _points: [candidate])
    monkeypatch.setattr(algorithms, "_viewing_condition", lambda _config: None)

    def fake_appearance(target, background, _config):
        calls.append((target, background))
        return np.asarray((sum(target), background[0], background[1]))

    monkeypatch.setattr(algorithms, "_appearance_array", fake_appearance)
    algorithms.find_sensitive_bases(fixed, config=Config(rgb_grid_points=2, min_delta=0))

    assert calls == [(candidate, fixed), (candidate, candidate)]


def test_chromatic_objective_changes_ranking(monkeypatch):
    initial = (0.5, 0.5, 0.5)
    high_total = (1.0, 0.0, 0.0)
    high_chromatic = (0.0, 1.0, 0.0)
    appearances = {
        initial: np.asarray((0.0, 0.0, 0.0)),
        high_total: np.asarray((10.0, 0.0, 1.0)),
        high_chromatic: np.asarray((0.0, 2.0, 0.0)),
    }
    monkeypatch.setattr(algorithms, "_rgb_grid", lambda _points: [high_total, high_chromatic])
    monkeypatch.setattr(
        algorithms,
        "_appearance_array",
        lambda _target, background, _config: appearances[background],
    )
    config = Config(rgb_grid_points=2, min_delta=0, max_candidates=1)

    total = algorithms.find_maximal_surround_shift((0.2, 0.2, 0.2), initial, config=config)
    chromatic = algorithms.find_maximal_surround_shift(
        (0.2, 0.2, 0.2),
        initial,
        config=config,
        objective=algorithms.OBJECTIVE_CHROMATIC,
    )

    assert total.candidates[0].rgb == high_total
    assert chromatic.candidates[0].rgb == high_chromatic


def test_chromatic_separation_ignores_lightness():
    origin = np.asarray((0.0, 0.0, 0.0))
    mostly_lightness = np.asarray((100.0, 1.0, 1.0))
    assert (
        algorithms._candidate_separation(origin, mostly_lightness, algorithms.OBJECTIVE_TOTAL) > 10
    )
    assert (
        algorithms._candidate_separation(origin, mostly_lightness, algorithms.OBJECTIVE_CHROMATIC)
        < 10
    )


def test_equal_scores_have_deterministic_rgb_order(monkeypatch):
    colours = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    monkeypatch.setattr(algorithms, "_rgb_grid", lambda _points: colours)

    def evaluate(rgb):
        return np.asarray((1.0, 0.0, 0.0)), np.asarray((0.0, 0.0, 0.0))

    selected = algorithms._rank_candidates(
        evaluate, Config(rgb_grid_points=2, min_delta=0, max_candidates=2), "total"
    )
    assert [candidate.rgb for candidate in selected] == sorted(colours)


def test_invalid_objective_is_rejected():
    with pytest.raises(ValueError, match="Unsupported search objective"):
        algorithms.find_strongest_surrounds((0.5, 0.5, 0.5), objective="unknown")


def test_invalid_viewing_condition_is_not_silently_returned_as_no_candidates():
    with pytest.raises(ValueError, match="Unsupported CAM16 viewing condition"):
        algorithms.find_sensitive_bases(
            (0.5, 0.5, 0.5), config=Config(viewing_condition="Unknown", rgb_grid_points=2)
        )


def test_preset_three_maximal_shift_has_candidates():
    result = algorithms.find_maximal_surround_shift(
        (0x32 / 255, 0x6C / 255, 0x36 / 255),
        (0x27 / 255, 0x34 / 255, 0x70 / 255),
        config=Config(rgb_grid_points=3, min_delta=5, max_candidates=3),
    )
    assert result.candidates


def test_paper_example_does_not_collapse_both_objectives_to_dark_surrounds():
    config = Config(rgb_grid_points=3, min_delta=0.5, max_candidates=3)
    base = (0x95 / 255, 0.0, 0.0)
    surround = (0x96 / 255, 0x43 / 255, 0x01 / 255)
    total = algorithms.find_maximal_surround_shift(base, surround, config=config)
    chromatic = algorithms.find_maximal_surround_shift(
        base,
        surround,
        config=config,
        objective=algorithms.OBJECTIVE_CHROMATIC,
    )
    assert total.candidates[0].rgb == (1.0, 1.0, 1.0)
    assert chromatic.candidates[0].rgb == (1.0, 0.0, 0.5)
