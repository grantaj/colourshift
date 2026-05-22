import argparse
from pathlib import Path

from colourshift.core.algorithms import compute_appearance_difference, find_extreme_shift_colors
from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex
from colourshift.core.config import Config
from colourshift.io import save_comparison_image, save_solution_json

MODE_MAXIMAL_SURROUND_SHIFT = "maximal-surround-shift"
MODE_STRONGEST_SURROUNDS = "strongest-surrounds"
MODE_SENSITIVE_BASES = "sensitive-bases"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run ColourShift searches without opening the Tk interface.",
    )
    parser.add_argument(
        "--mode",
        choices=[
            MODE_MAXIMAL_SURROUND_SHIFT,
            MODE_STRONGEST_SURROUNDS,
            MODE_SENSITIVE_BASES,
        ],
        default=MODE_MAXIMAL_SURROUND_SHIFT,
        help="Search mode to run.",
    )
    parser.add_argument("--base", default="#950000", help="Base colour as a 6-digit hex value.")
    parser.add_argument(
        "--surround",
        default="#964301",
        help="Surround colour as a 6-digit hex value.",
    )
    parser.add_argument("--output", required=True, help="Path for the JSON result file.")
    parser.add_argument(
        "--figures-dir",
        help="Optional directory for generated comparison PNGs.",
    )
    parser.add_argument("--grid-points", type=int, default=12, help="RGB grid points per channel.")
    parser.add_argument(
        "--min-delta", type=float, default=10.0, help="Minimum candidate separation."
    )
    parser.add_argument(
        "--max-candidates", type=int, default=3, help="Maximum candidates to export."
    )
    parser.add_argument(
        "--viewing-condition", default="Average", help="CIECAM02 viewing condition."
    )
    parser.add_argument("--background-luminance", type=float, default=20.0)
    parser.add_argument("--adapting-luminance", type=float, default=64.0)
    return parser


def run_search(mode, base_hex, surround_hex, config):
    base_rgb = hex_to_rgb(base_hex)
    surround_rgb = hex_to_rgb(surround_hex)

    if mode == MODE_MAXIMAL_SURROUND_SHIFT:
        return compute_appearance_difference(base_rgb, surround_rgb, config=config)
    if mode == MODE_STRONGEST_SURROUNDS:
        return find_extreme_shift_colors(base_rgb, fixed_as_base=True, config=config)
    if mode == MODE_SENSITIVE_BASES:
        return find_extreme_shift_colors(surround_rgb, fixed_as_base=False, config=config)
    raise ValueError(f"Unsupported search mode: {mode}")


def write_figures(figures_dir, mode, base_hex, surround_hex, candidates):
    output_dir = Path(figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, candidate in enumerate(candidates, start=1):
        if mode == MODE_SENSITIVE_BASES:
            figure_base = rgb_to_hex(candidate.rgb)
            figure_surround = surround_hex
        else:
            figure_base = base_hex
            figure_surround = rgb_to_hex(candidate.rgb)
        save_comparison_image(
            output_dir / f"{index}.png",
            figure_base,
            surround_hex,
            figure_surround,
        )


def config_from_args(args):
    return Config(
        viewing_condition=args.viewing_condition,
        background_luminance=args.background_luminance,
        adapting_luminance=args.adapting_luminance,
        rgb_grid_points=args.grid_points,
        min_delta=args.min_delta,
        max_candidates=args.max_candidates,
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args)
    candidates = run_search(args.mode, args.base, args.surround, config)

    save_solution_json(
        args.output,
        args.base,
        args.surround,
        candidates,
        mode=args.mode,
        config=config,
    )

    if args.figures_dir:
        write_figures(args.figures_dir, args.mode, args.base, args.surround, candidates)


if __name__ == "__main__":
    main()
