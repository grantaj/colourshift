# Auto-generated mechanical refactor from single-file version
import numpy as np
import warnings
import colour
from colour.appearance import XYZ_to_CIECAM02
from colour.models.cam02_ucs import JMh_CIECAM02_to_CAM02UCS
from colour.difference import delta_E_CAM02UCS

from .colour_models import rgb_to_hex, rgb_to_XYZ, is_valid_JMh

DEBUG = True

def compute_appearance_difference(base_rgb, original_surround_rgb, min_delta=10.0, max_candidates=3):
    base_XYZ = rgb_to_XYZ(base_rgb)
    original_surround_XYZ = rgb_to_XYZ(original_surround_rgb)

    vc = colour.VIEWING_CONDITIONS_CIECAM02['Average']
    Y_b = 20
    L_A = 64

    base_spec = XYZ_to_CIECAM02(base_XYZ, original_surround_XYZ, Y_b, L_A, surround=vc)
    base_JMh = [base_spec.J, base_spec.M, base_spec.h]
    base_UCS = JMh_CIECAM02_to_CAM02UCS(base_JMh)

    if DEBUG is True:
        print("Base JMh:", base_JMh)
        print("Base UCS:", base_UCS)

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for r in np.linspace(0, 1, 12):
            for g in np.linspace(0, 1, 12):
                for b in np.linspace(0, 1, 12):
                    candidate_rgb = [r, g, b]
                    try:
                        surround_XYZ = rgb_to_XYZ(candidate_rgb)
                        candidate_spec = XYZ_to_CIECAM02(base_XYZ, surround_XYZ, Y_b, L_A, surround=vc)
                        J, M, h = candidate_spec.J, candidate_spec.M, candidate_spec.h
                        if not is_valid_JMh(J, M, h):
                            continue
                        candidate_JMh = [J, M, h]
                        candidate_UCS = JMh_CIECAM02_to_CAM02UCS(candidate_JMh)
                        if not all(np.isfinite(candidate_UCS)):
                            continue
                        shift_dE = delta_E_CAM02UCS(base_UCS, candidate_UCS)
                        if not np.isfinite(shift_dE):
                            continue
                        if DEBUG is True:
                            print(f"Candidate {rgb_to_hex(candidate_rgb)} - JMh: {candidate_JMh}, UCS: {candidate_UCS}, ΔE: {shift_dE:.2f}")
                        candidates.append((candidate_rgb, shift_dE, candidate_UCS))
                    except Exception as e:
                        print(f"Error with {candidate_rgb}: {e}")
                        continue

    candidates.sort(key=lambda x: -x[1])

    filtered = []
    for rgb, shift_dE, ucs in candidates:
        deltas = [delta_E_CAM02UCS(ucs, other_ucs) for _, _, other_ucs in filtered]
        if DEBUG is True:
            print(f"Testing candidate {rgb_to_hex(rgb)} with ΔE distances to existing: {deltas}")
        if all(d >= min_delta for d in deltas):
            filtered.append((rgb, shift_dE, ucs))
        if len(filtered) >= max_candidates:
            break

    return [(rgb, delta_E_CAM02UCS(base_UCS, ucs)) for rgb, _, ucs in filtered]

def find_extreme_shift_colors(fixed_rgb, fixed_as_base, min_delta=10.0, max_candidates=3):
    fixed_XYZ = rgb_to_XYZ(fixed_rgb)
    vc = colour.VIEWING_CONDITIONS_CIECAM02['Average']
    Y_b = 20
    L_A = 64

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for r in np.linspace(0, 1, 12):
            for g in np.linspace(0, 1, 12):
                for b in np.linspace(0, 1, 12):
                    test_rgb = [r, g, b]
                    try:
                        test_XYZ = rgb_to_XYZ(test_rgb)
                        if fixed_as_base:
                            base_spec = XYZ_to_CIECAM02(fixed_XYZ, test_XYZ, Y_b, L_A, surround=vc)
                            test_spec = XYZ_to_CIECAM02(fixed_XYZ, fixed_XYZ, Y_b, L_A, surround=vc)
                        else:
                            base_spec = XYZ_to_CIECAM02(test_XYZ, fixed_XYZ, Y_b, L_A, surround=vc)
                            test_spec = XYZ_to_CIECAM02(fixed_XYZ, fixed_XYZ, Y_b, L_A, surround=vc)

                        base_JMh = [base_spec.J, base_spec.M, base_spec.h]
                        test_JMh = [test_spec.J, test_spec.M, test_spec.h]
                        if not (is_valid_JMh(*base_JMh) and is_valid_JMh(*test_JMh)):
                            continue
                        base_UCS = JMh_CIECAM02_to_CAM02UCS(base_JMh)
                        test_UCS = JMh_CIECAM02_to_CAM02UCS(test_JMh)
                        if not all(np.isfinite(test_UCS)):
                            continue
                        shift_dE = delta_E_CAM02UCS(base_UCS, test_UCS)
                        if not np.isfinite(shift_dE):
                            continue
                        candidates.append((test_rgb, shift_dE))
                    except Exception:
                        continue
    candidates.sort(key=lambda x: -x[1])
    filtered = []
    for rgb, dE in candidates:
        deltas = []
        for r, _ in filtered:
            spec1 = XYZ_to_CIECAM02(rgb_to_XYZ(rgb), fixed_XYZ, Y_b, L_A, surround=vc)
            spec2 = XYZ_to_CIECAM02(rgb_to_XYZ(r), fixed_XYZ, Y_b, L_A, surround=vc)
            ucs1 = JMh_CIECAM02_to_CAM02UCS([spec1.J, spec1.M, spec1.h])
            ucs2 = JMh_CIECAM02_to_CAM02UCS([spec2.J, spec2.M, spec2.h])
            deltas.append(delta_E_CAM02UCS(ucs1, ucs2))
        if all(d >= min_delta for d in deltas):
            filtered.append((rgb, dE))
        if len(filtered) >= max_candidates:
            break
    return filtered

