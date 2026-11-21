"""Command-line tools for Watercolour Effect reproduction and optimisation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex

from .figure3 import write_figure3_bundle
from .figure4 import write_figure4_report
from .model import WatercolourGeometry
from .optimise import WatercolourOptimisationConfig, optimise_watercolour

_GEOMETRY_ARGUMENTS = (
    "inner_width_arcmin",
    "outer_width_arcmin",
    "diameter_deg",
    "frequency_cpr",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="colourshift-watercolour",
        description="Reproduce and optimise Watercolour Effect model results.",
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

    optimise = subparsers.add_parser(
        "optimise",
        help="find contour colours maximising modelled chromatic WCE shift",
    )
    optimise.add_argument("--field", required=True, help="Field colour as a 6-digit hex value.")
    optimise.add_argument(
        "--background",
        help="Background colour as a 6-digit hex value; defaults to the field.",
    )
    optimise.add_argument("--output", required=True, help="Path for the JSON result file.")
    optimise.add_argument("--seed", type=int, default=0)
    optimise.add_argument("--popsize", type=int, default=8)
    optimise.add_argument("--maxiter", type=int, default=20)
    optimise.add_argument("--tol", type=float, default=1e-4)
    optimise.add_argument("--no-polish", action="store_true")
    optimise.add_argument("--inner-width-arcmin", type=float)
    optimise.add_argument("--outer-width-arcmin", type=float)
    optimise.add_argument("--diameter-deg", type=float)
    optimise.add_argument("--frequency-cpr", type=float)
    return parser


def _geometry_from_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> WatercolourGeometry | None:
    values = [getattr(args, name) for name in _GEOMETRY_ARGUMENTS]
    if not any(value is not None for value in values):
        return None
    if not all(value is not None for value in values):
        parser.error(
            "custom geometry requires --inner-width-arcmin, --outer-width-arcmin, "
            "--diameter-deg and --frequency-cpr together"
        )
    return WatercolourGeometry(
        inner_width_arcmin=args.inner_width_arcmin,
        outer_width_arcmin=args.outer_width_arcmin,
        diameter_deg=args.diameter_deg,
        frequency_cpr=args.frequency_cpr,
    )


def _optimisation_payload(result, config: WatercolourOptimisationConfig) -> dict:
    prediction = result.prediction
    return {
        "field_rgb": list(result.field_rgb),
        "field_hex": rgb_to_hex(result.field_rgb),
        "background_rgb": list(result.background_rgb),
        "background_hex": rgb_to_hex(result.background_rgb),
        "inner_rgb": list(result.inner_rgb),
        "inner_hex": rgb_to_hex(result.inner_rgb),
        "outer_rgb": list(result.outer_rgb),
        "outer_hex": rgb_to_hex(result.outer_rgb),
        "geometry": asdict(result.geometry),
        "chromatic_shift_uv": prediction.chromatic_shift_uv,
        "relative_luminance_shift": prediction.relative_luminance_shift,
        "predicted_rgb_unclipped": list(prediction.predicted_rgb_unclipped),
        "optimiser": {
            **asdict(config),
            "evaluations": result.evaluations,
            "nonfinite_evaluations": result.nonfinite_evaluations,
            "success": result.success,
            "message": result.message,
        },
    }


def _run_optimise(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    geometry = _geometry_from_args(parser, args)
    config = WatercolourOptimisationConfig(
        seed=args.seed,
        popsize=args.popsize,
        maxiter=args.maxiter,
        tol=args.tol,
        polish=not args.no_polish,
    )
    field_rgb = tuple(hex_to_rgb(args.field))
    background_rgb = None if args.background is None else tuple(hex_to_rgb(args.background))
    result = optimise_watercolour(
        field_rgb=field_rgb,
        background_rgb=background_rgb,
        geometry=geometry,
        config=config,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(_optimisation_payload(result, config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "figure3":
        write_figure3_bundle(args.output_dir)
        return 0
    if args.command == "figure4":
        write_figure4_report(args.output_dir)
        return 0
    if args.command == "optimise":
        _run_optimise(parser, args)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
