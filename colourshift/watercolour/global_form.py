"""Calibrated global geometry response used by the WCE model.

Published psychophysical scales anchor the frequency saturation and reference
width/diameter ratio. The reciprocal scale kernel is a modelling hypothesis;
calibration checks for it are not independent validation.
"""

from __future__ import annotations

from .published import (
    DEVINCK_2014_OPTIMAL_TOTAL_WIDTH_ARCMIN,
    DEVINCK_2014_SIZE_DIAMETERS_DEG,
    GERARDIN_2014_FREQUENCY_PLATEAU_CPR,
)
from .spatial_selectivity import paired_contour_gain_arcmin

_CURVATURE_SATURATION_CPR = GERARDIN_2014_FREQUENCY_PLATEAU_CPR
_REFERENCE_TOTAL_WIDTH_ARCMIN = DEVINCK_2014_OPTIMAL_TOTAL_WIDTH_ARCMIN
_REFERENCE_DIAMETER_DEG = DEVINCK_2014_SIZE_DIAMETERS_DEG[1]
_REFERENCE_WIDTH_TO_DIAMETER = (_REFERENCE_TOTAL_WIDTH_ARCMIN / 60.0) / _REFERENCE_DIAMETER_DEG


def curvature_frequency_gain(frequency_cpr: float) -> float:
    if frequency_cpr < 0:
        raise ValueError("frequency_cpr must be non-negative")
    return min(frequency_cpr / _CURVATURE_SATURATION_CPR, 1.0)


def relative_scale_gain(total_width_arcmin: float, diameter_deg: float) -> float:
    if total_width_arcmin <= 0:
        raise ValueError("total_width_arcmin must be positive")
    if diameter_deg <= 0:
        raise ValueError("diameter_deg must be positive")
    ratio = (total_width_arcmin / 60.0) / diameter_deg
    relative = ratio / _REFERENCE_WIDTH_TO_DIAMETER
    return float(2.0 * relative / (1.0 + relative * relative))


def geometry_gain(
    *,
    inner_width_arcmin: float,
    outer_width_arcmin: float,
    diameter_deg: float,
    frequency_cpr: float,
) -> float:
    width_gain = paired_contour_gain_arcmin(
        inner_width_arcmin,
        outer_width_arcmin,
    )
    total_width = inner_width_arcmin + outer_width_arcmin
    return (
        width_gain
        * curvature_frequency_gain(frequency_cpr)
        * relative_scale_gain(total_width, diameter_deg)
    )
