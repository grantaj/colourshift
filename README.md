# ColourShift

ColourShift explores colour appearance and contextual colour effects. The main
Tk application uses the Zhu–Luo CAM16 simultaneous-contrast model to search for surround/base colour
combinations that produce large predicted perceptual shifts.

The repository also contains an experimental Watercolour Effect (WCE) forward
model. It combines a reproduction of the Cohen-Duwek & Spitzer edge/filling-in
model with a calibrated geometry term expressed in visual-angle units.

## Install

```bash
uv sync
```

## Run the application

```bash
uv run colourshift
```

The main actions are:

- `Maximal Shift`: keep the current base colour fixed and search alternative
  surrounds.
- `Sensitive Bases`: keep the surround fixed and search for sensitive bases.
- `Strongest Surrounds`: search surrounds that most strongly affect the base.

The `Min result separation` slider controls how different returned candidate
appearances must be from each other.

ColourShift has one supported model: `zhu-luo-cam16cc-2019-v1`, shown as
**Zhu–Luo CAM16 simultaneous contrast (2019)**. Target and background colours
are converted independently under a fixed D65 CAM16 adapting white. The model
then applies Zhu and Luo's fitted lightness and hue-contrast corrections.
The app defaults to the chromatic objective because the total objective is
normally dominated by the model's intentionally strong lightness correction.

Results can be ranked by total CAM16-UCS appearance shift or by chromatic
displacement alone. In chromatic mode, the minimum result-separation filter
also operates only in the chromatic `a′b′` plane, avoiding candidates that
differ mostly in lightness. Both scores are shown beneath each candidate.
The 2019 model does not include an independent chroma-contrast term. See the
[numerical contract](docs/colourshift-numerical-contract.md) for the precise
mapping, search semantics, and portable reference fixture.

The same searches are available from the command line:

```bash
uv run colourshift-export \
  --mode maximal-surround-shift \
  --base '#950000' \
  --surround '#964301' \
  --objective total \
  --output result.json
```

JSON results use the versioned `colourshift-search-result-v1` schema and
include the model, complete configuration, input snapshot, and both total and
chromatic scores for every candidate.

## Watercolour Effect model

The supported WCE API is:

```python
from colourshift.watercolour import WatercolourGeometry, predict_watercolour

prediction = predict_watercolour(
    field_rgb=(1.0, 1.0, 1.0),
    inner_rgb=(1.0, 0.72, 0.0),
    outer_rgb=(0.32, 0.36, 0.85),
    geometry=WatercolourGeometry(),
)

print(prediction.chromatic_shift_uv)
```

`chromatic_shift_uv` is the model's chromatic WCE score: displacement in
CIE 1976 u'v' chromaticity, matching the coordinate system used in the
published WCE comparison. Relative luminance shift is reported separately.
The model does not claim a unified perceptual ΔE because its uncalibrated
filling-in magnitude can produce appearance coordinates outside display gamut.
Raw opponent-channel magnitude is not treated as a perceptual distance.

The geometry model is restricted to the experimental domain used to calibrate
it: adjacent, visibly wavy double contours with total width 6–24 arcmin,
inner:outer width ratio 1:2–2:1, figure diameter 2.3–4.5 degrees, and 4–20 contour
cycles/revolution. Straight contours, separated contours, amplitude-dependent
predictions, and geometries outside these ranges are not currently supported.

Published reproduction utilities remain available for auditing the internal
edge model:

```bash
uv run colourshift-watercolour figure3
uv run colourshift-watercolour figure4
```

These are reproduction/audit commands, not alternate production models.

## Notes

Both the surround-colour search and the WCE model are exploratory scientific
tools rather than calibrated observer models. The WCE geometry functions encode
published psychophysical scales plus explicit modelling assumptions; calibration
tests for those functions are not independent validation.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
