"""Single supported forward model for the Watercolour Effect.

A fixed internal edge/diffusion reference estimates colour/luminance shift
direction. A calibrated scalar geometry term then scales that shift in
visual-angle units.

The public model is deliberately restricted to the encoded psychophysical
domain: adjacent, visibly wavy double contours. CIE 1976 u'v' chromatic
displacement is reported as the chromatic WCE score, with relative luminance
shift reported separately. No unified perceptual Delta E is claimed because
the uncalibrated filling-in model can predict appearances outside display gamut.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from scipy.ndimage import distance_transform_edt

from colourshift.watercolour._edge_model import (
    EdgeModelConfig,
    opponent_to_rgb,
    rgb_to_opponent,
    run_edge_model,
)
from colourshift.watercolour.colourimetry import sRGB_to_uvY
from colourshift.watercolour.global_form import geometry_gain
from colourshift.watercolour.published import (
    DEVINCK_2014_INNER_OUTER_RATIOS,
    DEVINCK_2014_SIZE_DIAMETERS_DEG,
    DEVINCK_2014_TOTAL_WIDTHS_ARCMIN,
    GERARDIN_2014_FREQUENCIES_CPR,
)
from colourshift.watercolour.stimuli import StarWatercolourStimulus, star_masks

RGB: TypeAlias = tuple[float, float, float]

_MIN_TOTAL_WIDTH_ARCMIN = min(DEVINCK_2014_TOTAL_WIDTHS_ARCMIN)
_MAX_TOTAL_WIDTH_ARCMIN = max(DEVINCK_2014_TOTAL_WIDTHS_ARCMIN)
_MIN_WIDTH_RATIO = min(DEVINCK_2014_INNER_OUTER_RATIOS)
_MAX_WIDTH_RATIO = max(DEVINCK_2014_INNER_OUTER_RATIOS)
_MIN_DIAMETER_DEG = min(DEVINCK_2014_SIZE_DIAMETERS_DEG)
_MAX_DIAMETER_DEG = max(DEVINCK_2014_SIZE_DIAMETERS_DEG)
_MIN_FREQUENCY_CPR = min(GERARDIN_2014_FREQUENCIES_CPR)
_MAX_FREQUENCY_CPR = max(GERARDIN_2014_FREQUENCIES_CPR)


def _finite_rgb(name: str, rgb: RGB) -> np.ndarray:
    values = np.asarray(rgb, dtype=float)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain three finite values")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError(f"{name} must contain sRGB values in [0, 1]")
    return values


@dataclass(frozen=True)
class WatercolourGeometry:
    inner_width_arcmin: float = 7.5
    outer_width_arcmin: float = 7.5
    diameter_deg: float = 3.2
    frequency_cpr: float = 12.0

    def __post_init__(self) -> None:
        values = (
            self.inner_width_arcmin,
            self.outer_width_arcmin,
            self.diameter_deg,
            self.frequency_cpr,
        )
        if any(not np.isfinite(value) or value <= 0 for value in values):
            raise ValueError("geometry values must be finite and positive")

        total_width = self.inner_width_arcmin + self.outer_width_arcmin
        if not _MIN_TOTAL_WIDTH_ARCMIN <= total_width <= _MAX_TOTAL_WIDTH_ARCMIN:
            raise ValueError(
                f"total contour width must be in "
                f"[{_MIN_TOTAL_WIDTH_ARCMIN}, {_MAX_TOTAL_WIDTH_ARCMIN}] arcmin"
            )
        ratio = self.inner_width_arcmin / self.outer_width_arcmin
        if not _MIN_WIDTH_RATIO <= ratio <= _MAX_WIDTH_RATIO:
            raise ValueError(
                f"inner:outer width ratio must be in [{_MIN_WIDTH_RATIO}, {_MAX_WIDTH_RATIO}]"
            )
        if not _MIN_DIAMETER_DEG <= self.diameter_deg <= _MAX_DIAMETER_DEG:
            raise ValueError(
                f"diameter must be in [{_MIN_DIAMETER_DEG}, {_MAX_DIAMETER_DEG}] degrees"
            )
        if not _MIN_FREQUENCY_CPR <= self.frequency_cpr <= _MAX_FREQUENCY_CPR:
            raise ValueError(
                f"frequency must be in [{_MIN_FREQUENCY_CPR}, {_MAX_FREQUENCY_CPR}] cpr"
            )


@dataclass(frozen=True)
class _ColourDriveReference:
    size_px: int = 256
    outer_radius_px: float = 76.0
    inner_radius_ratio: float = 0.62
    points: int = 7
    inner_width_px: float = 4.0
    outer_width_px: float = 4.0
    inset_px: float = 12.0


@dataclass(frozen=True)
class WatercolourPrediction:
    geometry: WatercolourGeometry
    geometry_gain: float
    predicted_rgb_unclipped: tuple[float, float, float]
    chromatic_shift_uv: float
    relative_luminance_shift: float
    opponent_shift: tuple[float, float, float]


def _reference_masks(reference: _ColourDriveReference):
    placeholder = StarWatercolourStimulus(
        size_px=reference.size_px,
        outer_radius_px=reference.outer_radius_px,
        inner_radius_ratio=reference.inner_radius_ratio,
        points=reference.points,
        inner_width_px=reference.inner_width_px,
        outer_width_px=reference.outer_width_px,
    )
    return star_masks(placeholder)


def _extract_colour_drive(
    *,
    field_rgb: np.ndarray,
    inner_rgb: np.ndarray,
    outer_rgb: np.ndarray,
    background_rgb: np.ndarray,
    reference: _ColourDriveReference,
) -> tuple[np.ndarray, np.ndarray]:
    masks = _reference_masks(reference)
    image = np.empty((reference.size_px, reference.size_px, 3), dtype=float)
    image[:] = background_rgb
    image[masks.field] = field_rgb
    image[masks.inner] = inner_rgb
    image[masks.gap] = field_rgb
    image[masks.outer] = outer_rgb

    config = EdgeModelConfig(opponent_transform="van_de_sande")
    result = run_edge_model(image, config)
    deep_interior = masks.field & (distance_transform_edt(masks.field) >= reference.inset_px)
    if not np.any(deep_interior):
        raise ValueError("internal colour-drive reference has no interior pixels")
    predicted = np.mean(result.opponent_prediction[deep_interior], axis=0)
    physical = rgb_to_opponent(field_rgb.reshape(1, 1, 3), config.opponent_transform)[0, 0]
    return physical, predicted - physical


def predict_watercolour(
    *,
    field_rgb: RGB,
    inner_rgb: RGB,
    outer_rgb: RGB,
    geometry: WatercolourGeometry | None = None,
    background_rgb: RGB | None = None,
) -> WatercolourPrediction:
    geometry = geometry or WatercolourGeometry()
    field = _finite_rgb("field_rgb", field_rgb)
    inner = _finite_rgb("inner_rgb", inner_rgb)
    outer = _finite_rgb("outer_rgb", outer_rgb)
    background = (
        field.copy() if background_rgb is None else _finite_rgb("background_rgb", background_rgb)
    )
    physical_opponent, colour_drive = _extract_colour_drive(
        field_rgb=field,
        inner_rgb=inner,
        outer_rgb=outer,
        background_rgb=background,
        reference=_ColourDriveReference(),
    )
    gain = geometry_gain(
        inner_width_arcmin=geometry.inner_width_arcmin,
        outer_width_arcmin=geometry.outer_width_arcmin,
        diameter_deg=geometry.diameter_deg,
        frequency_cpr=geometry.frequency_cpr,
    )
    final_shift = gain * colour_drive
    predicted_opponent = physical_opponent + final_shift
    predicted_rgb = opponent_to_rgb(predicted_opponent.reshape(1, 1, 3), "van_de_sande")[0, 0]

    field_uv, field_y = sRGB_to_uvY(field)
    predicted_uv, predicted_y = sRGB_to_uvY(predicted_rgb)

    return WatercolourPrediction(
        geometry=geometry,
        geometry_gain=float(gain),
        predicted_rgb_unclipped=tuple(float(value) for value in predicted_rgb),
        chromatic_shift_uv=float(np.linalg.norm(predicted_uv - field_uv)),
        relative_luminance_shift=float(predicted_y - field_y),
        opponent_shift=tuple(float(value) for value in final_shift),
    )
