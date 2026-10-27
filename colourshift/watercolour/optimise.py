"""Optimisation of Watercolour Effect contour colours.

The optimiser is intentionally a thin orchestration layer around the single
public forward model. Geometry is fixed during colour optimisation; the default
geometry is the calibrated maximum already encoded by the forward model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy.optimize import differential_evolution

from .model import RGB, WatercolourGeometry, WatercolourPrediction, predict_watercolour

_BOUNDS = [(0.0, 1.0)] * 6
_NONFINITE_PENALTY = 1.0e6


@dataclass(frozen=True)
class WatercolourOptimisationConfig:
    """Configuration for the six-channel differential-evolution search."""

    seed: int = 0
    popsize: int = 8
    maxiter: int = 20
    tol: float = 1e-4
    polish: bool = True


@dataclass(frozen=True)
class WatercolourOptimisationResult:
    """Best contour pair found for a fixed field, background and geometry."""

    field_rgb: RGB
    background_rgb: RGB
    inner_rgb: RGB
    outer_rgb: RGB
    geometry: WatercolourGeometry
    prediction: WatercolourPrediction
    evaluations: int
    nonfinite_evaluations: int
    success: bool
    message: str
    seed: int


def optimal_watercolour_geometry() -> WatercolourGeometry:
    """Return the canonical maximum of the calibrated geometry response."""

    return WatercolourGeometry(
        inner_width_arcmin=7.5,
        outer_width_arcmin=7.5,
        diameter_deg=3.2,
        frequency_cpr=12.0,
    )


def _decode_colours(x) -> tuple[RGB, RGB]:
    inner = tuple(float(value) for value in x[:3])
    outer = tuple(float(value) for value in x[3:])
    return cast(RGB, inner), cast(RGB, outer)


def optimise_watercolour(
    *,
    field_rgb: RGB,
    background_rgb: RGB | None = None,
    geometry: WatercolourGeometry | None = None,
    config: WatercolourOptimisationConfig | None = None,
) -> WatercolourOptimisationResult:
    """Find contour colours maximising modelled chromatic WCE shift."""

    geometry = geometry or optimal_watercolour_geometry()
    config = config or WatercolourOptimisationConfig()
    resolved_field = cast(RGB, tuple(float(value) for value in field_rgb))
    resolved_background = (
        resolved_field
        if background_rgb is None
        else cast(RGB, tuple(float(value) for value in background_rgb))
    )

    # Validate static inputs through the authoritative public model before SciPy
    # can wrap a ValueError raised by the objective function.
    predict_watercolour(
        field_rgb=resolved_field,
        background_rgb=resolved_background,
        inner_rgb=(0.0, 0.0, 0.0),
        outer_rgb=(1.0, 1.0, 1.0),
        geometry=geometry,
    )

    nonfinite_evaluations = 0

    def objective(x) -> float:
        nonlocal nonfinite_evaluations
        inner_rgb, outer_rgb = _decode_colours(x)
        prediction = predict_watercolour(
            field_rgb=resolved_field,
            background_rgb=resolved_background,
            inner_rgb=inner_rgb,
            outer_rgb=outer_rgb,
            geometry=geometry,
        )
        score = prediction.chromatic_shift_uv
        if not np.isfinite(score):
            nonfinite_evaluations += 1
            return _NONFINITE_PENALTY
        return -float(score)

    optimum = differential_evolution(
        objective,
        _BOUNDS,
        seed=config.seed,
        popsize=config.popsize,
        maxiter=config.maxiter,
        tol=config.tol,
        polish=config.polish,
        updating="immediate",
        workers=1,
    )
    inner_rgb, outer_rgb = _decode_colours(optimum.x)
    prediction = predict_watercolour(
        field_rgb=resolved_field,
        background_rgb=resolved_background,
        inner_rgb=inner_rgb,
        outer_rgb=outer_rgb,
        geometry=geometry,
    )

    return WatercolourOptimisationResult(
        field_rgb=resolved_field,
        background_rgb=resolved_background,
        inner_rgb=inner_rgb,
        outer_rgb=outer_rgb,
        geometry=geometry,
        prediction=prediction,
        evaluations=int(optimum.nfev),
        nonfinite_evaluations=nonfinite_evaluations,
        success=bool(optimum.success),
        message=str(optimum.message),
        seed=config.seed,
    )
