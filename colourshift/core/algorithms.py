"""Zhu-Luo CAM16 simultaneous-contrast searches.

This implements the final lightness and hue corrections published in Zhu and
Luo (2019), Color and Imaging Conference 27, paper 34. Target and background
colours are converted independently under one fixed D65 CAM16 viewing
condition; the background is never substituted for the adapting white.
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Callable

import numpy as np

from ._colour_warnings import suppress_colour_optional_dependency_warnings
from .colour_models import rgb_to_XYZ
from .config import DEFAULT_CONFIG, Config

suppress_colour_optional_dependency_warnings()

import colour  # noqa: E402
from colour.appearance import XYZ_to_CAM16  # noqa: E402
from colour.models import JMh_CAM16_to_CAM16UCS  # noqa: E402

logger = logging.getLogger(__name__)

MODEL_ID = "zhu-luo-cam16cc-2019-v1"
MODEL_LABEL = "Zhu–Luo CAM16 simultaneous contrast (2019)"
MODEL_DOI = "10.2352/ISSN.2169-2629.2019.27.34"

MODE_MAXIMAL_SURROUND_SHIFT = "maximal-surround-shift"
MODE_STRONGEST_SURROUNDS = "strongest-surrounds"
MODE_SENSITIVE_BASES = "sensitive-bases"
MODES = (
    MODE_MAXIMAL_SURROUND_SHIFT,
    MODE_STRONGEST_SURROUNDS,
    MODE_SENSITIVE_BASES,
)

OBJECTIVE_TOTAL = "total"
OBJECTIVE_CHROMATIC = "chromatic"
OBJECTIVES = (OBJECTIVE_TOTAL, OBJECTIVE_CHROMATIC)

RGB = tuple[float, float, float]


@dataclass(frozen=True)
class ColourShiftCandidate:
    rgb: RGB
    total_shift: float
    chromatic_shift: float


@dataclass(frozen=True)
class SearchResult:
    """An immutable snapshot of one complete search and all its inputs."""

    model: str
    mode: str
    objective: str
    config: Config
    base_rgb: RGB | None
    surround_rgb: RGB | None
    candidates: tuple[ColourShiftCandidate, ...]


@dataclass(frozen=True)
class _RankedCandidate:
    candidate: ColourShiftCandidate
    score: float
    shifted_ucs: np.ndarray


def _settings(config: Config | None) -> Config:
    return config or DEFAULT_CONFIG


def _rgb_tuple(rgb) -> RGB:
    values = tuple(float(channel) for channel in rgb)
    if len(values) != 3 or not all(np.isfinite(values)):
        raise ValueError("RGB values must contain three finite channels")
    if not all(0.0 <= channel <= 1.0 for channel in values):
        raise ValueError("RGB channels must be between 0 and 1")
    return values  # type: ignore[return-value]


def _validate_objective(objective: str) -> None:
    if objective not in OBJECTIVES:
        raise ValueError(f"Unsupported search objective: {objective}")


def _viewing_condition(config: Config):
    try:
        return colour.VIEWING_CONDITIONS_CAM16[config.viewing_condition]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported CAM16 viewing condition: {config.viewing_condition}"
        ) from exc


def _d65_white_xyz() -> np.ndarray:
    xy = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]
    return np.asarray(colour.xy_to_XYZ(xy), dtype=float) * 100.0


def _cam16_ucs(rgb, config: Config) -> np.ndarray:
    """Convert sRGB to CAM16-UCS under a fixed D65 adapting white."""
    xyz = np.asarray(rgb_to_XYZ(_rgb_tuple(rgb)), dtype=float) * 100.0
    spec = XYZ_to_CAM16(
        XYZ=xyz,
        XYZ_w=_d65_white_xyz(),
        L_A=config.adapting_luminance,
        Y_b=config.background_luminous_factor,
        surround=_viewing_condition(config),
    )
    jmh = np.asarray((spec.J, spec.M, spec.h), dtype=float)
    if not np.all(np.isfinite(jmh)) or jmh[0] < 0 or jmh[1] < 0:
        raise ValueError("Colour does not produce finite CAM16 correlates")
    coordinates = np.asarray(JMh_CAM16_to_CAM16UCS(jmh), dtype=float)
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("Colour does not produce finite CAM16-UCS coordinates")
    return coordinates


def cam16_ucs_coordinates(rgb, config: Config | None = None) -> tuple[float, float, float]:
    """Return ordinary CAM16-UCS coordinates under the fixed viewing condition."""
    coordinates = _cam16_ucs(rgb, _settings(config))
    return tuple(float(value) for value in coordinates)  # type: ignore[return-value]


def _lightness_contrast_correction(delta_j_background_minus_target: float) -> float:
    """Equation 1 of the final Zhu-Luo CAM16cc paper, in J' units."""
    delta = float(delta_j_background_minus_target)
    return 16.0067 / (0.0837 + np.exp(-0.0240 * delta)) - 13.4455


def _signed_hue_metric_difference(background_ucs, target_ucs) -> float:
    """Signed CAM16-UCS hue difference from target to background."""
    target = np.asarray(target_ucs, dtype=float)
    background = np.asarray(background_ucs, dtype=float)
    target_chroma = float(np.linalg.norm(target[1:]))
    background_chroma = float(np.linalg.norm(background[1:]))
    if target_chroma == 0.0 or background_chroma == 0.0:
        return 0.0
    target_hue = float(np.arctan2(target[2], target[1]))
    background_hue = float(np.arctan2(background[2], background[1]))
    hue_difference = np.arctan2(
        np.sin(background_hue - target_hue),
        np.cos(background_hue - target_hue),
    )
    return float(2.0 * np.sqrt(target_chroma * background_chroma) * np.sin(hue_difference / 2.0))


def _hue_contrast_correction(delta_h_metric: float) -> float:
    """Equation 3 of the final Zhu-Luo CAM16cc paper, in hue-metric units."""
    delta = float(delta_h_metric)
    return float(0.4408 * delta * np.exp(-0.001 * delta**2))


def _apply_hue_metric_correction(target_ucs, correction: float) -> np.ndarray:
    target = np.asarray(target_ucs, dtype=float)
    chroma = float(np.linalg.norm(target[1:]))
    if chroma <= np.finfo(float).eps or correction == 0.0:
        return target.copy()
    ratio = float(np.clip(correction / (2.0 * chroma), -1.0, 1.0))
    hue_rotation = 2.0 * np.arcsin(ratio)
    hue = np.arctan2(target[2], target[1]) + hue_rotation
    return np.asarray((target[0], chroma * np.cos(hue), chroma * np.sin(hue)))


def appearance_coordinates(
    target_rgb,
    background_rgb,
    config: Config | None = None,
) -> tuple[float, float, float]:
    """Predict target CAM16-UCS appearance under a coloured background."""
    settings = _settings(config)
    target = _cam16_ucs(target_rgb, settings)
    background = _cam16_ucs(background_rgb, settings)

    predicted = target.copy()
    predicted[0] += _lightness_contrast_correction(background[0] - target[0])
    hue_metric = _signed_hue_metric_difference(background, target)
    predicted = _apply_hue_metric_correction(
        predicted,
        _hue_contrast_correction(hue_metric),
    )
    if not np.all(np.isfinite(predicted)):
        raise ValueError("Target and background do not produce a finite prediction")
    return tuple(float(value) for value in predicted)  # type: ignore[return-value]


def _appearance_array(target_rgb, background_rgb, config: Config) -> np.ndarray:
    return np.asarray(appearance_coordinates(target_rgb, background_rgb, config), dtype=float)


def _shift_components(reference_ucs, candidate_ucs) -> tuple[float, float]:
    difference = np.asarray(candidate_ucs, dtype=float) - np.asarray(reference_ucs, dtype=float)
    return float(np.linalg.norm(difference)), float(np.linalg.norm(difference[1:]))


def _rgb_grid(points: int):
    for r in np.linspace(0, 1, points):
        for g in np.linspace(0, 1, points):
            for b in np.linspace(0, 1, points):
                yield (float(r), float(g), float(b))


def _candidate_separation(left_ucs, right_ucs, objective: str) -> float:
    difference = np.asarray(left_ucs, dtype=float) - np.asarray(right_ucs, dtype=float)
    if objective == OBJECTIVE_CHROMATIC:
        difference = difference[1:]
    return float(np.linalg.norm(difference))


def _rank_candidates(
    evaluate: Callable[[RGB], tuple[np.ndarray, np.ndarray] | None],
    config: Config,
    objective: str,
) -> tuple[ColourShiftCandidate, ...]:
    ranked: list[_RankedCandidate] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for rgb in _rgb_grid(config.rgb_grid_points):
            try:
                appearances = evaluate(rgb)
                if appearances is None:
                    continue
                shifted_ucs, reference_ucs = appearances
                total, chromatic = _shift_components(reference_ucs, shifted_ucs)
                score = total if objective == OBJECTIVE_TOTAL else chromatic
                if np.isfinite(score):
                    ranked.append(
                        _RankedCandidate(
                            ColourShiftCandidate(rgb, total, chromatic),
                            score,
                            shifted_ucs,
                        )
                    )
            except (ArithmeticError, ValueError, RuntimeWarning) as exc:
                logger.debug("Skipping invalid candidate %s: %s", rgb, exc)

    ranked.sort(key=lambda item: (-item.score, item.candidate.rgb))
    selected: list[_RankedCandidate] = []
    for item in ranked:
        if all(
            _candidate_separation(item.shifted_ucs, other.shifted_ucs, objective)
            >= config.min_delta
            for other in selected
        ):
            selected.append(item)
        if len(selected) >= config.max_candidates:
            break
    return tuple(item.candidate for item in selected)


def find_maximal_surround_shift(
    base_rgb,
    initial_surround_rgb,
    *,
    config: Config | None = None,
    objective: str = OBJECTIVE_TOTAL,
) -> SearchResult:
    settings = _settings(config)
    _validate_objective(objective)
    base = _rgb_tuple(base_rgb)
    surround = _rgb_tuple(initial_surround_rgb)
    reference = _appearance_array(base, surround, settings)

    def evaluate(candidate_rgb):
        return _appearance_array(base, candidate_rgb, settings), reference

    candidates = _rank_candidates(evaluate, settings, objective)
    return SearchResult(
        MODEL_ID,
        MODE_MAXIMAL_SURROUND_SHIFT,
        objective,
        settings,
        base,
        surround,
        candidates,
    )


def find_strongest_surrounds(
    base_rgb,
    *,
    config: Config | None = None,
    objective: str = OBJECTIVE_TOTAL,
) -> SearchResult:
    settings = _settings(config)
    _validate_objective(objective)
    base = _rgb_tuple(base_rgb)
    reference = _appearance_array(base, base, settings)

    def evaluate(candidate_rgb):
        return _appearance_array(base, candidate_rgb, settings), reference

    candidates = _rank_candidates(evaluate, settings, objective)
    return SearchResult(
        MODEL_ID, MODE_STRONGEST_SURROUNDS, objective, settings, base, None, candidates
    )


def find_sensitive_bases(
    surround_rgb,
    *,
    config: Config | None = None,
    objective: str = OBJECTIVE_TOTAL,
) -> SearchResult:
    settings = _settings(config)
    _validate_objective(objective)
    _viewing_condition(settings)
    surround = _rgb_tuple(surround_rgb)

    def evaluate(candidate_rgb):
        shifted = _appearance_array(candidate_rgb, surround, settings)
        reference = _appearance_array(candidate_rgb, candidate_rgb, settings)
        return shifted, reference

    candidates = _rank_candidates(evaluate, settings, objective)
    return SearchResult(
        MODEL_ID, MODE_SENSITIVE_BASES, objective, settings, None, surround, candidates
    )
