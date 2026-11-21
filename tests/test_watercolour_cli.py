import json

import pytest

import colourshift.watercolour.cli as cli_module
from colourshift.watercolour.model import WatercolourPrediction
from colourshift.watercolour.optimise import (
    WatercolourOptimisationResult,
    optimal_watercolour_geometry,
)


def test_cli_exposes_reproduction_and_optimisation_commands():
    parser = cli_module.build_parser()
    assert parser.parse_args(["figure3"]).command == "figure3"
    assert parser.parse_args(["figure4"]).command == "figure4"
    args = parser.parse_args(["optimise", "--field", "#ffffff", "--output", "result.json"])
    assert args.command == "optimise"
    assert args.seed == 0
    assert args.popsize == 8
    assert args.maxiter == 20


def test_optimise_cli_writes_reproducible_json(monkeypatch, tmp_path):
    geometry = optimal_watercolour_geometry()
    prediction = WatercolourPrediction(
        geometry=geometry,
        geometry_gain=1.0,
        predicted_rgb_unclipped=(1.05, 0.9, 0.8),
        chromatic_shift_uv=0.123,
        relative_luminance_shift=-0.04,
        opponent_shift=(0.01, 0.02, 0.03),
    )

    def fake_optimise(**kwargs):
        assert kwargs["field_rgb"] == (1.0, 1.0, 1.0)
        assert kwargs["background_rgb"] is None
        assert kwargs["geometry"] is None
        assert kwargs["config"].seed == 11
        assert kwargs["config"].popsize == 4
        assert kwargs["config"].maxiter == 2
        assert kwargs["config"].polish is False
        return WatercolourOptimisationResult(
            field_rgb=(1.0, 1.0, 1.0),
            background_rgb=(1.0, 1.0, 1.0),
            inner_rgb=(1.0, 0.0, 0.0),
            outer_rgb=(0.0, 1.0, 0.0),
            geometry=geometry,
            prediction=prediction,
            evaluations=31,
            nonfinite_evaluations=2,
            success=True,
            message="ok",
            seed=11,
        )

    monkeypatch.setattr(cli_module, "optimise_watercolour", fake_optimise)
    output = tmp_path / "nested" / "result.json"
    assert (
        cli_module.main(
            [
                "optimise",
                "--field",
                "#ffffff",
                "--output",
                str(output),
                "--seed",
                "11",
                "--popsize",
                "4",
                "--maxiter",
                "2",
                "--no-polish",
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text())
    assert payload["field_hex"] == "#ffffff"
    assert payload["inner_hex"] == "#ff0000"
    assert payload["outer_hex"] == "#00ff00"
    assert payload["predicted_rgb_unclipped"] == [1.05, 0.9, 0.8]
    assert payload["chromatic_shift_uv"] == pytest.approx(0.123)
    assert payload["optimiser"] == {
        "seed": 11,
        "popsize": 4,
        "maxiter": 2,
        "tol": 1e-4,
        "polish": False,
        "evaluations": 31,
        "nonfinite_evaluations": 2,
        "success": True,
        "message": "ok",
    }


def test_optimise_cli_requires_complete_custom_geometry(tmp_path):
    with pytest.raises(SystemExit):
        cli_module.main(
            [
                "optimise",
                "--field",
                "#ffffff",
                "--output",
                str(tmp_path / "result.json"),
                "--inner-width-arcmin",
                "7.5",
            ]
        )
