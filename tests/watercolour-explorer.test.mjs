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
  assert.match(html, /href="watercolour\.css\?v=8"/);
  assert.match(html, /src="watercolour\.js\?v=20"/);
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


test("initial colour controls visibly match the default inner colour before JavaScript runs", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );

  assert.match(
    html,
    /id="colour-plane-marker"[^>]*left: 25\.513%; top: 31\.543%/,
  );
  assert.match(
    html,
    /id="colour-lightness"[^>]*[\s\S]*?value="0\.7495"/,
  );
  assert.match(
    html,
    /id="colour-lightness-value"[^>]*>0\.75<\/output>/,
  );
});


test("colour plane renders synchronously as inline SVG", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(html, /<svg[\s\S]*id="colour-plane"/);
  assert.ok(!html.includes("<canvas"));
  assert.ok(!js.includes("getContext"));
  assert.ok(!js.includes("putImageData"));
  assert.ok(!js.includes("backgroundImage"));
  assert.ok(!js.includes("encodeURIComponent(svg)"));
  assert.match(js, /function ensureColourPlaneCells/);
  assert.match(js, /createElementNS\(SVG_NS, "rect"\)/);
  assert.match(js, /rect\.setAttribute\(\s*"fill"/);
});




test("initial and switched colour planes use the same synchronous lightness renderer", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(js, /function syncColourDock\(\)[\s\S]*drawColourPlane\(\)/);
  assert.match(js, /function selectColour\(key\)[\s\S]*syncColourDock\(\)/);
  assert.ok(!js.includes("requestAnimationFrame"));
});


test("colour plane has no cached lightness state", async () => {
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.ok(!js.includes("renderedPlaneLightness"));
  assert.match(js, /function syncColourDock\(\)[\s\S]*drawColourPlane\(\)/);
  assert.match(js, /function drawColourPlane\(\)[\s\S]*fixedColourLightness\[selectedColourKey\]/);
});


test("default colour plane is painted before JavaScript and remains live", async () => {
  const html = await readFile(new URL("../docs/watercolour/index.html", import.meta.url), "utf8");
  const js = await readFile(new URL("../docs/watercolour/watercolour.js", import.meta.url), "utf8");
  const plane = html.match(/<svg\s+id="colour-plane"[\s\S]*?<\/svg>/)?.[0];
  assert.ok(plane, "inline colour plane must exist");
  const cells = [...plane.matchAll(/<rect\s+[^>]*data-colour-plane-x="(\d+)" data-colour-plane-y="(\d+)"[^>]*>/g)];
  assert.equal(cells.length, 576, "render all 24×24 cells in HTML");
  const points = new Set(cells.map(cell => cell[1] + "," + cell[2]));
  assert.equal(points.size, 576, "cells must cover all 24×24 positions exactly once");
  for (const [, x, y] of cells) {
    assert.ok(Number(x) >= 0 && Number(x) < 24);
    assert.ok(Number(y) >= 0 && Number(y) < 24);
  }
  assert.match(plane, /<rect[^>]*fill="#6aca00"[^>]*data-colour-plane-x="0" data-colour-plane-y="0"/);
  assert.match(html, /id="colour-lightness"[^>]*[\s\S]*?value="0\.7495"/);
  assert.match(js, /function drawColourPlane\(\)[\s\S]*?rect\.setAttribute\(\s*"fill"/);
  assert.match(js, /function syncColourDock\(\)[\s\S]*?drawColourPlane\(\)/);
});


test("lightness editing is isolated to selected colour and clearly labelled", async () => {
  const html = await readFile(new URL("../docs/watercolour/index.html", import.meta.url), "utf8");
  const js = await readFile(new URL("../docs/watercolour/watercolour.js", import.meta.url), "utf8");
  const css = await readFile(new URL("../docs/watercolour/watercolour.css", import.meta.url), "utf8");

  assert.match(html, /id="edit-inner" class="colour-target active"[^>]*aria-pressed="true"/);
  assert.match(html, /id="edit-outer" class="colour-target"[^>]*aria-pressed="false"/);
  assert.match(html, /id="colour-lightness-label" for="colour-lightness">Inner lightness/);
  assert.match(html, /id="edit-inner"[^>]*aria-pressed="true"[\s\S]*?class="target-selection-dot"/);
  assert.match(css, /\.colour-target\[aria-pressed="true"\] \.target-selection-dot::after \{\s*opacity: 1/);
  assert.match(js, /function syncSelectedColourOnly\(\)/);
  assert.match(js, /\["outerInducing", "innerInducing"\]|\[elements\.outerInducing, elements\.innerInducing\]/);
  assert.match(js, /\[elements\.outerBarrier, elements\.innerBarrier\]/);
  assert.match(js, /function setSelectedLightness\(value\)[\s\S]*?syncSelectedColourOnly\(\)/);
  assert.match(js, /function resetExplorer\(\) \{\s*selectedColourKey = "innerColour"/);
});
