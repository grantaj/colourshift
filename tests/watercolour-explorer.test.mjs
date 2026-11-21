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
  assert.match(html, /href="watercolour\.css\?v=3"/);
  assert.match(html, /src="watercolour\.js\?v=7"/);
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



test("crenellation uses a single pure sinusoid and integer closed wave counts", async () => {
  const geometry = await readFile(
    new URL("../docs/watercolour/geometry.mjs", import.meta.url),
    "utf8",
  );
  const html = await readFile(
    new URL("../docs/watercolour/index.html", import.meta.url),
    "utf8",
  );
  const js = await readFile(
    new URL("../docs/watercolour/watercolour.js", import.meta.url),
    "utf8",
  );

  assert.match(geometry, /Math\.cos\(wavePhase\)/);
  assert.ok(!geometry.includes("lowerWave"));
  assert.ok(!geometry.includes("upperWave"));
  assert.ok(!geometry.includes("blend"));
  assert.match(html, /id="waves"[^>]*step="1"/);
  assert.match(js, /Math\.round\([\s\S]*Number\(state\.waves\)/);
  assert.match(js, /const outerWaves = state\.waves/);
  assert.match(js, /Math\.round\(state\.waves \* \(innerFieldRadius \/ outerFieldRadius\)\)/);
});
