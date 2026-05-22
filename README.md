# ColourShift

ColourShift is a small Tk application for exploring how a colour's perceived
appearance changes when its surrounding colour changes. It uses CIECAM02 and
CAM02-UCS calculations through `colour-science` to search for surround/base
colour combinations that produce large perceptual shifts.

The app is intended as an exploratory tool: pick a base colour and a surround
colour, run one of the searches, then inspect or export the resulting colour
patches.

## Install
```bash
uv sync
```

## Run
```bash
uv run colourshift
```

## Using The App

The two swatches at the top are the current base colour and surround colour.
Click either swatch to choose a new colour. The preset selector loads a few
example base/surround pairs.

The main actions are:

- `Maximal Shift`: keeps the current base colour fixed and searches for
  alternative surround colours that make it appear most different from the
  current base/surround pair.
- `Sensitive Bases`: keeps the current surround colour fixed and searches for
  base colours whose appearance is strongly affected by that surround.
- `Strongest Surrounds`: keeps the current base colour fixed and searches for
  surround colours that most strongly affect its appearance.

The `Min ΔE` slider controls how different returned candidates must be from
each other in CAM02-UCS space. Higher values produce more separated, less
similar candidates.

Click a result patch to either compare it with the original pair or set it as
the current base/surround, depending on the active mode. `Save JSON` exports
the current colours and result candidates. Result comparisons can also be
exported as PNG images.

## Notes

The current search is a brute-force RGB grid search, so results are approximate
and depend on the configured grid density. The implementation is deliberately
small and interactive; deeper scientific context belongs in the accompanying
paper rather than this README.

## Development
```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
```
