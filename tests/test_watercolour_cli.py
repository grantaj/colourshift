from colourshift.watercolour.cli import build_parser


def test_cli_exposes_only_published_reproduction_commands():
    parser = build_parser()
    assert parser.parse_args(["figure3"]).command == "figure3"
    assert parser.parse_args(["figure4"]).command == "figure4"
