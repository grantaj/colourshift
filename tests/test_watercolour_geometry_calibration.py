import pytest

from colourshift.watercolour.global_form import (
    curvature_frequency_gain,
    geometry_gain,
    relative_scale_gain,
)
from colourshift.watercolour.spatial_selectivity import paired_contour_gain_arcmin


def test_local_width_calibration_peaks_at_15_arcmin_total():
    totals = (6.0, 11.0, 15.0, 19.0, 24.0)
    gains = {total: paired_contour_gain_arcmin(total / 2, total / 2) for total in totals}
    assert max(gains, key=gains.get) == 15.0


def test_equal_width_calibration_is_symmetric():
    total = 15.0

    def gain(ratio):
        inner = total * ratio / (1 + ratio)
        outer = total / (1 + ratio)
        return paired_contour_gain_arcmin(inner, outer)

    assert gain(1.0) > gain(0.5)
    assert gain(1.0) > gain(2.0)
    assert gain(0.5) == pytest.approx(gain(2.0))


def test_frequency_calibration_saturates_at_12_cpr():
    assert curvature_frequency_gain(4) == pytest.approx(1 / 3)
    assert curvature_frequency_gain(8) == pytest.approx(2 / 3)
    assert curvature_frequency_gain(12) == pytest.approx(1)
    assert curvature_frequency_gain(20) == pytest.approx(1)


def test_relative_scale_kernel_is_reciprocal_symmetric():
    assert relative_scale_gain(15, 3.2) == pytest.approx(1.0)

    reference_ratio = (15 / 60) / 3.2
    smaller_width = reference_ratio * 0.5 * 3.2 * 60
    larger_width = reference_ratio * 2.0 * 3.2 * 60
    assert relative_scale_gain(smaller_width, 3.2) == pytest.approx(
        relative_scale_gain(larger_width, 3.2)
    )


def test_calibrated_geometry_encodes_observed_size_directions():
    narrow_small = geometry_gain(
        inner_width_arcmin=3,
        outer_width_arcmin=3,
        diameter_deg=2.3,
        frequency_cpr=10,
    )
    narrow_standard = geometry_gain(
        inner_width_arcmin=3,
        outer_width_arcmin=3,
        diameter_deg=3.2,
        frequency_cpr=10,
    )
    wide_standard = geometry_gain(
        inner_width_arcmin=12,
        outer_width_arcmin=12,
        diameter_deg=3.2,
        frequency_cpr=10,
    )
    wide_large = geometry_gain(
        inner_width_arcmin=12,
        outer_width_arcmin=12,
        diameter_deg=4.5,
        frequency_cpr=10,
    )

    assert narrow_small > narrow_standard
    assert wide_large > wide_standard
