import numpy as np
import pytest

from colourshift.watercolour.colourimetry import (
    SRGBConversionPolicy,
    XYZ_to_uv,
    is_unit_gamut,
    sRGB_to_uvY,
    uvY_to_sRGB,
    uvY_to_XYZ,
    xyY_to_sRGB,
)


def test_uvY_XYZ_round_trip():
    uv = np.array([0.2490, 0.5301])
    XYZ = uvY_to_XYZ(uv[0], uv[1], 0.6875)
    assert XYZ_to_uv(XYZ) == pytest.approx(uv)


def test_extended_srgb_round_trip_preserves_devinck_coordinate():
    policy = SRGBConversionPolicy(False, False)
    rgb = uvY_to_sRGB(0.2490, 0.5301, 55 / 80, policy=policy)
    uv, Y = sRGB_to_uvY(rgb, policy=policy)
    assert uv == pytest.approx([0.2490, 0.5301], abs=2e-7)
    assert Y == pytest.approx(55 / 80, abs=2e-7)


def test_extended_policy_exposes_out_of_gamut_instead_of_hiding_it():
    policy = SRGBConversionPolicy(False, False)
    orange = uvY_to_sRGB(0.2490, 0.5301, 55 / 80, policy=policy)
    assert not is_unit_gamut(orange)
    assert np.max(orange) > 1.0


def test_clipped_policy_is_explicit_and_destructive():
    extended = uvY_to_sRGB(
        0.2490,
        0.5301,
        55 / 80,
        policy=SRGBConversionPolicy(False, False),
    )
    clipped = uvY_to_sRGB(
        0.2490,
        0.5301,
        55 / 80,
        policy=SRGBConversionPolicy(False, True),
    )
    assert np.max(extended) > 1.0
    assert np.max(clipped) == 1.0


def test_xyY_extended_srgb_round_trip_via_uv_coordinates():
    rgb = xyY_to_sRGB(0.40, 0.43, 109.6 / 134)
    uv, Y = sRGB_to_uvY(rgb)
    # Convert the original xy to u'v' analytically.
    denominator = -2 * 0.40 + 12 * 0.43 + 3
    expected_u = 4 * 0.40 / denominator
    expected_v = 9 * 0.43 / denominator
    assert uv == pytest.approx([expected_u, expected_v], abs=2e-7)
    assert Y == pytest.approx(109.6 / 134, abs=2e-7)
