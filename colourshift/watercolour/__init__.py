"""Watercolour Effect forward model and contour-colour optimiser."""

from .model import WatercolourGeometry, WatercolourPrediction, predict_watercolour
from .optimise import (
    WatercolourOptimisationConfig,
    WatercolourOptimisationResult,
    optimal_watercolour_geometry,
    optimise_watercolour,
)

__all__ = [
    "WatercolourGeometry",
    "WatercolourOptimisationConfig",
    "WatercolourOptimisationResult",
    "WatercolourPrediction",
    "optimal_watercolour_geometry",
    "optimise_watercolour",
    "predict_watercolour",
]
