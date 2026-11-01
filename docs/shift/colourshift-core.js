// DOM-free browser port of ColourShift's corrected empirical white-point proxy.
// The public app deliberately keeps this module small and dependency-free.

export const MODEL_ID = "empirical-ciecam02-white-point-v1";
export const OBJECTIVE_TOTAL = "total";
export const OBJECTIVE_CHROMATIC = "chromatic";
const EMPIRICAL_DEFAULTS = {
  gridPoints: 12,
  minDelta: 10,
  minRgbDelta: 0,
  maxCandidates: 3,
  adaptingLuminance: 64,
  backgroundLuminousFactor: 20,
};

export function hexToRgb(hex) {
  if (!/^#?[0-9a-f]{6}$/i.test(hex)) throw new Error("Expected a 6-digit hex colour");
  const value = hex.replace(/^#/, "");
  return [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16) / 255);
}

export function rgbToHex(rgb) {
  return `#${rgb.map((channel) => Math.round(255 * channel).toString(16).padStart(2, "0")).join("")}`;
}

function multiply(matrix, vector) {
  return matrix.map((row) => row.reduce((sum, value, index) => sum + value * vector[index], 0));
}

function srgbToLinear(value) {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

export function rgbToXyz(rgb) {
  const [r, g, b] = rgb.map(srgbToLinear);
  return multiply([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.072175],
    [0.0193339, 0.119192, 0.9503041],
  ], [r, g, b]);
}

const CAT02 = [[0.7328, 0.4296, -0.1624], [-0.7036, 1.6975, 0.0061], [0.0030, 0.0136, 0.9834]];
// M_HPE * inverse(M_CAT02), used by the CIECAM02 forward model.
const CAT02_HPE = [[1.096124, -0.278869, 0.182745], [0.454369, 0.473533, 0.072098], [-0.009628, -0.005698, 1.015326]];
const D65 = [95.047, 100, 108.883];

function responseCompression(value, FL) {
  const sign = Math.sign(value);
  const absolute = (FL * Math.abs(value) / 100) ** 0.42;
  return sign * (400 * absolute / (absolute + 27.13)) + 2.3;
}

function ciecam02(rgb, backgroundRgb, config = {}) {
  const LA = config.adaptingLuminance;
  const Yb = config.backgroundLuminousFactor;
  const F = 1; const c = 0.69; const Nc = 1;
  const xyzWhite = rgbToXyz(backgroundRgb).map((value) => value * 100);
  const Yw = xyzWhite[1];
  const k = 1 / (5 * LA + 1);
  const FL = 0.2 * k ** 4 * 5 * LA + 0.1 * (1 - k ** 4) ** 2 * (5 * LA) ** (1 / 3);
  const n = Yb / Yw; const z = 1.48 + Math.sqrt(n); const Nbb = 0.725 * (1 / n) ** 0.2;
  const rgbWhite = multiply(CAT02, xyzWhite);
  const D = Math.max(0, Math.min(1, F * (1 - Math.exp((-LA - 42) / 92) / 3.6)));
  const discount = rgbWhite.map((value) => D * Yw / value + 1 - D);
  const whiteHpe = multiply(CAT02_HPE, rgbWhite.map((value, i) => value * discount[i])).map((value) => responseCompression(value, FL));
  const Aw = (2 * whiteHpe[0] + whiteHpe[1] + 0.05 * whiteHpe[2] - 0.305) * Nbb;
  const xyz = rgbToXyz(rgb).map((value) => value * 100);
  const hpe = multiply(CAT02_HPE, multiply(CAT02, xyz).map((value, i) => value * discount[i])).map((value) => responseCompression(value, FL));
  const [R, G, B] = hpe;
  const A = (2 * R + G + 0.05 * B - 0.305) * Nbb;
  const J = 100 * (A / Aw) ** (c * z);
  const a = (2 * R + G + 0.05 * B - 0.305) * Nbb;
  const b = (R + G - 2 * B) * Nbb / 9;
  const h = (Math.atan2(b, a) * 180 / Math.PI + 360) % 360;
  const et = 0.25 * (Math.cos((h + 2) * Math.PI / 180) + 3.8);
  const t = (50000 / 13 * Nc * et * Math.sqrt(a * a + b * b)) / (R + G + 21 * B / 20);
  const C = t ** 0.9 * Math.sqrt(J / 100) * (1.64 - 0.29 ** n) ** 0.73;
  const M = C * FL ** 0.25;
  const Jp = 1.7 * J / (1 + 0.007 * J);
  const Mp = Math.log1p(0.0228 * M) / 0.0228;
  return [Jp, Mp * Math.cos(h * Math.PI / 180), Mp * Math.sin(h * Math.PI / 180)];
}

export function cam02UcsCoordinates(rgb, backgroundRgb, config = {}) { return ciecam02(rgb, backgroundRgb, config); }

export function appearanceCoordinates(targetRgb, backgroundRgb, config = {}) {
  return ciecam02(targetRgb, backgroundRgb, config);
}

function distance(a, b, objective) {
  const start = objective === OBJECTIVE_CHROMATIC ? 1 : 0;
  return Math.hypot(...a.slice(start).map((value, index) => value - b[index + start]));
}

function rgbDistance(a, b) {
  return Math.hypot(...a.map((value, index) => value - b[index]));
}

function grid(points) {
  const values = Array.from({ length: points }, (_, index) => index / (points - 1));
  return values.flatMap((r) => values.flatMap((g) => values.map((b) => [r, g, b])));
}

export function search(mode, baseRgb, surroundRgb, options = {}) {
  const config = { ...EMPIRICAL_DEFAULTS, ...options };
  const objective = options.objective ?? OBJECTIVE_TOTAL;
  const reference = mode === "strongest-surrounds" ? appearanceCoordinates(baseRgb, baseRgb, config) : null;
  const scored = grid(config.gridPoints).map((candidate) => {
    const shifted = mode === "sensitive-bases" ? appearanceCoordinates(candidate, surroundRgb, config) : appearanceCoordinates(baseRgb, candidate, config);
    const baseline = mode === "sensitive-bases" ? appearanceCoordinates(candidate, candidate, config) : (reference ?? appearanceCoordinates(baseRgb, surroundRgb, config));
    const totalShift = distance(shifted, baseline, OBJECTIVE_TOTAL);
    const chromaticShift = distance(shifted, baseline, OBJECTIVE_CHROMATIC);
    return { rgb: candidate, totalShift, chromaticShift, shifted };
  }).filter((item) => Number.isFinite(item.totalShift) && Number.isFinite(item.chromaticShift)).sort((a, b) => (b[objective === OBJECTIVE_CHROMATIC ? "chromaticShift" : "totalShift"] - a[objective === OBJECTIVE_CHROMATIC ? "chromaticShift" : "totalShift"]) || rgbToHex(a.rgb).localeCompare(rgbToHex(b.rgb)));
  const candidates = [];
  for (const item of scored) {
    if (candidates.every((other) => distance(item.shifted, other.shifted, objective) >= config.minDelta && rgbDistance(item.rgb, other.rgb) >= config.minRgbDelta)) candidates.push(item);
    if (candidates.length >= config.maxCandidates) break;
  }
  return { schema: "colourshift-search-result-v1", model: MODEL_ID, mode, objective, config, inputs: { base: baseRgb, surround: surroundRgb }, candidates: candidates.map(({ rgb, totalShift, chromaticShift }) => ({ rgb, hex: rgbToHex(rgb), total_shift: totalShift, chromatic_shift: chromaticShift })) };
}
