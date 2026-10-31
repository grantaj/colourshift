import json
from pathlib import Path

import pytest

from colourshift.core.algorithms import (
    MODEL_ID,
    appearance_coordinates,
    cam16_ucs_coordinates,
    find_maximal_surround_shift,
    find_sensitive_bases,
    find_strongest_surrounds,
)
from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex, rgb_to_XYZ
from colourshift.core.config import Config

FIXTURE = Path(__file__).parent / "fixtures" / "colourshift_reference.json"


def test_portable_numerical_reference():
    reference = json.loads(FIXTURE.read_text(encoding="utf-8"))
    config = Config(**reference["config"])
    conversion = reference["conversions"]
    appearance = reference["appearance"]

    assert reference["model"] == MODEL_ID
    assert hex_to_rgb(conversion["hex"]) == pytest.approx(conversion["rgb"], abs=1e-12)
    assert rgb_to_hex(conversion["rgb"]) == conversion["roundtrip_hex"]
    assert rgb_to_XYZ(conversion["rgb"]) == pytest.approx(conversion["xyz"], abs=1e-12)
    assert cam16_ucs_coordinates(appearance["target"], config) == pytest.approx(
        appearance["ordinary_target_cam16_ucs"], abs=1e-10
    )
    assert appearance_coordinates(
        appearance["target"], appearance["background"], config
    ) == pytest.approx(appearance["corrected_coordinates"], abs=1e-10)

    operations = {
        "maximal-surround-shift": lambda objective: find_maximal_surround_shift(
            appearance["target"], appearance["background"], config=config, objective=objective
        ),
        "strongest-surrounds": lambda objective: find_strongest_surrounds(
            appearance["target"], config=config, objective=objective
        ),
        "sensitive-bases": lambda objective: find_sensitive_bases(
            appearance["background"], config=config, objective=objective
        ),
    }
    for mode, objectives in reference["searches"].items():
        for objective, expected in objectives.items():
            actual = operations[mode](objective).candidates
            assert [list(candidate.rgb) for candidate in actual] == [
                candidate["rgb"] for candidate in expected
            ]
            assert [candidate.total_shift for candidate in actual] == pytest.approx(
                [candidate["total_shift"] for candidate in expected], abs=1e-10
            )
            assert [candidate.chromatic_shift for candidate in actual] == pytest.approx(
                [candidate["chromatic_shift"] for candidate in expected], abs=1e-10
            )
