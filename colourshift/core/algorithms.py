import logging
import warnings

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


def _settings(config):
    return config or DEFAULT_CONFIG


def _viewing_condition(config):
    return colour.VIEWING_CONDITIONS_CIECAM02[config.viewing_condition]


def _cam02_ucs(stimulus_XYZ, surround_XYZ, config):
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


def _rgb_grid(points):
    for r in np.linspace(0, 1, points):
        for g in np.linspace(0, 1, points):
            for b in np.linspace(0, 1, points):
                yield [float(r), float(g), float(b)]


def _filter_separated_candidates(candidates, min_delta, max_candidates):
    filtered = []
    for rgb, shift_delta, ucs in candidates:
        if all(delta_E_CAM02UCS(ucs, other_ucs) >= min_delta for _, _, other_ucs in filtered):
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
):
    config = _settings(config)
    min_delta = config.min_delta if min_delta is None else min_delta
    max_candidates = config.max_candidates if max_candidates is None else max_candidates

    base_XYZ = rgb_to_XYZ(base_rgb)
    original_surround_XYZ = rgb_to_XYZ(original_surround_rgb)
    base_UCS = _cam02_ucs(base_XYZ, original_surround_XYZ, config)
    if base_UCS is None:
        return []

    logger.debug("Base CAM02-UCS: %s", base_UCS)

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for candidate_rgb in _rgb_grid(config.rgb_grid_points):
            try:
                candidate_UCS = _cam02_ucs(base_XYZ, rgb_to_XYZ(candidate_rgb), config)
                if candidate_UCS is None:
                    continue
                shift_delta = delta_E_CAM02UCS(base_UCS, candidate_UCS)
                if np.isfinite(shift_delta):
                    candidates.append((candidate_rgb, float(shift_delta), candidate_UCS))
            except (ArithmeticError, ValueError, RuntimeWarning) as exc:
                logger.debug("Skipping invalid surround candidate %s: %s", candidate_rgb, exc)

    candidates.sort(key=lambda x: -x[1])
    filtered = _filter_separated_candidates(candidates, min_delta, max_candidates)
    return [(rgb, shift_delta) for rgb, shift_delta, _ in filtered]


def find_extreme_shift_colors(
    fixed_rgb,
    fixed_as_base,
    min_delta=None,
    max_candidates=None,
    config=None,
):
    config = _settings(config)
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
                    shifted_UCS = _cam02_ucs(fixed_XYZ, test_XYZ, config)
                    reference_UCS = _cam02_ucs(fixed_XYZ, fixed_XYZ, config)
                else:
                    shifted_UCS = _cam02_ucs(test_XYZ, fixed_XYZ, config)
                    reference_UCS = _cam02_ucs(test_XYZ, test_XYZ, config)
                if shifted_UCS is None or reference_UCS is None:
                    continue
                shift_delta = delta_E_CAM02UCS(shifted_UCS, reference_UCS)
                if np.isfinite(shift_delta):
                    candidates.append((test_rgb, float(shift_delta), shifted_UCS))
            except (ArithmeticError, ValueError, RuntimeWarning) as exc:
                logger.debug("Skipping invalid extreme-shift candidate %s: %s", test_rgb, exc)

    candidates.sort(key=lambda x: -x[1])
    filtered = _filter_separated_candidates(candidates, min_delta, max_candidates)
    return [(rgb, shift_delta) for rgb, shift_delta, _ in filtered]
