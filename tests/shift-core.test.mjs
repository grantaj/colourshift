import assert from "node:assert/strict";
import test from "node:test";
import { hexToRgb, rgbToHex, rgbToXyz, search } from "../docs/shift/colourshift-core.js";

test("shift core keeps hex and sRGB conversions deterministic", () => {
  assert.deepEqual(hexToRgb("#804020"), [128 / 255, 64 / 255, 32 / 255]);
  assert.equal(rgbToHex(hexToRgb("#804020")), "#804020");
  assert.deepEqual(rgbToXyz(hexToRgb("#804020")).map((value) => Number(value.toFixed(6))), [0.109972, 0.083616, 0.024010]);
});

test("search returns the portable result shape and both shift components", () => {
  const result = search("maximal-surround-shift", hexToRgb("#950000"), hexToRgb("#964301"), { gridPoints: 3, maxCandidates: 3, minDelta: 0.5, objective: "chromatic" });
  assert.equal(result.schema, "colourshift-search-result-v1");
  assert.equal(result.model, "empirical-ciecam02-white-point-v1");
  assert.equal(result.config.adaptingLuminance, 64);
  assert.equal(result.config.backgroundLuminousFactor, 20);
  assert.equal(result.config.minDelta, 0.5);
  assert.equal(result.candidates.length, 3);
  assert.ok(result.candidates.every((candidate) => candidate.total_shift >= candidate.chromatic_shift));
});

test("minimum separation selects distinct result sets", () => {
  const options = {
    objective: "chromatic",
    gridPoints: 7,
    minRgbDelta: 0.35,
    maxCandidates: 3,
  };
  const base = hexToRgb("#950000");
  const surround = hexToRgb("#964301");
  const lowSeparation = search("maximal-surround-shift", base, surround, { ...options, minDelta: 20 });
  const highSeparation = search("maximal-surround-shift", base, surround, { ...options, minDelta: 60 });

  assert.notDeepEqual(lowSeparation.candidates, highSeparation.candidates);
});

test("browser search matches the Tk empirical proxy ranking", () => {
  const result = search(
    "maximal-surround-shift",
    hexToRgb("#950000"),
    hexToRgb("#964301"),
    { objective: "chromatic", gridPoints: 12, minDelta: 10, maxCandidates: 3 },
  );

  assert.deepEqual(result.candidates.map((candidate) => candidate.hex), [
    "#8b00ff",
    "#005ce7",
    "#175ce7",
  ]);
});
