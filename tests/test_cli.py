import json

from colourshift import cli
from colourshift.core.algorithms import (
    MODE_MAXIMAL_SURROUND_SHIFT,
    MODE_SENSITIVE_BASES,
    MODE_STRONGEST_SURROUNDS,
    MODEL_ID,
    OBJECTIVE_CHROMATIC,
    OBJECTIVE_TOTAL,
    ColourShiftCandidate,
    SearchResult,
)
from colourshift.core.config import Config
from colourshift.io import NEUTRAL_GREY_HEX


def result(mode=MODE_MAXIMAL_SURROUND_SHIFT):
    base = None if mode == MODE_SENSITIVE_BASES else (0.0, 0.0, 0.0)
    surround = (1.0, 1.0, 1.0) if mode != MODE_STRONGEST_SURROUNDS else None
    return SearchResult(
        MODEL_ID,
        mode,
        OBJECTIVE_TOTAL,
        Config(rgb_grid_points=2),
        base,
        surround,
        (ColourShiftCandidate((0.0, 1.0, 0.0), 7.5, 6.0),),
    )


def test_config_from_args_maps_renamed_cli_option():
    args = cli.build_parser().parse_args(
        [
            "--output",
            "out.json",
            "--grid-points",
            "4",
            "--background-luminous-factor",
            "12",
            "--adapting-luminance",
            "34",
        ]
    )
    config = cli.config_from_args(args)
    assert config.background_luminous_factor == 12
    assert config.adapting_luminance == 34
    assert config.rgb_grid_points == 4
    assert not hasattr(args, "engine")
    assert args.objective == OBJECTIVE_CHROMATIC


def test_cli_writes_unified_json_and_figures(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    figures = tmp_path / "figures"
    monkeypatch.setattr(cli, "run_search", lambda *args, **kwargs: result())
    cli.main(["--output", str(output), "--figures-dir", str(figures)])

    payload = json.loads(output.read_text())
    assert payload["model"] == MODEL_ID
    assert payload["mode"] == MODE_MAXIMAL_SURROUND_SHIFT
    assert payload["candidates"][0]["hex"] == "#00ff00"
    assert (figures / "1.png").exists()


def test_sensitive_figure_uses_neutral_reference(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "save_comparison_image", lambda *args: calls.append(args))
    cli.write_figures(tmp_path, result(MODE_SENSITIVE_BASES))
    assert calls == [(tmp_path / "1.png", "#00ff00", NEUTRAL_GREY_HEX, "#00ff00", "#ffffff")]


def test_strongest_figure_uses_self_surround_reference(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "save_comparison_image", lambda *args: calls.append(args))
    cli.write_figures(tmp_path, result(MODE_STRONGEST_SURROUNDS))
    assert calls == [(tmp_path / "1.png", "#000000", "#000000", "#000000", "#00ff00")]
