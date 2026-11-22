import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildArcLengthMap,
  closedPath,
  minimumShapeFactor,
  superellipseRadiusFactor,
} from "../docs/watercolour/geometry.mjs";

test("shape family runs smoothly from circle to rounded square", () => {
  const circleAxis = superellipseRadiusFactor(0, 0);
  const circleDiagonal = superellipseRadiusFactor(Math.PI / 4, 0);
  const squareAxis = superellipseRadiusFactor(0, 1);
  const squareDiagonal = superellipseRadiusFactor(Math.PI / 4, 1);

  assert.ok(Math.abs(circleAxis - 1) < 1e-12);
  assert.ok(Math.abs(circleDiagonal - 1) < 1e-12);
  assert.ok(squareDiagonal > squareAxis);
  assert.ok(squareAxis > 0.8);
});

test("arc-length map is monotone and closes one normalized perimeter", () => {
  const map = buildArcLengthMap(1, 4096);

  assert.ok(map.perimeterFactor > 0);
  assert.equal(map.fractions[0], 0);

  for (let index = 1; index < map.fractions.length; index += 1) {
    assert.ok(map.fractions[index] > map.fractions[index - 1]);
  }

  assert.ok(map.fractions.at(-1) < 1);
  assert.ok(map.fractions.at(-1) > 0.99);
});


test("explorer stays focused on manual stimulus exploration", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(html, /id="preset-blue-green"/);
  assert.match(html, /id="preset-red-yellow"/);
  assert.ok(!html.includes("pairwise-test"));
  assert.ok(!html.includes("preset-blue-yellow"));
  assert.ok(!html.includes("preset-red-cyan"));
  assert.ok(!js.includes("openPairwiseTest"));
  assert.ok(!js.includes("blueYellow"));
  assert.ok(!js.includes("redCyan"));
  assert.match(html, /href="watercolour\.css\?v=6"/);
  assert.match(html, /src="watercolour\.js\?v=14"/);
});


test("explorer renders ribbons as layered strokes rather than offset polygons", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(html, /stroke-linejoin="round"/);
  assert.ok(!js.includes("offsetClosedPolyline"));
  assert.match(js, /stroke-width/);
  assert.match(js, /4 \* w/);
  assert.match(js, /2 \* w/);
});






test("explorer exposes crenellation shape with a sine reference at 0.50", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );
  const geometry = await readFile(
    new URL("../docs/watercolour/geometry.mjs", import.meta.url),
    "utf8",
  );

  assert.match(html, /id="crenellation-shape"/);
  assert.match(html, /min="0\.25"/);
  assert.match(html, /max="1\.25"/);
  assert.match(html, /value="0\.50"/);
  assert.match(js, /crenellationShape: 0\.5/);
  assert.match(js, /LIMITS\.crenellationShape/);
  assert.match(geometry, /export function crenellationWave/);
  assert.match(geometry, /crenellationShape = 0\.5/);
  assert.match(geometry, /Math\.sin\(phase\)/);
});




test("crenellation is a local periodic waveform independent of spline control count", async () => {
  const geometry = await readFile(
    new URL("../docs/watercolour/geometry.mjs", import.meta.url),
    "utf8",
  );

  assert.match(geometry, /export function crenellationWave/);
  assert.match(geometry, /Math\.sin\(phase\)/);
  assert.match(geometry, /Math\.sin\(3 \* phase\)/);
  assert.match(geometry, /2 \* Math\.PI \* waveCount \* arcFraction/);
  assert.ok(!geometry.includes("cardinalSpline"));
  assert.ok(!geometry.includes("controlCount"));
});

test("outer and inner boundaries use the same local waveform and absolute amplitude", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(js, /const outerWaves = state\.waves/);
  assert.match(
    js,
    /Math\.round\(state\.waves \* \(innerFieldRadius \/ outerFieldRadius\)\)/,
  );
  assert.equal(
    (js.match(/state\.amplitude,/g) || []).length >= 2,
    true,
  );
  assert.equal(
    (js.match(/state\.crenellationShape,/g) || []).length >= 2,
    true,
  );
});

test("explorer cache-busts geometry and mobile sliders leave scroll gutters", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );
  const css = await readFile(
    new URL("../docs/watercolour/watercolour.css", import.meta.url),
    "utf8",
  );

  assert.match(js, /from "\.\/geometry\.mjs\?v=4"/);
  assert.match(css, /@media \(max-width: 560px\)[\s\S]*input\[type="range"\][\s\S]*width: 76%/);
});


test("shape slider is limited to the smooth circle-square family", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );
  const geometry = await readFile(
    new URL("../docs/watercolour/geometry.mjs", import.meta.url),
    "utf8",
  );

  assert.match(html, /id="shape"[^>]*max="1"/);
  assert.match(js, /shape: \[0, 1\]/);
  assert.ok(!geometry.includes("greekCrossRadiusFactor"));
  assert.ok(!geometry.includes("GREEK_CROSS"));
  assert.match(geometry, /exponent = 2 \+ 2 \* t/);
});


test("colour exploration uses a nearby two-dimensional OKLab plane", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );
  const css = await readFile(
    new URL("../docs/watercolour/watercolour.css", import.meta.url),
    "utf8",
  );

  assert.match(html, /class="colour-dock"/);
  assert.match(html, /id="colour-plane"/);
  assert.match(html, /id="edit-inner"/);
  assert.match(html, /id="edit-outer"/);
  assert.ok(!html.includes('type="color"'));
  assert.ok(!html.includes('id="inner-hex"'));
  assert.match(js, /function rgbToOklab/);
  assert.match(js, /function gamutMappedOklab/);
  assert.match(js, /function bindColourPlane/);
  assert.match(css, /\.colour-plane[\s\S]*touch-action: none/);
});


test("colour dock marker follows pointer and exposes lightness control", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(html, /id="colour-lightness"/);
  assert.ok(!html.includes(">green<"));
  assert.ok(!html.includes(">red<"));
  assert.match(js, /function setColourPlaneMarkerPosition/);
  assert.match(js, /setColourPlaneMarkerPosition\(x, y\)/);
  assert.match(js, /function setSelectedLightness/);
  assert.match(js, /colourLightness\.addEventListener\("input"/);
});


test("colour-plane marker preserves the dragged position after gamut mapping", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(js, /const colourPlanePosition =/);
  assert.match(js, /colourPlanePosition\[selectedColourKey\] = \{ x, y \}/);
  assert.match(js, /const position = colourPlanePosition\[selectedColourKey\]/);
});


test("presets set colour, plane position, and lightness together", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(js, /function presetColourState/);
  assert.match(js, /fixedColourLightness\.innerColour = inner\.lightness/);
  assert.match(js, /fixedColourLightness\.outerColour = outer\.lightness/);
  assert.match(js, /colourPlanePosition\.innerColour = inner\.position/);
  assert.match(js, /colourPlanePosition\.outerColour = outer\.position/);
});


test("initial colour controls use the same complete state as presets", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(js, /function setCompleteColourState/);
  assert.match(
    js,
    /setCompleteColourState\(state\.innerColour, state\.outerColour\);/,
  );
  assert.match(
    js,
    /setCompleteColourState\(preset\.innerColour, preset\.outerColour\);/,
  );
});


test("startup, reset, and presets share the complete colour-state helper", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(
    js,
    /setCompleteColourState\(state\.innerColour, state\.outerColour\);[\s\S]*bindColourPlane\(\)/,
  );
  assert.match(
    js,
    /function resetExplorer\(\)[\s\S]*setCompleteColourState\(state\.innerColour, state\.outerColour\)/,
  );
  assert.match(
    js,
    /setCompleteColourState\(preset\.innerColour, preset\.outerColour\)/,
  );
  assert.ok(!js.includes("initialiseColourControlsFromState"));
});
