"""Calibrated local contour-width response used by the WCE model.

The preferred scale is anchored to the Devinck et al. (2014) 15 arcmin total
double-contour optimum. The odd-Gabor form is a modelling hypothesis, not an
independent validation result.
"""

from __future__ import annotations

from math import exp, pi, sin

import numpy as np
from scipy.integrate import quad

from .published import DEVINCK_2014_OPTIMAL_TOTAL_WIDTH_ARCMIN

_PREFERRED_TOTAL_WIDTH_DEG = DEVINCK_2014_OPTIMAL_TOTAL_WIDTH_ARCMIN / 60.0
_PREFERRED_FREQUENCY_CPD = 1.0 / _PREFERRED_TOTAL_WIDTH_DEG
_PREFERRED_RIBBON_WIDTH_DEG = _PREFERRED_TOTAL_WIDTH_DEG / 2.0
_GAUSSIAN_SIGMA_DEG = _PREFERRED_RIBBON_WIDTH_DEG
_RESPONSE_POWER = 2.0


def _odd_gabor(x_deg: float) -> float:
    carrier = sin(2.0 * pi * _PREFERRED_FREQUENCY_CPD * x_deg)
    envelope = exp(-(x_deg * x_deg) / (2.0 * _GAUSSIAN_SIGMA_DEG**2))
    return carrier * envelope


def _signed_pair_response(inner_width_deg: float, outer_width_deg: float) -> float:
    if inner_width_deg <= 0 or outer_width_deg <= 0:
        raise ValueError("contour widths must be positive")
    inner = quad(
        _odd_gabor,
        -inner_width_deg,
        0.0,
        epsabs=1e-12,
        epsrel=1e-10,
    )[0]
    outer = quad(
        lambda x: -_odd_gabor(x),
        0.0,
        outer_width_deg,
        epsabs=1e-12,
        epsrel=1e-10,
    )[0]
    return abs(inner + outer)


def paired_contour_gain_arcmin(
    inner_width_arcmin: float,
    outer_width_arcmin: float,
) -> float:
    response = _signed_pair_response(
        inner_width_arcmin / 60.0,
        outer_width_arcmin / 60.0,
    )
    reference = _signed_pair_response(
        _PREFERRED_RIBBON_WIDTH_DEG,
        _PREFERRED_RIBBON_WIDTH_DEG,
    )
    if reference <= np.finfo(float).eps:
        raise RuntimeError("spatial-selectivity reference response is zero")
    return float((response / reference) ** _RESPONSE_POWER)
