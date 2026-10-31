from types import SimpleNamespace

import numpy as np
import pytest

import colourshift.watercolour.optimise as optimise_module
from colourshift.watercolour.global_form import geometry_gain
from colourshift.watercolour.model import (
    WatercolourGeometry,
    WatercolourPrediction,
    predict_watercolour,
)
from colourshift.watercolour.optimise import (
    WatercolourOptimisationConfig,
    optimal_watercolour_geometry,
    optimise_watercolour,
)


def _prediction(geometry, score=0.25):
    return WatercolourPrediction(
        geometry=geometry,
        geometry_gain=1.0,
        predicted_rgb_unclipped=(0.4, 0.5, 0.6),
        chromatic_shift_uv=score,
        relative_luminance_shift=0.02,
        opponent_shift=(0.01, 0.02, 0.03),
    )


def test_optimal_geometry_is_canonical_calibrated_maximum():
    geometry = optimal_watercolour_geometry()
    assert geometry == WatercolourGeometry(
        inner_width_arcmin=7.5,
        outer_width_arcmin=7.5,
        diameter_deg=3.2,
        frequency_cpr=12.0,
    )
    assert geometry_gain(
        inner_width_arcmin=geometry.inner_width_arcmin,
        outer_width_arcmin=geometry.outer_width_arcmin,
        diameter_deg=geometry.diameter_deg,
        frequency_cpr=geometry.frequency_cpr,
    ) == pytest.approx(1.0)


def test_optimiser_decodes_candidate_and_propagates_configuration(monkeypatch):
    candidate = np.asarray((0.1, 0.2, 0.3, 0.7, 0.8, 0.9))
    geometry = WatercolourGeometry(frequency_cpr=16.0)
    calls = []

    def fake_predict(**kwargs):
        calls.append(kwargs)
        score = 0.42 if kwargs["inner_rgb"] == (0.1, 0.2, 0.3) else 0.1
        return _prediction(kwargs["geometry"], score=score)

    def fake_differential_evolution(objective, bounds, **kwargs):
        assert bounds == [(0.0, 1.0)] * 6
        assert objective(candidate) == pytest.approx(-0.42)
        assert kwargs == {
            "seed": 7,
            "popsize": 5,
            "maxiter": 3,
            "tol": 2e-4,
            "polish": False,
            "updating": "immediate",
            "workers": 1,
        }
        return SimpleNamespace(
            x=candidate,
            nfev=19,
            success=True,
            message="converged",
        )

    monkeypatch.setattr(optimise_module, "predict_watercolour", fake_predict)
    monkeypatch.setattr(optimise_module, "differential_evolution", fake_differential_evolution)

    result = optimise_watercolour(
        field_rgb=(0.9, 0.8, 0.7),
        background_rgb=(0.2, 0.3, 0.4),
        geometry=geometry,
        config=WatercolourOptimisationConfig(
            seed=7,
            popsize=5,
            maxiter=3,
            tol=2e-4,
            polish=False,
        ),
    )

    assert result.inner_rgb == (0.1, 0.2, 0.3)
    assert result.outer_rgb == (0.7, 0.8, 0.9)
    assert result.geometry is geometry
    assert result.evaluations == 19
    assert result.nonfinite_evaluations == 0
    assert result.success is True
    assert result.message == "converged"
    assert result.seed == 7
    assert calls[-1]["inner_rgb"] == result.inner_rgb
    assert calls[-1]["outer_rgb"] == result.outer_rgb
    assert calls[-1]["geometry"] is geometry
    assert len(calls) == 3  # preflight, objective, final direct re-evaluation


def test_nonfinite_objective_is_penalised_and_reported(monkeypatch):
    candidate = np.asarray((0.1, 0.2, 0.3, 0.7, 0.8, 0.9))
    calls = 0

    def fake_predict(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return _prediction(kwargs["geometry"], score=float("nan"))
        return _prediction(kwargs["geometry"], score=0.1)

    def fake_differential_evolution(objective, bounds, **kwargs):
        value = objective(candidate)
        assert np.isfinite(value)
        assert value > 0
        return SimpleNamespace(x=candidate, nfev=1, success=False, message="budget")

    monkeypatch.setattr(optimise_module, "predict_watercolour", fake_predict)
    monkeypatch.setattr(optimise_module, "differential_evolution", fake_differential_evolution)

    result = optimise_watercolour(field_rgb=(1.0, 1.0, 1.0))
    assert result.nonfinite_evaluations == 1


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"field_rgb": (1.01, 1.0, 1.0)}, "field_rgb"),
        (
            {
                "field_rgb": (1.0, 1.0, 1.0),
                "background_rgb": (0.5, -0.01, 0.5),
            },
            "background_rgb",
        ),
    ],
)
def test_invalid_static_input_uses_forward_model_validation(kwargs, match):
    with pytest.raises(ValueError, match=match):
        optimise_watercolour(
            **kwargs,
            config=WatercolourOptimisationConfig(maxiter=0, popsize=1, polish=False),
        )


def test_small_budget_real_model_smoke():
    result = optimise_watercolour(
        field_rgb=(1.0, 1.0, 1.0),
        config=WatercolourOptimisationConfig(seed=3, popsize=2, maxiter=1, polish=False),
    )

    assert all(0.0 <= value <= 1.0 for value in result.inner_rgb)
    assert all(0.0 <= value <= 1.0 for value in result.outer_rgb)
    assert isinstance(result.geometry, WatercolourGeometry)
    assert result.background_rgb == result.field_rgb
    assert np.isfinite(result.prediction.chromatic_shift_uv)
    assert result.prediction.chromatic_shift_uv >= 0.0

    direct = predict_watercolour(
        field_rgb=result.field_rgb,
        background_rgb=result.background_rgb,
        inner_rgb=result.inner_rgb,
        outer_rgb=result.outer_rgb,
        geometry=result.geometry,
    )
    assert result.prediction == direct
