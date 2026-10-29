import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  DEFAULT_MITER_LIMIT,
  buildArcLengthMap,
  closedPath,
  greekCrossRadiusFactor,
  minimumShapeFactor,
  offsetClosedPolyline,
  ringPath,
} from "../docs/watercolour/geometry.mjs";

test("extreme explorer controls retain a feasible field width", () => {
  const centreMargin = 20;
  const maxExtent = 360;
  const radiusMaximum = 240;
  const fieldWidthMinimum = 50;
  const amplitudeMaximum = 35;
  const ribbonWidthMaximum = 12;
  const shape = 2;

  const minimumFactor = minimumShapeFactor(shape);
  const innerClearance =
    centreMargin +
    amplitudeMaximum +
    2 * ribbonWidthMaximum * DEFAULT_MITER_LIMIT;
  const minimumInnerBaseRadius = innerClearance / minimumFactor;
  const minimumOuterRadius =
    fieldWidthMinimum + minimumInnerBaseRadius;
  const maximumOuterRadius =
    maxExtent -
    amplitudeMaximum -
    2 * ribbonWidthMaximum * DEFAULT_MITER_LIMIT;

  assert.ok(minimumOuterRadius <= radiusMaximum);
  assert.ok(minimumOuterRadius <= maximumOuterRadius);
  assert.ok(
    radiusMaximum - minimumInnerBaseRadius >= fieldWidthMinimum,
  );
});

test("mitered normal offset preserves constant-width square sides", () => {
  const square = [
    [-50, -50],
    [50, -50],
    [50, 50],
    [-50, 50],
  ];

  assert.deepEqual(offsetClosedPolyline(square, 10), [
    [-60, -60],
    [60, -60],
    [60, 60],
    [-60, 60],
  ]);

  assert.deepEqual(offsetClosedPolyline(square, -10), [
    [-40, -40],
    [40, -40],
    [40, 40],
    [-40, 40],
  ]);
});

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

test("SVG path helpers produce two closed subpaths for a ribbon", () => {
  const inner = [
    [1, 1],
    [2, 1],
    [2, 2],
    [1, 2],
  ];
  const outer = [
    [0, 0],
    [3, 0],
    [3, 3],
    [0, 3],
  ];

  const path = ringPath(inner, outer);

  assert.match(closedPath(inner), /^M /);
  assert.equal((path.match(/ Z/g) ?? []).length, 2);
  assert.ok(!path.includes("NaN"));
  assert.ok(!path.includes("Infinity"));
});


test("explorer does not display canonical-model prediction scores", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );

  assert.ok(!html.includes("Δu"));
  assert.ok(!html.includes("ΔY"));
  assert.match(html, /type="module" src="watercolour\.js\?v=4"/);
});


test("explorer exposes empirical high-contrast presets without an optimum claim", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  for (const id of [
    "preset-blue-yellow",
    "preset-yellow-blue",
    "preset-magenta-green",
    "preset-green-magenta",
    "preset-red-cyan",
    "preset-cyan-red",
  ]) {
    assert.ok(html.includes(`id="${id}"`));
  }

  for (const pair of [
    ['innerColour: "#0000ff"', 'outerColour: "#ffff00"'],
    ['innerColour: "#ffff00"', 'outerColour: "#0000ff"'],
    ['innerColour: "#ff00ff"', 'outerColour: "#00ff00"'],
    ['innerColour: "#00ff00"', 'outerColour: "#ff00ff"'],
    ['innerColour: "#ff0000"', 'outerColour: "#00ffff"'],
    ['innerColour: "#00ffff"', 'outerColour: "#ff0000"'],
  ]) {
    assert.ok(js.includes(pair[0]));
    assert.ok(js.includes(pair[1]));
  }

  assert.ok(!html.includes("Model optimum"));
  assert.ok(!js.includes("modelOptimum"));
});


test("pairwise test page reuses explorer geometry and records eight presets", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/compare.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/compare.js", import.meta.url),
    "utf8",
  );

  assert.match(html, /Which white annulus shows the stronger apparent colour shift/);
  assert.match(html, /compare\.js\?v=1/);
  assert.match(js, /new URLSearchParams\(window\.location\.search\)/);
  assert.match(js, /buildArcLengthMap/);
  assert.match(js, /offsetClosedPolyline/);
  assert.match(js, /ringPath/);
  assert.equal((js.match(/\{ name:/g) ?? []).length, 8);
  assert.match(js, /Winner:/);
  assert.match(js, /Choices:/);
});

test("explorer offers pairwise test using current geometry", async () => {
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.ok(html.includes('id="pairwise-test"'));
  assert.match(js, /function openPairwiseTest\(\)/);
  for (const key of [
    "radius",
    "fieldWidth",
    "shape",
    "ribbonWidth",
    "amplitude",
    "waves",
  ]) {
    assert.ok(js.includes(key));
  }
  assert.match(js, /compare\.html\?/);
});


test("explorer pages version mutable CSS and JavaScript assets", async () => {
  const indexHtml = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const compareHtml = await readFile(
    new URL("../docs/watercolour/compare.html", import.meta.url),
    "utf8",
  );

  assert.match(indexHtml, /href="watercolour\.css\?v=2"/);
  assert.match(indexHtml, /src="watercolour\.js\?v=4"/);
  assert.match(compareHtml, /href="watercolour\.css\?v=2"/);
  assert.match(compareHtml, /src="compare\.js\?v=1"/);
});
