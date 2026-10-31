import logging
import warnings
from dataclasses import dataclass

import numpy as np

from ._colour_warnings import suppress_colour_optional_dependency_warnings
from .colour_models import is_valid_JMh, rgb_to_XYZ
from .config import DEFAULT_CONFIG

suppress_colour_optional_dependency_warnings()

import colour  # noqa: E402
from colour.appearance import XYZ_to_CIECAM02  # noqa: E402
from colour.difference import delta_E_CAM02UCS  # noqa: E402
from colour.models.cam02_ucs import JMh_CIECAM02_to_CAM02UCS  # noqa: E402

logger = logging.getLogger(__name__)

ENGINE_LEGACY = "legacy-ciecam02-proxy"
ENGINE_CORRECTED = "corrected-ciecam02-proxy"
ENGINE_LABELS = {
    ENGINE_LEGACY: "Legacy CIECAM02 proxy (deprecated)",
    ENGINE_CORRECTED: "Corrected CIECAM02 proxy",
}

OBJECTIVE_TOTAL = "total"
OBJECTIVE_CHROMATIC = "chromatic"
OBJECTIVES = (OBJECTIVE_TOTAL, OBJECTIVE_CHROMATIC)


@dataclass(frozen=True)
class ColourShiftResult:
    rgb: list[float]
    delta_e: float
    chromatic_delta: float | None = None


@dataclass(frozen=True)
class EngineSearchResults:
    engine: str
    engine_label: str
    objective: str
    candidates: list[ColourShiftResult]


def _settings(config):
    return config or DEFAULT_CONFIG


def _viewing_condition(config):
    return colour.VIEWING_CONDITIONS_CIECAM02[config.viewing_condition]


def _cam02_ucs(stimulus_XYZ, surround_XYZ, config):
    """Historical appearance proxy, preserved exactly for reproducibility.

    This intentionally retains the original positional L_A/Y_b reversal and
    use of the coloured surround as XYZ_w.
    """
    spec = XYZ_to_CIECAM02(
        stimulus_XYZ,
        surround_XYZ,
        config.background_luminance,
        config.adapting_luminance,
        surround=_viewing_condition(config),
    )
    JMh = [spec.J, spec.M, spec.h]
    if not is_valid_JMh(*JMh):
        return None
    ucs = JMh_CIECAM02_to_CAM02UCS(JMh)
    if not all(np.isfinite(ucs)):
        return None
    return ucs


def _cam02_ucs_corrected(stimulus_XYZ, surround_XYZ, config):
    """Adaptation proxy with the intended L_A/Y_b mapping made explicit."""
    spec = XYZ_to_CIECAM02(
        XYZ=stimulus_XYZ,
        XYZ_w=surround_XYZ,
        L_A=config.adapting_luminance,
        Y_b=config.background_luminance,
        surround=_viewing_condition(config),
    )
    JMh = [spec.J, spec.M, spec.h]
    if not is_valid_JMh(*JMh):
        return None
    ucs = JMh_CIECAM02_to_CAM02UCS(JMh)
    if not all(np.isfinite(ucs)):
        return None
    return ucs


def _appearance_function(engine):
    if engine == ENGINE_LEGACY:
        return _cam02_ucs
    if engine == ENGINE_CORRECTED:
        return _cam02_ucs_corrected
    raise ValueError(f"Unsupported appearance engine: {engine}")


def _shift_components(reference_ucs, candidate_ucs):
    total = float(delta_E_CAM02UCS(reference_ucs, candidate_ucs))
    difference = np.asarray(candidate_ucs, dtype=float) - np.asarray(reference_ucs, dtype=float)
    chromatic = float(np.linalg.norm(difference[1:]))
    return total, chromatic


def _rgb_grid(points):
    for r in np.linspace(0, 1, points):
        for g in np.linspace(0, 1, points):
            for b in np.linspace(0, 1, points):
                yield [float(r), float(g), float(b)]


def _candidate_separation(left_ucs, right_ucs, objective):
    if objective == OBJECTIVE_CHROMATIC:
        difference = np.asarray(left_ucs, dtype=float) - np.asarray(right_ucs, dtype=float)
        return float(np.linalg.norm(difference[1:]))
    return float(delta_E_CAM02UCS(left_ucs, right_ucs))


def _filter_separated_candidates(
    candidates,
    min_delta,
    max_candidates,
    objective=OBJECTIVE_TOTAL,
):
    filtered = []
    for rgb, shift_delta, ucs in candidates:
        if all(
            _candidate_separation(ucs, other_ucs, objective) >= min_delta
            for _, _, other_ucs in filtered
        ):
            filtered.append((rgb, shift_delta, ucs))
        if len(filtered) >= max_candidates:
            break
    return filtered


def compute_appearance_difference(
    base_rgb,
    original_surround_rgb,
    min_delta=None,
    max_candidates=None,
    config=None,
    engine=ENGINE_LEGACY,
    objective=OBJECTIVE_TOTAL,
):
    config = _settings(config)
    if objective not in OBJECTIVES:
        raise ValueError(f"Unsupported search objective: {objective}")
    appearance = _appearance_function(engine)
    min_delta = config.min_delta if min_delta is None else min_delta
    max_candidates = config.max_candidates if max_candidates is None else max_candidates

    base_XYZ = rgb_to_XYZ(base_rgb)
    original_surround_XYZ = rgb_to_XYZ(original_surround_rgb)
    base_UCS = appearance(base_XYZ, original_surround_XYZ, config)
    if base_UCS is None:
        return []

    logger.debug("Base CAM02-UCS: %s", base_UCS)

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for candidate_rgb in _rgb_grid(config.rgb_grid_points):
            try:
                candidate_UCS = appearance(base_XYZ, rgb_to_XYZ(candidate_rgb), config)
                if candidate_UCS is None:
                    continue
                total_delta, chromatic_delta = _shift_components(base_UCS, candidate_UCS)
                score = total_delta if objective == OBJECTIVE_TOTAL else chromatic_delta
                if np.isfinite(score):
                    candidates.append(
                        (candidate_rgb, score, candidate_UCS, total_delta, chromatic_delta)
                    )
            except (ArithmeticError, ValueError, RuntimeWarning) as exc:
                logger.debug("Skipping invalid surround candidate %s: %s", candidate_rgb, exc)

    candidates.sort(key=lambda x: -x[1])
    filter_input = [(rgb, score, ucs) for rgb, score, ucs, _, _ in candidates]
    filtered = _filter_separated_candidates(
        filter_input,
        min_delta,
        max_candidates,
        objective,
    )
    components = {tuple(rgb): (total, chromatic) for rgb, _, _, total, chromatic in candidates}
    return [
        ColourShiftResult(
            rgb=rgb,
            delta_e=components[tuple(rgb)][0],
            chromatic_delta=components[tuple(rgb)][1],
        )
        for rgb, _, _ in filtered
    ]


def compare_appearance_engines(
    base_rgb,
    original_surround_rgb,
    *,
    engines=(ENGINE_CORRECTED, ENGINE_LEGACY),
    objective=OBJECTIVE_TOTAL,
    min_delta=None,
    max_candidates=None,
    config=None,
):
    """Run the same maximal-surround search through multiple engines."""
    return [
        EngineSearchResults(
            engine=engine,
            engine_label=ENGINE_LABELS[engine],
            objective=objective,
            candidates=compute_appearance_difference(
                base_rgb,
                original_surround_rgb,
                min_delta=min_delta,
                max_candidates=max_candidates,
                config=config,
                engine=engine,
                objective=objective,
            ),
        )
        for engine in engines
    ]


def find_extreme_shift_colors(
    fixed_rgb,
    fixed_as_base,
    min_delta=None,
    max_candidates=None,
    config=None,
    engine=ENGINE_LEGACY,
    objective=OBJECTIVE_TOTAL,
):
    config = _settings(config)
    if objective not in OBJECTIVES:
        raise ValueError(f"Unsupported search objective: {objective}")
    appearance = _appearance_function(engine)
    min_delta = config.min_delta if min_delta is None else min_delta
    max_candidates = config.max_candidates if max_candidates is None else max_candidates
    fixed_XYZ = rgb_to_XYZ(fixed_rgb)

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for test_rgb in _rgb_grid(config.rgb_grid_points):
            try:
                test_XYZ = rgb_to_XYZ(test_rgb)
                if fixed_as_base:
                    shifted_UCS = appearance(fixed_XYZ, test_XYZ, config)
                    reference_UCS = appearance(fixed_XYZ, fixed_XYZ, config)
                else:
                    shifted_UCS = appearance(test_XYZ, fixed_XYZ, config)
                    reference_UCS = appearance(test_XYZ, test_XYZ, config)
                if shifted_UCS is None or reference_UCS is None:
                    continue
                total_delta, chromatic_delta = _shift_components(
                    shifted_UCS,
                    reference_UCS,
                )
                score = total_delta if objective == OBJECTIVE_TOTAL else chromatic_delta
                if np.isfinite(score):
                    candidates.append((test_rgb, score, shifted_UCS, total_delta, chromatic_delta))
            except (ArithmeticError, ValueError, RuntimeWarning) as exc:
                logger.debug("Skipping invalid extreme-shift candidate %s: %s", test_rgb, exc)

    candidates.sort(key=lambda x: -x[1])
    filter_input = [(rgb, score, ucs) for rgb, score, ucs, _, _ in candidates]
    filtered = _filter_separated_candidates(
        filter_input,
        min_delta,
        max_candidates,
        objective,
    )
    components = {tuple(rgb): (total, chromatic) for rgb, _, _, total, chromatic in candidates}
    return [
        ColourShiftResult(
            rgb=rgb,
            delta_e=components[tuple(rgb)][0],
            chromatic_delta=components[tuple(rgb)][1],
        )
        for rgb, _, _ in filtered
    ]


def compare_extreme_shift_engines(
    fixed_rgb,
    fixed_as_base,
    *,
    engines=(ENGINE_CORRECTED, ENGINE_LEGACY),
    objective=OBJECTIVE_TOTAL,
    min_delta=None,
    max_candidates=None,
    config=None,
):
    """Run an extreme base/surround search through multiple engines."""
    return [
        EngineSearchResults(
            engine=engine,
            engine_label=ENGINE_LABELS[engine],
            objective=objective,
            candidates=find_extreme_shift_colors(
                fixed_rgb,
                fixed_as_base,
                min_delta=min_delta,
                max_candidates=max_candidates,
                config=config,
                engine=engine,
                objective=objective,
            ),
        )
        for engine in engines
    ]
