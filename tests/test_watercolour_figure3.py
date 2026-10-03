from colourshift.watercolour._edge_model import EdgeModelConfig
from colourshift.watercolour.figure3 import (
    figure3_cases,
    reproduce_figure3,
)


def test_figure3_fixture_contains_all_six_published_conditions():
    assert [case.label for case in figure3_cases()] == [
        "A-I",
        "A-II",
        "B-I",
        "B-II",
        "C-I",
        "C-II",
    ]


def test_gate_1a_reproduces_all_six_qualitative_directions():
    config = EdgeModelConfig(opponent_transform="van_de_sande")
    measurements = reproduce_figure3(config)

    assert all(measurement.passes_direction_check for measurement in measurements)

    chromatic = [m for m in measurements if m.kind == "chromatic"]
    assert all(m.assimilation_cosine is not None for m in chromatic)
    assert min(m.assimilation_cosine for m in chromatic) > 0.9

    achromatic = {m.label: m for m in measurements if m.kind == "achromatic"}
    assert achromatic["C-I"].luminance_shift > 0
    assert achromatic["C-II"].luminance_shift < 0


def test_figure3_primary_transform_is_not_hidden_model_tuning():
    default = EdgeModelConfig()
    assert default.opponent_transform == "van_de_sande"
