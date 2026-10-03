import numpy as np
import pytest

from colourshift.watercolour.model import (
    WatercolourGeometry,
    _ColourDriveReference,
    _extract_colour_drive,
    predict_watercolour,
)

FIELD = (1.0, 1.0, 1.0)
INNER = (1.0, 0.72, 0.0)
OUTER = (0.32, 0.36, 0.85)


def test_default_prediction_has_explicit_chromatic_score():
    prediction = predict_watercolour(
        field_rgb=FIELD,
        inner_rgb=INNER,
        outer_rgb=OUTER,
    )
    assert prediction.chromatic_shift_uv > 0
    assert np.isfinite(prediction.relative_luminance_shift)
    assert prediction.geometry_gain == pytest.approx(1.0)


@pytest.mark.parametrize(
    "geometry",
    [
        WatercolourGeometry(inner_width_arcmin=3, outer_width_arcmin=3),
        WatercolourGeometry(inner_width_arcmin=12, outer_width_arcmin=12),
        WatercolourGeometry(inner_width_arcmin=5, outer_width_arcmin=10),
        WatercolourGeometry(inner_width_arcmin=10, outer_width_arcmin=5),
        WatercolourGeometry(diameter_deg=2.3),
        WatercolourGeometry(diameter_deg=4.5),
        WatercolourGeometry(frequency_cpr=4),
        WatercolourGeometry(frequency_cpr=20),
    ],
)
def test_supported_geometry_boundaries_are_accepted(geometry):
    assert geometry.inner_width_arcmin > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"inner_width_arcmin": 2, "outer_width_arcmin": 2},
        {"inner_width_arcmin": 13, "outer_width_arcmin": 13},
        {"inner_width_arcmin": 4, "outer_width_arcmin": 12},
        {"inner_width_arcmin": 12, "outer_width_arcmin": 4},
        {"diameter_deg": 2.2},
        {"diameter_deg": 4.6},
        {"frequency_cpr": 3.9},
        {"frequency_cpr": 20.1},
    ],
)
def test_unsupported_geometry_is_rejected(kwargs):
    with pytest.raises(ValueError):
        WatercolourGeometry(**kwargs)


def test_geometry_changes_strength_without_rotating_opponent_direction():
    reference = predict_watercolour(
        field_rgb=FIELD,
        inner_rgb=INNER,
        outer_rgb=OUTER,
    )
    altered = predict_watercolour(
        field_rgb=FIELD,
        inner_rgb=INNER,
        outer_rgb=OUTER,
        geometry=WatercolourGeometry(
            inner_width_arcmin=3,
            outer_width_arcmin=3,
            diameter_deg=3.2,
            frequency_cpr=8,
        ),
    )
    left = np.asarray(reference.opponent_shift)
    right = np.asarray(altered.opponent_shift)
    cosine = np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right))
    assert cosine == pytest.approx(1.0, abs=1e-12)


def test_colour_drive_direction_is_stable_under_reference_changes():
    field = np.asarray(FIELD)
    inner = np.asarray(INNER)
    outer = np.asarray(OUTER)
    references = (
        _ColourDriveReference(),
        _ColourDriveReference(
            size_px=192,
            outer_radius_px=54,
            points=5,
            inner_width_px=3,
            outer_width_px=3,
            inset_px=9,
        ),
        _ColourDriveReference(
            size_px=320,
            outer_radius_px=96,
            points=9,
            inner_width_px=5,
            outer_width_px=5,
            inset_px=15,
        ),
    )
    shifts = [
        _extract_colour_drive(
            field_rgb=field,
            inner_rgb=inner,
            outer_rgb=outer,
            background_rgb=field,
            reference=reference,
        )[1]
        for reference in references
    ]
    base = shifts[0][1:]
    for shift in shifts[1:]:
        candidate = shift[1:]
        cosine = np.dot(base, candidate) / (np.linalg.norm(base) * np.linalg.norm(candidate))
        assert cosine > 0.95


@pytest.mark.parametrize(
    "name,value",
    [
        ("field_rgb", (1.01, 1.0, 1.0)),
        ("inner_rgb", (-0.01, 0.5, 0.5)),
        ("outer_rgb", (0.5, 0.5, 1.01)),
        ("background_rgb", (0.5, -0.01, 0.5)),
    ],
)
def test_public_model_rejects_out_of_gamut_input(name, value):
    kwargs = {
        "field_rgb": FIELD,
        "inner_rgb": INNER,
        "outer_rgb": OUTER,
    }
    kwargs[name] = value
    with pytest.raises(ValueError):
        predict_watercolour(**kwargs)
