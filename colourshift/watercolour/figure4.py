"""Quantitative reproduction of Cohen-Duwek & Spitzer (2019), Figure 4.

The 2019 paper converts Devinck et al. (2005) CIE Lu'v' stimulus colours to
sRGB, applies the WCE model, then converts predictions back to CIE Lu'v'.
Two implementation details are not specified: gamut clipping and chromatic
adaptation of the experimental white to sRGB D65.  This module exposes those
choices and reports sensitivity rather than fitting them.

The canonical reproduction uses direct *extended* sRGB (no clipping, no
chromatic adaptation).  Out-of-gamut components are retained as floating point
model inputs; only exported display images should ever be clipped.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from ._edge_model import EdgeModelConfig, opponent_to_rgb, run_edge_model
from .colourimetry import (
    SRGBConversionPolicy,
    is_unit_gamut,
    sRGB_to_uvY,
    uvY_to_sRGB,
)
from .published import (
    DEVINCK_2005_BACKGROUND_LUMINANCE,
    DEVINCK_2005_CHROMATICITIES,
    DEVINCK_2005_EFFECTS,
    DEVINCK_2005_INNER_LUMINANCE,
    DEVINCK_2005_OUTER_LUMINANCE,
)
from .stimuli import StarWatercolourStimulus, star_masks


@dataclass(frozen=True)
class Figure4Geometry:
    """Representative star geometry; exact Figure 4 raster was not published."""

    size_px: int = 256
    outer_radius_px: float = 76.0
    inner_radius_ratio: float = 0.62
    points: int = 7
    inner_width_px: float = 4.0
    outer_width_px: float = 4.0
    inset_px: float = 12.0


@dataclass(frozen=True)
class Figure4Measurement:
    inner_colour: str
    outer_colour: str
    conversion_policy: str
    inner_rgb: tuple[float, float, float]
    outer_rgb: tuple[float, float, float]
    background_rgb: tuple[float, float, float]
    inner_in_unit_gamut: bool
    outer_in_unit_gamut: bool
    background_in_unit_gamut: bool
    predicted_u_prime: float
    predicted_v_prime: float
    predicted_relative_Y: float
    predicted_shift_ratio: float
    predicted_angle_difference_deg: float
    published_shift_ratio: float
    published_angle_difference_deg: float
    shift_ratio_error: float
    angle_difference_error_deg: float


FIGURE4_CONDITIONS: tuple[tuple[str, str], ...] = (
    ("orange", "purple"),
    ("purple", "orange"),
    ("red", "green"),
    ("green", "red"),
    ("yellow", "blue"),
    ("blue", "yellow"),
)


def _source_white_uv() -> tuple[float, float]:
    white = DEVINCK_2005_CHROMATICITIES["white"]
    return white.u_prime, white.v_prime


def _published_rgb(
    colour: str,
    luminance: float,
    policy: SRGBConversionPolicy,
) -> np.ndarray:
    chromaticity = DEVINCK_2005_CHROMATICITIES[colour]
    relative_Y = luminance / DEVINCK_2005_BACKGROUND_LUMINANCE
    return uvY_to_sRGB(
        chromaticity.u_prime,
        chromaticity.v_prime,
        relative_Y,
        source_white_uv=_source_white_uv(),
        policy=policy,
    )


def _geometry_masks(geometry: Figure4Geometry):
    placeholder = StarWatercolourStimulus(
        size_px=geometry.size_px,
        outer_radius_px=geometry.outer_radius_px,
        inner_radius_ratio=geometry.inner_radius_ratio,
        points=geometry.points,
        inner_width_px=geometry.inner_width_px,
        outer_width_px=geometry.outer_width_px,
    )
    return star_masks(placeholder)


def _render_extended_stimulus(
    inner_colour: str,
    outer_colour: str,
    geometry: Figure4Geometry,
    policy: SRGBConversionPolicy,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Render model input without forcing extended-sRGB values into [0, 1]."""
    inner_rgb = _published_rgb(inner_colour, DEVINCK_2005_INNER_LUMINANCE, policy)
    outer_rgb = _published_rgb(outer_colour, DEVINCK_2005_OUTER_LUMINANCE, policy)
    background_rgb = _published_rgb("white", DEVINCK_2005_BACKGROUND_LUMINANCE, policy)

    masks = _geometry_masks(geometry)
    image = np.empty((geometry.size_px, geometry.size_px, 3), dtype=float)
    image[:] = background_rgb
    image[masks.inner] = inner_rgb
    image[masks.outer] = outer_rgb
    # Field and any zero-width gap are the same physical white as background.
    image[masks.field] = background_rgb
    image[masks.gap] = background_rgb
    return image, inner_rgb, outer_rgb, background_rgb


def _angle_deg(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    norm = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if norm <= np.finfo(float).eps:
        return float("nan")
    cosine = float(np.dot(vector_a, vector_b) / norm)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def evaluate_figure4_condition(
    inner_colour: str,
    outer_colour: str,
    *,
    geometry: Figure4Geometry | None = None,
    conversion_policy: SRGBConversionPolicy | None = None,
    model_config: EdgeModelConfig | None = None,
) -> Figure4Measurement:
    """Run one Figure 4 colour pair and compare with Devinck's mean vector."""
    if inner_colour not in DEVINCK_2005_EFFECTS:
        raise ValueError(f"unknown inducing colour: {inner_colour!r}")
    if outer_colour not in DEVINCK_2005_CHROMATICITIES:
        raise ValueError(f"unknown outer colour: {outer_colour!r}")

    geometry = geometry or Figure4Geometry()
    conversion_policy = conversion_policy or SRGBConversionPolicy()
    model_config = model_config or EdgeModelConfig(opponent_transform="van_de_sande")

    image, inner_rgb, outer_rgb, background_rgb = _render_extended_stimulus(
        inner_colour, outer_colour, geometry, conversion_policy
    )
    result = run_edge_model(image, model_config)
    masks = _geometry_masks(geometry)
    deep_interior = masks.field & (distance_transform_edt(masks.field) >= geometry.inset_px)
    if not np.any(deep_interior):
        raise ValueError("Figure 4 geometry leaves no deep interior pixels")

    # Use the un-clipped opponent prediction. result.predicted_rgb is intended
    # for display and clips to [0, 1], which would silently alter Figure 4.
    predicted_opponent = np.mean(result.opponent_prediction[deep_interior], axis=0)
    predicted_rgb = opponent_to_rgb(
        predicted_opponent.reshape(1, 1, 3),
        model_config.opponent_transform,
    )[0, 0]
    predicted_uv, predicted_Y = sRGB_to_uvY(
        predicted_rgb,
        source_white_uv=_source_white_uv(),
        policy=conversion_policy,
    )

    white = DEVINCK_2005_CHROMATICITIES["white"]
    inner = DEVINCK_2005_CHROMATICITIES[inner_colour]
    white_uv = np.array([white.u_prime, white.v_prime], dtype=float)
    inner_uv = np.array([inner.u_prime, inner.v_prime], dtype=float)
    predicted_shift = predicted_uv - white_uv
    inducing_vector = inner_uv - white_uv

    predicted_shift_ratio = float(np.linalg.norm(predicted_shift) / np.linalg.norm(inducing_vector))
    predicted_angle = _angle_deg(predicted_shift, inducing_vector)
    published = DEVINCK_2005_EFFECTS[inner_colour]

    return Figure4Measurement(
        inner_colour=inner_colour,
        outer_colour=outer_colour,
        conversion_policy=conversion_policy.name,
        inner_rgb=tuple(float(v) for v in inner_rgb),
        outer_rgb=tuple(float(v) for v in outer_rgb),
        background_rgb=tuple(float(v) for v in background_rgb),
        inner_in_unit_gamut=is_unit_gamut(inner_rgb),
        outer_in_unit_gamut=is_unit_gamut(outer_rgb),
        background_in_unit_gamut=is_unit_gamut(background_rgb),
        predicted_u_prime=float(predicted_uv[0]),
        predicted_v_prime=float(predicted_uv[1]),
        predicted_relative_Y=float(predicted_Y),
        predicted_shift_ratio=predicted_shift_ratio,
        predicted_angle_difference_deg=predicted_angle,
        published_shift_ratio=published.shift_ratio,
        published_angle_difference_deg=published.angle_difference_deg,
        shift_ratio_error=predicted_shift_ratio - published.shift_ratio,
        angle_difference_error_deg=predicted_angle - published.angle_difference_deg,
    )


def reproduce_figure4(
    *,
    geometry: Figure4Geometry | None = None,
    conversion_policy: SRGBConversionPolicy | None = None,
    model_config: EdgeModelConfig | None = None,
) -> list[Figure4Measurement]:
    """Evaluate all six reversed colour-pair conditions from Figure 4."""
    return [
        evaluate_figure4_condition(
            inner,
            outer,
            geometry=geometry,
            conversion_policy=conversion_policy,
            model_config=model_config,
        )
        for inner, outer in FIGURE4_CONDITIONS
    ]


def conversion_sensitivity_audit(
    geometry: Figure4Geometry | None = None,
    model_config: EdgeModelConfig | None = None,
) -> dict[str, list[Figure4Measurement]]:
    """Run all four plausible clipping/adaptation conventions."""
    policies = (
        SRGBConversionPolicy(False, False),
        SRGBConversionPolicy(False, True),
        SRGBConversionPolicy(True, False),
        SRGBConversionPolicy(True, True),
    )
    return {
        policy.name: reproduce_figure4(
            geometry=geometry,
            conversion_policy=policy,
            model_config=model_config,
        )
        for policy in policies
    }


def write_figure4_report(
    output_dir: str | Path,
    *,
    geometry: Figure4Geometry | None = None,
    model_config: EdgeModelConfig | None = None,
) -> Path:
    """Write canonical results plus gamut/conversion sensitivity as JSON."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    geometry = geometry or Figure4Geometry()
    model_config = model_config or EdgeModelConfig(opponent_transform="van_de_sande")

    canonical_policy = SRGBConversionPolicy(False, False)
    canonical = reproduce_figure4(
        geometry=geometry,
        conversion_policy=canonical_policy,
        model_config=model_config,
    )
    sensitivity = conversion_sensitivity_audit(geometry, model_config)

    non_orange = [item for item in canonical if item.inner_colour not in {"orange"}]
    report = {
        "source": "Cohen-Duwek & Spitzer (2019), Figure 4; Devinck et al. (2005)",
        "scope": "quantitative u'v' reproduction with explicit conversion ambiguity",
        "canonical_conversion_policy": canonical_policy.name,
        "canonical_policy_rationale": (
            "Direct extended sRGB preserves the published u'v'Y coordinates "
            "without undocumented clipping or white-point adaptation."
        ),
        "exact_figure4_raster_published": False,
        "geometry": asdict(geometry),
        "model": asdict(model_config),
        "canonical_measurements": [asdict(item) for item in canonical],
        "sensitivity": {
            name: [asdict(item) for item in measurements]
            for name, measurements in sensitivity.items()
        },
        "summary": {
            "canonical_max_angle_excluding_orange_deg": max(
                item.predicted_angle_difference_deg for item in non_orange
            ),
            "canonical_orange_angle_deg": next(
                item.predicted_angle_difference_deg
                for item in canonical
                if item.inner_colour == "orange"
            ),
            "canonical_predicted_shift_ratio_range": [
                min(item.predicted_shift_ratio for item in canonical),
                max(item.predicted_shift_ratio for item in canonical),
            ],
            "published_shift_ratio_range": [
                min(item.published_shift_ratio for item in canonical),
                max(item.published_shift_ratio for item in canonical),
            ],
        },
    }

    report_path = output / "figure4_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path
