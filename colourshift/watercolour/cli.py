"""Command-line tools for reproducing published Watercolour Effect results."""

from __future__ import annotations

import argparse

from .figure3 import write_figure3_bundle
from .figure4 import write_figure4_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="colourshift-watercolour",
        description="Reproduce published Watercolour Effect model results.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    figure3 = subparsers.add_parser(
        "figure3",
        help="reproduce the qualitative Cohen-Duwek & Spitzer Figure 3 cases",
    )
    figure3.add_argument("--output-dir", default="watercolour-figure3")

    figure4 = subparsers.add_parser(
        "figure4",
        help="reproduce the quantitative Figure 4 comparison and sensitivity audit",
    )
    figure4.add_argument("--output-dir", default="watercolour-figure4")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "figure3":
        write_figure3_bundle(args.output_dir)
        return 0
    if args.command == "figure4":
        write_figure4_report(args.output_dir)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
