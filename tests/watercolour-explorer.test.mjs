import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildArcLengthMap,
  closedPath,
  greekCrossRadiusFactor,
  minimumShapeFactor,
} from "../docs/watercolour/geometry.mjs";

test("Greek cross has axial arms and recessed diagonals", () => {
  const axial = greekCrossRadiusFactor(0);
  const diagonal = greekCrossRadiusFactor(Math.PI / 4);

  assert.ok(axial > diagonal);
  assert.ok(axial > 0.8);
  assert.ok(diagonal < 0.6);
});

test("arc-length map is monotone and closes one normalized perimeter", () => {
  const map = buildArcLengthMap(2, 4096);

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
  assert.match(html, /href="watercolour\.css\?v=4"/);
  assert.match(html, /src="watercolour\.js\?v=10"/);
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






test("explorer exposes crenellation shape while preserving current geometry at 0.50", async () => {
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
  assert.match(geometry, /function cardinalSpline/);
  assert.match(geometry, /crenellationShape = 0\.5/);
  assert.match(geometry, /tangentScale/);
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

  assert.match(js, /from "\.\/geometry\.mjs\?v=3"/);
  assert.match(css, /@media \(max-width: 560px\)[\s\S]*input\[type="range"\][\s\S]*width: 76%/);
});
