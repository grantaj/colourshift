# Watercolour Explorer — design note

## Status

Implementation handoff for a standalone manual Watercolour Effect (WCE) stimulus explorer hosted by the existing GitHub Pages site.

This is not an optimiser and not a browser port of the Python WCE forward model. It is a visual studio/research tool for interactively drawing and exporting double-contour WCE stimuli.

The existing essay remains at docs/index.html.

The explorer should live at docs/watercolour/index.html so GitHub Pages serves it as a separate page while preserving the essay.

## 1. Goal

Provide an immediate browser-based way to manually explore how WCE stimulus geometry and contour colours change the visible effect.

The central workflow is:

1. look at a large clean WCE stimulus;
2. adjust geometry and colours with sliders/colour controls;
3. visually inspect the effect;
4. save the exact current stimulus as an SVG for later use in artwork, documentation, plotting, or fabrication.

There is no numerical optimisation and no model-predicted WCE score in v1.

## 2. Core controls

The first version should expose exactly the main variables needed for visual exploration.

### Geometry

- Ribbon width
  - one shared width applied equally to the inner and outer ribbons in v1;
  - should update continuously;
  - use SVG user units internally.

- Waviness amplitude
  - radial amplitude of the sinusoidal modulation of the enclosed boundary;
  - amplitude = 0 gives a circle;
  - larger values produce increasingly crenellated/wavy boundaries.

- Wavelength
  - because the contour is closed, the implementation should store an integer number of waves n around the boundary;
  - the UI may label this control Wavelength and show both the wave count and the derived approximate wavelength along the unmodulated circumference;
  - derived wavelength is lambda = 2 * pi * R / n;
  - this avoids a discontinuity at the closure seam.

- Overall scale
  - mean radius R of the enclosed shape;
  - controls the size of the enclosed field while preserving the chosen amplitude/ribbon settings.

### Colours

- Inner ribbon colour.
- Outer ribbon colour.

Use native browser colour inputs plus visible hex text.

For v1:
- enclosed field = white;
- page/stimulus background = white.

Do not add field/background colour controls until there is a clear artistic need; keep the first tool visually sparse.

## 3. Stimulus geometry

Use SVG as the authoritative representation.

The enclosed boundary is:

    r(theta) = R + A * sin(n * theta)

where:
- R = mean enclosed radius;
- A = waviness amplitude;
- n = integer waves around the boundary.

The boundary should be sampled densely enough that no visible faceting appears in normal browser viewing or the saved SVG.

A reasonable initial sample count is max(720, 48 * n), but implementation should verify smoothness.

## 4. Constructing the two ribbons

Do not fake the stimulus using two ordinary SVG strokes centred on the same path.

Construct explicit closed filled paths for:
1. the white enclosed field;
2. the inner ribbon;
3. the outer ribbon.

Use radial boundaries:

    r0(theta) = R + A * sin(n * theta)
    r1(theta) = r0(theta) + w
    r2(theta) = r0(theta) + 2w

where w is the shared ribbon width.

Render:
- field: area inside r0, white;
- inner ribbon: annulus between r0 and r1;
- outer ribbon: annulus between r1 and r2;
- background outside r2: white.

This radial-offset construction is the stimulus convention for the explorer. Do not claim that it is an exact Euclidean constant-normal-width offset under high curvature.

## 5. Default state

Suggested defaults:

    R                  = 180 SVG units
    ribbon width       = 10 SVG units
    amplitude          = 18 SVG units
    waves around shape = 10
    inner colour       = #ff8a16
    outer colour       = #4f2a78
    field              = #ffffff
    background         = #ffffff

The defaults may be adjusted by eye during implementation, but should begin with an obvious classic orange/purple WCE-like stimulus.

Add a Reset button that restores the canonical state.

## 6. Layout

This is a visual exploration tool, not an engineering dashboard.

Desktop:
- stimulus occupies roughly two-thirds of the useful width;
- controls occupy a restrained side column.

Mobile:
1. stimulus;
2. controls;
3. export action.

No horizontal page scrolling.

## 7. Visual design

Reuse the broad visual language of the existing Pages essay where useful, but keep the explorer quieter and more neutral.

Requirements:
- white stimulus/background area;
- no gradients behind the stimulus;
- restrained typography;
- controls should not compete visually with the artwork;
- preview remains crisp on high-DPI displays;
- no canvas rasterisation for the main preview.

Recommended structure:

    docs/
        index.html
        style.css
        watercolour/
            index.html
            watercolour.css
            watercolour.js

Avoid external UI frameworks. Plain HTML/CSS/JavaScript is sufficient.

## 8. Live interaction

Every control should update the SVG immediately on input, not only on change.

Show the current numeric value beside each slider.

Suggested exploratory ranges:

    scale R:       90 .. 240
    ribbon width:   2 .. 30
    amplitude:      0 .. 60
    waves n:        2 .. 30, integer steps

These are UI ranges, not scientific calibration bounds.

The implementation should prevent the stimulus from being cropped:
- use a generous fixed SVG viewBox;
- constrain R + A + 2w to fit;
- clamp invalid slider combinations rather than drawing clipped geometry.

## 9. Wavelength presentation

The user-facing concept is wavelength, but a closed radial sinusoid requires an integer number of cycles.

Therefore:
- store n as canonical state;
- label the slider Wavelength;
- display text such as "10 waves · wavelength ≈ 113 SVG units";
- compute lambda = 2 * pi * R / n;
- as R changes, the displayed wavelength changes even if n does not.

If this proves unintuitive, relabel it Waves / wavelength. Do not permit non-closing fractional-cycle geometry in v1.

## 10. Save as SVG — required

Save as SVG is a first-class requirement.

Add a prominent button:

    Save as SVG

It must download a standalone SVG reproducing the exact current stimulus state.

### Export requirements

The exported file must:
- be valid standalone SVG;
- use vector paths, not a screenshot or raster;
- contain the current inner/outer colours;
- contain the exact current geometry;
- preserve white field and white background;
- set an explicit viewBox;
- include no dependency on page CSS or JavaScript;
- open correctly in browsers and common vector editors;
- be deterministic for a given explorer state.

### Metadata

Include a human-readable metadata element containing the explorer parameters, for example JSON text with:
- radius;
- ribbon width;
- amplitude;
- waves;
- inner colour;
- outer colour.

This makes exported stimuli recoverable and reproducible later.

### Filename

Use a useful deterministic filename such as:

    watercolour-R180-w10-A18-n10-ff8a16-4f2a78.svg

Sanitise values for portability.

### Implementation

Recommended export flow:
1. clone or serialize the actual preview SVG;
2. ensure all appearance-critical attributes are inline SVG attributes;
3. insert/update metadata;
4. create a Blob with MIME type image/svg+xml;
5. create a temporary object URL;
6. trigger download through an anchor with download attribute;
7. revoke the object URL.

Do not maintain a separate export renderer. The preview SVG is the single source of truth so preview and saved result cannot drift apart.

## 11. Optional secondary export

Do not implement PNG export in the first PR unless it falls out trivially.

SVG is the required format because:
- hard edges remain exact;
- it scales cleanly for large paintings/printing;
- it can be edited in vector tools;
- it preserves the actual geometry instead of a screen raster.

## 12. GitHub Pages integration

The repository already publishes docs/.

The implementation should add the explorer under docs/watercolour/index.html.

Do not replace or disrupt docs/index.html.

Add a small discoverable Watercolour Explorer link from the existing essay, ideally near the existing discussion of tools or in lightweight site navigation.

The explorer should include a link back to the essay/home page.

All asset paths must work from the nested /watercolour/ path on GitHub Pages. Prefer relative paths that work both locally and on Pages.

## 13. No model or optimiser in v1

This page is for manual visual exploration only.

Do not:
- load Pyodide;
- run the Python WCE model;
- port the WCE model to JavaScript;
- show a numerical WCE strength score;
- include the colour optimiser;
- include a Find strongest colours action;
- claim any slider position is perceptually optimal.

The Python model/optimiser is a computational research instrument.

The web explorer is a studio instrument for looking.

## 14. Accessibility

Use native controls:
- range inputs;
- colour inputs;
- buttons;
- visible labels.

Requirements:
- all controls keyboard accessible;
- current numeric values visible as text;
- focus states visible;
- Save as SVG accessible by keyboard;
- controls approximately 44 px high on touch devices;
- colour values available as text, not represented only visually.

The stimulus SVG should have an accessible label such as "Interactive watercolour-effect double-contour stimulus".

## 15. State

Keep all explorer state in one plain JavaScript object, for example:

    const state = {
      radius: 180,
      ribbonWidth: 10,
      amplitude: 18,
      waves: 10,
      innerColour: "#ff8a16",
      outerColour: "#4f2a78",
    };

Do not require persistence in v1.

This structure leaves room for a later shareable query-string feature.

Do not use localStorage unless there is a specific later need.

## 16. Recommended JavaScript structure

Keep JavaScript small and functional.

Suggested flow:

    state
      -> validate/clamp
      -> build radial paths
      -> render SVG
      -> update displayed values

    save button
      -> serialize current SVG
      -> add metadata
      -> Blob/download

Suggested pure helpers:
- pointOnBoundary(radius, amplitude, waves, theta)
- sampleBoundary(radius, amplitude, waves, offset)
- closedPath(points)
- ringPath(innerPoints, outerPoints)
- render()
- serializeCurrentSvg()
- downloadSvg()

Pure geometry helpers should be easy to inspect and test.

## 17. Testing

Do not introduce a large frontend framework solely for this page.

The implementation agent must manually verify:
1. all controls update immediately;
2. amplitude = 0 produces a clean circle;
3. changing wavelength/waves produces a seamless closed contour;
4. ribbons remain adjacent with no gap;
5. colours update correctly;
6. large allowed values do not crop the stimulus;
7. Reset restores defaults;
8. Save as SVG downloads successfully;
9. saved SVG visually matches the preview;
10. saved SVG opens standalone after the browser page is closed;
11. metadata matches saved geometry and colours;
12. mobile layout remains usable;
13. existing docs/index.html still renders correctly.

Existing Python CI must remain green:

    uv run ruff check .
    uv run ruff format --check .
    uv run pytest

## 18. Acceptance criteria

The explorer is complete when:
- it is available as a separate GitHub Pages page under /watercolour/;
- existing essay remains the root index;
- a large SVG WCE stimulus dominates the interface;
- user can manually control ribbon width, waviness amplitude, wavelength/waves, enclosed-shape scale, inner colour and outer colour;
- all controls update live;
- amplitude zero is supported;
- contour closes cleanly for every wavelength setting;
- Reset works;
- Save as SVG works and reproduces the exact visible stimulus;
- exported SVG is standalone vector content with parameter metadata;
- no optimiser or WCE prediction model is included;
- desktop and mobile layouts are usable;
- existing repository tests remain green.

## 19. Likely files

Expected additions/changes:

    docs/watercolour/index.html
    docs/watercolour/watercolour.css
    docs/watercolour/watercolour.js
    docs/index.html

Do not modify the Python WCE model for this task.
