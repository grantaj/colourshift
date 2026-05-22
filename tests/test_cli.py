import json

from colourshift import cli
from colourshift.core.algorithms import ColourShiftResult
from colourshift.io import NEUTRAL_GREY_HEX


def test_config_from_args_maps_cli_options():
    args = cli.build_parser().parse_args(
        [
            "--output",
            "out.json",
            "--grid-points",
            "4",
            "--min-delta",
            "6",
            "--max-candidates",
            "2",
            "--viewing-condition",
            "Dim",
            "--background-luminance",
            "12",
            "--adapting-luminance",
            "34",
        ]
    )

    config = cli.config_from_args(args)

    assert config.viewing_condition == "Dim"
    assert config.background_luminance == 12
    assert config.adapting_luminance == 34
    assert config.rgb_grid_points == 4
    assert config.min_delta == 6
    assert config.max_candidates == 2


def test_cli_writes_json_and_figures(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    figures_dir = tmp_path / "figures"

    monkeypatch.setattr(
        cli,
        "run_search",
        lambda mode, base_hex, surround_hex, config: [
            ColourShiftResult(rgb=[0.0, 1.0, 0.0], delta_e=7.5)
        ],
    )

    cli.main(
        [
            "--output",
            str(output),
            "--figures-dir",
            str(figures_dir),
            "--base",
            "#000000",
            "--surround",
            "#ffffff",
            "--grid-points",
            "2",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["search"]["mode"] == cli.MODE_MAXIMAL_SURROUND_SHIFT
    assert payload["search"]["config"]["rgb_grid_points"] == 2
    assert payload["candidates"][0]["hex"] == "#00ff00"
    assert (figures_dir / "1.png").exists()


def test_write_figures_uses_neutral_reference_for_sensitive_bases(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        cli,
        "save_comparison_image",
        lambda path, left_base, left_surround, right_base, right_surround: calls.append(
            (path, left_base, left_surround, right_base, right_surround)
        ),
    )

    cli.write_figures(
        tmp_path,
        cli.MODE_SENSITIVE_BASES,
        "#950000",
        "#964301",
        [ColourShiftResult(rgb=[0.0, 1.0, 0.0], delta_e=7.5)],
    )

    assert calls == [
        (tmp_path / "1.png", "#00ff00", NEUTRAL_GREY_HEX, "#00ff00", "#964301")
    ]


def test_write_figures_uses_self_surround_reference_for_strongest_surrounds(
    monkeypatch, tmp_path
):
    calls = []

    monkeypatch.setattr(
        cli,
        "save_comparison_image",
        lambda path, left_base, left_surround, right_base, right_surround: calls.append(
            (path, left_base, left_surround, right_base, right_surround)
        ),
    )

    cli.write_figures(
        tmp_path,
        cli.MODE_STRONGEST_SURROUNDS,
        "#950000",
        "#964301",
        [ColourShiftResult(rgb=[0.0, 0.0, 0.0], delta_e=7.5)],
    )

    assert calls == [
        (tmp_path / "1.png", "#950000", "#950000", "#950000", "#000000")
    ]
