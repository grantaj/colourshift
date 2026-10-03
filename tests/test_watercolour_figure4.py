import json

from colourshift.watercolour._edge_model import EdgeModelConfig
from colourshift.watercolour.colourimetry import SRGBConversionPolicy
from colourshift.watercolour.figure4 import (
    FIGURE4_CONDITIONS,
    conversion_sensitivity_audit,
    reproduce_figure4,
    write_figure4_report,
)


def test_figure4_has_all_six_reversed_pair_conditions():
    assert FIGURE4_CONDITIONS == (
        ("orange", "purple"),
        ("purple", "orange"),
        ("red", "green"),
        ("green", "red"),
        ("yellow", "blue"),
        ("blue", "yellow"),
    )


def test_figure4_canonical_reproduction_has_expected_direction_pattern():
    measurements = reproduce_figure4(
        conversion_policy=SRGBConversionPolicy(False, False),
        model_config=EdgeModelConfig(opponent_transform="van_de_sande"),
    )
    by_inner = {item.inner_colour: item for item in measurements}

    for colour in ("purple", "red", "green", "yellow", "blue"):
        assert by_inner[colour].predicted_angle_difference_deg < 5.0
    assert by_inner["orange"].predicted_angle_difference_deg > 20.0
    assert all(item.predicted_shift_ratio > item.published_shift_ratio for item in measurements)


def test_figure4_conversion_sensitivity_keeps_all_policies_visible():
    audit = conversion_sensitivity_audit()
    assert set(audit) == {
        "direct-extended",
        "direct-clipped",
        "bradford-d65-extended",
        "bradford-d65-clipped",
    }
    assert all(len(measurements) == 6 for measurements in audit.values())


def test_write_figure4_report_records_under_specification(tmp_path):
    report_path = write_figure4_report(tmp_path)
    payload = json.loads(report_path.read_text())

    assert payload["canonical_conversion_policy"] == "direct-extended"
    assert payload["exact_figure4_raster_published"] is False
    assert len(payload["canonical_measurements"]) == 6
    assert payload["summary"]["canonical_orange_angle_deg"] > 20.0
    assert payload["summary"]["canonical_max_angle_excluding_orange_deg"] < 5.0
