# Watercolour Explorer — design note

## Purpose

A standalone manual Watercolour Effect (WCE) explorer hosted at:

    docs/watercolour/index.html

It is a studio/research viewing tool, not an optimiser and not a browser port of the Python WCE model.

The existing essay at `docs/index.html` is unrelated and must remain untouched and unlinked.

## Stimulus topology

The explorer uses an **annular white field** bounded on both sides by adjacent double contours.

This replaces the earlier single convex enclosure.

The white field occupies the band between:

    r_inner(theta)
    r_outer(theta)

with:

    r_outer(theta) = R + A sin(n theta)
    r_inner(theta) = (R - F) + A sin(n theta)

where:

- `R` = outer field radius / scale;
- `F` = white field width;
- `A` = waviness amplitude;
- `n` = integer waves around the closed contour.

The inducing colour faces the white band on **both** boundaries.

For ribbon width `w`:

Outer boundary, moving outward:

    white field
    inducing colour
    barrier colour
    white background

Inner boundary, moving inward:

    white field
    inducing colour
    barrier colour
    white centre

This orientation is essential. The white annulus is therefore flanked by the inducing contour on both sides.

Use explicit filled SVG paths rather than SVG strokes.

## Controls

Geometry:

- Scale
- Shape
  - one continuous slider;
  - 0 = circle;
  - 1 = square;
  - 2 = Greek cross / cruciform;
  - intermediate values smoothly interpolate between those shapes.
- Field width
- Ribbon width
- Amplitude
- Waves / wavelength

Colours:

- Inner = inducing colour
- Outer = barrier colour
- native colour picker plus editable hex value

Colour presets:

1. Blue / green
   - outer/barrier: `#3155A4`
   - inner/inducing: `#6EC66A`

2. Red / yellow
   - outer/barrier: `#A93232`
   - inner/inducing: `#F0CF45`

These are representative display colours for the remembered strong examples, not claimed source-measured RGB values.

## Default state

Use the blue/green annular example:

    outer field radius = 220
    field width        = 110
    ribbon width       = 8
    amplitude          = 15
    waves              = 12
    inner colour       = #6EC66A
    outer colour       = #3155A4

The default should show an obvious annular white band between an inner and outer double contour.

Default shape morph = 0 (circle).

The shape control must morph both annular boundaries coherently. Use a normalized radial shape factor so the inner and outer boundaries remain nested through the full circle → square → Greek-cross transition. The square stage uses the exact radial distance to an axis-aligned square with fixed circumradius. The cross endpoint is the exact radial boundary of the union of equal horizontal and vertical rectangles, normalized to a fixed circumradius, giving a true Greek-cross/cruciform outline with rectilinear arms and re-entrant corners.

Reset restores this state.

## Geometry constraints

The outer stimulus must fit inside the SVG viewBox:

    R + A + 2w <= maximum extent

The inner contour must not collapse into the centre:

    R - F - A - 2w >= centre margin

Invalid slider combinations should be clamped.

Use dense path sampling:

    sample count = max(1440, 96n)

Place the closed-path seam on a symmetry axis. Use cosine-phase waviness so the radial waviness derivative is zero at the seam; circle, square and Greek-cross base shapes also have zero radial slope there. This minimizes any artificial tangent kink at SVG path closure.

## Wavelength

Closed geometry stores an integer wave count `n`.

Display approximate wavelength using:

    lambda = 2 pi R / n

Do not permit fractional cycles that leave a seam.

## Presentation

The normal interface should remain sparse:

- title;
- large stimulus;
- compact controls;
- Focus view;
- Reset;
- Save SVG.

No explanatory essay copy is needed on the page.

## Focus view

Focus view is a first-class viewing mode.

When activated:

- hide title and controls;
- make the stimulus area fill the viewport;
- use a white page background;
- request the browser Fullscreen API when available;
- retain an in-tab distraction-free fallback if fullscreen is unavailable.

Exit focus view by:

- Escape; or
- clicking/tapping the stimulus field.

No visible exit control should remain over the stimulus.

## SVG export

Save SVG must serialize the exact live preview.

Requirements:

- standalone SVG;
- vector paths only;
- exact current geometry and colours;
- explicit viewBox;
- white centre, white annular field, white background;
- no CSS or JavaScript dependency;
- deterministic output;
- metadata containing:
  - topology;
  - shape morph value and human-readable shape position;
  - outer field radius;
  - field width;
  - derived inner field radius;
  - ribbon width;
  - amplitude;
  - waves;
  - inner colour;
  - outer colour.

Do not maintain a separate export renderer.

## Scope exclusions

Do not:

- run or port the Python WCE model;
- display a predicted WCE score;
- include the optimiser;
- claim any settings are perceptually optimal;
- link the explorer from the unrelated essay.

## Implementation files

    docs/watercolour/index.html
    docs/watercolour/watercolour.css
    docs/watercolour/watercolour.js

The Python WCE model is outside this task.
