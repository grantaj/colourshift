import argparse
from pathlib import Path

from colourshift.core.algorithms import (
    MODE_MAXIMAL_SURROUND_SHIFT,
    MODE_SENSITIVE_BASES,
    MODE_STRONGEST_SURROUNDS,
    MODES,
    OBJECTIVE_CHROMATIC,
    OBJECTIVE_TOTAL,
    SearchResult,
    find_maximal_surround_shift,
    find_sensitive_bases,
    find_strongest_surrounds,
)
from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex
from colourshift.core.config import Config
from colourshift.io import NEUTRAL_GREY_HEX, save_comparison_image, save_search_result_json


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run ColourShift's Zhu-Luo CAM16 simultaneous-contrast searches.",
    )
    parser.add_argument("--mode", choices=MODES, default=MODE_MAXIMAL_SURROUND_SHIFT)
    parser.add_argument("--base", default="#950000", help="Base colour as a 6-digit hex value.")
    parser.add_argument(
        "--surround", default="#964301", help="Surround colour as a 6-digit hex value."
    )
    parser.add_argument("--output", required=True, help="Path for the JSON result file.")
    parser.add_argument(
        "--objective",
        choices=[OBJECTIVE_TOTAL, OBJECTIVE_CHROMATIC],
        default=OBJECTIVE_CHROMATIC,
        help="Rank and separate candidates by total or chromatic appearance shift.",
    )
    parser.add_argument("--figures-dir", help="Optional directory for comparison PNGs.")
    parser.add_argument("--grid-points", type=int, default=12)
    parser.add_argument("--min-delta", type=float, default=1.0)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--viewing-condition", default="Average")
    parser.add_argument("--background-luminous-factor", type=float, default=20.0)
    parser.add_argument("--adapting-luminance", type=float, default=23.0)
    return parser


def run_search(mode, base_hex, surround_hex, config, objective):
    base_rgb = hex_to_rgb(base_hex)
    surround_rgb = hex_to_rgb(surround_hex)
    if mode == MODE_MAXIMAL_SURROUND_SHIFT:
        return find_maximal_surround_shift(
            base_rgb, surround_rgb, config=config, objective=objective
        )
    if mode == MODE_STRONGEST_SURROUNDS:
        return find_strongest_surrounds(base_rgb, config=config, objective=objective)
    if mode == MODE_SENSITIVE_BASES:
        return find_sensitive_bases(surround_rgb, config=config, objective=objective)
    raise ValueError(f"Unsupported search mode: {mode}")


def write_figures(figures_dir, result: SearchResult):
    output_dir = Path(figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_hex = rgb_to_hex(result.base_rgb) if result.base_rgb is not None else None
    surround_hex = rgb_to_hex(result.surround_rgb) if result.surround_rgb is not None else None

    for index, candidate in enumerate(result.candidates, start=1):
        candidate_hex = rgb_to_hex(candidate.rgb)
        if result.mode == MODE_SENSITIVE_BASES:
            left_base, left_surround = candidate_hex, NEUTRAL_GREY_HEX
            right_base, right_surround = candidate_hex, surround_hex
        elif result.mode == MODE_STRONGEST_SURROUNDS:
            left_base = left_surround = right_base = base_hex
            right_surround = candidate_hex
        else:
            left_base = right_base = base_hex
            left_surround, right_surround = surround_hex, candidate_hex
        save_comparison_image(
            output_dir / f"{index}.png",
            left_base,
            left_surround,
            right_base,
            right_surround,
        )


def config_from_args(args):
    return Config(
        viewing_condition=args.viewing_condition,
        background_luminous_factor=args.background_luminous_factor,
        adapting_luminance=args.adapting_luminance,
        rgb_grid_points=args.grid_points,
        min_delta=args.min_delta,
        max_candidates=args.max_candidates,
    )


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = run_search(
        args.mode,
        args.base,
        args.surround,
        config_from_args(args),
        args.objective,
    )
    save_search_result_json(args.output, result)
    if args.figures_dir:
        write_figures(args.figures_dir, result)


if __name__ == "__main__":
    main()
