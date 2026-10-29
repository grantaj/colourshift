"use strict";

import {
  DEFAULT_MITER_LIMIT,
  buildArcLengthMap,
  clamp,
  minimumShapeFactor,
  offsetClosedPolyline,
  ringPath,
  sampleBoundary,
  translatePoints,
} from "./geometry.mjs";

const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWBOX_SIZE = 760;
const CENTRE = VIEWBOX_SIZE / 2;
const EDGE_MARGIN = 20;
const CENTRE_MARGIN = 20;
const MAX_EXTENT = CENTRE - EDGE_MARGIN;

const LIMITS = Object.freeze({
  radius: [150, 240],
  fieldWidth: [50, 150],
  shape: [0, 2],
  ribbonWidth: [2, 12],
  amplitude: [0, 35],
  waves: [2, 30],
});

const PRESETS = Object.freeze({
  blueGreen: Object.freeze({
    innerColour: "#6ec66a",
    outerColour: "#3155a4",
  }),
  redYellow: Object.freeze({
    innerColour: "#f0cf45",
    outerColour: "#a93232",
  }),
  blueYellow: Object.freeze({
    innerColour: "#0000ff",
    outerColour: "#ffff00",
  }),
  yellowBlue: Object.freeze({
    innerColour: "#ffff00",
    outerColour: "#0000ff",
  }),
  magentaGreen: Object.freeze({
    innerColour: "#ff00ff",
    outerColour: "#00ff00",
  }),
  greenMagenta: Object.freeze({
    innerColour: "#00ff00",
    outerColour: "#ff00ff",
  }),
  redCyan: Object.freeze({
    innerColour: "#ff0000",
    outerColour: "#00ffff",
  }),
  cyanRed: Object.freeze({
    innerColour: "#00ffff",
    outerColour: "#ff0000",
  }),
});

const DEFAULT_STATE = Object.freeze({
  radius: 220,
  fieldWidth: 110,
  shape: 0,
  ribbonWidth: 8,
  amplitude: 15,
  waves: 12,
  innerColour: PRESETS.blueGreen.innerColour,
  outerColour: PRESETS.blueGreen.outerColour,
});

const state = { ...DEFAULT_STATE };

const elements = {
  svg: document.getElementById("stimulus"),
  stage: document.getElementById("stage"),
  field: document.getElementById("field"),
  outerBarrier: document.getElementById("outer-barrier"),
  outerInducing: document.getElementById("outer-inducing"),
  innerBarrier: document.getElementById("inner-barrier"),
  innerInducing: document.getElementById("inner-inducing"),
  radius: document.getElementById("radius"),
  fieldWidth: document.getElementById("field-width"),
  shape: document.getElementById("shape"),
  ribbonWidth: document.getElementById("ribbon-width"),
  amplitude: document.getElementById("amplitude"),
  waves: document.getElementById("waves"),
  radiusValue: document.getElementById("radius-value"),
  fieldWidthValue: document.getElementById("field-width-value"),
  shapeValue: document.getElementById("shape-value"),
  ribbonWidthValue: document.getElementById("ribbon-width-value"),
  amplitudeValue: document.getElementById("amplitude-value"),
  wavesValue: document.getElementById("waves-value"),
  innerColour: document.getElementById("inner-colour"),
  outerColour: document.getElementById("outer-colour"),
  innerHex: document.getElementById("inner-hex"),
  outerHex: document.getElementById("outer-hex"),
  presetBlueGreen: document.getElementById("preset-blue-green"),
  presetRedYellow: document.getElementById("preset-red-yellow"),
  presetBlueYellow: document.getElementById("preset-blue-yellow"),
  presetYellowBlue: document.getElementById("preset-yellow-blue"),
  presetMagentaGreen: document.getElementById("preset-magenta-green"),
  presetGreenMagenta: document.getElementById("preset-green-magenta"),
  presetRedCyan: document.getElementById("preset-red-cyan"),
  presetCyanRed: document.getElementById("preset-cyan-red"),
  pairwiseTest: document.getElementById("pairwise-test"),
  focusView: document.getElementById("focus-view"),
  reset: document.getElementById("reset"),
  saveSvg: document.getElementById("save-svg"),
};

function clampState() {
  state.shape = clamp(
    Number(state.shape),
    LIMITS.shape[0],
    LIMITS.shape[1],
  );
  state.ribbonWidth = clamp(
    Number(state.ribbonWidth),
    LIMITS.ribbonWidth[0],
    LIMITS.ribbonWidth[1],
  );
  state.amplitude = clamp(
    Number(state.amplitude),
    LIMITS.amplitude[0],
    LIMITS.amplitude[1],
  );
  state.waves = Math.round(
    clamp(Number(state.waves), LIMITS.waves[0], LIMITS.waves[1]),
  );

  const minimumFactor = minimumShapeFactor(state.shape);
  const innerClearance =
    CENTRE_MARGIN +
    state.amplitude +
    2 * state.ribbonWidth * DEFAULT_MITER_LIMIT;
  const minimumInnerBaseRadius = innerClearance / minimumFactor;

  const minimumOuterRadius =
    LIMITS.fieldWidth[0] + minimumInnerBaseRadius;
  const maximumOuterRadius =
    MAX_EXTENT -
    state.amplitude -
    2 * state.ribbonWidth * DEFAULT_MITER_LIMIT;

  const radiusMinimum = Math.max(LIMITS.radius[0], minimumOuterRadius);
  const radiusMaximum = Math.min(LIMITS.radius[1], maximumOuterRadius);

  if (radiusMinimum > radiusMaximum) {
    throw new RangeError("Explorer geometry limits are infeasible");
  }

  state.radius = clamp(
    Number(state.radius),
    radiusMinimum,
    radiusMaximum,
  );

  const maximumFieldWidth =
    state.radius - minimumInnerBaseRadius;
  const fieldWidthMaximum = Math.min(
    LIMITS.fieldWidth[1],
    maximumFieldWidth,
  );

  if (fieldWidthMaximum < LIMITS.fieldWidth[0]) {
    throw new RangeError("Explorer field-width limits are infeasible");
  }

  state.fieldWidth = clamp(
    Number(state.fieldWidth),
    LIMITS.fieldWidth[0],
    fieldWidthMaximum,
  );
}

function formatValue(value, fractionDigits) {
  return Number(value.toFixed(fractionDigits)).toString();
}

function shapeLabel(shape) {
  if (shape <= 0.01) {
    return "Circle";
  }
  if (Math.abs(shape - 1) <= 0.01) {
    return "Square";
  }
  if (shape >= 1.99) {
    return "Greek cross";
  }
  if (shape < 1) {
    return "Circle → square · " + Math.round(shape * 100) + "%";
  }
  return "Square → cross · " + Math.round((shape - 1) * 100) + "%";
}

function activePresetName() {
  for (const [name, preset] of Object.entries(PRESETS)) {
    if (
      state.innerColour === preset.innerColour &&
      state.outerColour === preset.outerColour
    ) {
      return name;
    }
  }
  return null;
}

function syncControlsFromState() {
  elements.radius.value = String(state.radius);
  elements.fieldWidth.value = String(state.fieldWidth);
  elements.shape.value = String(state.shape);
  elements.ribbonWidth.value = String(state.ribbonWidth);
  elements.amplitude.value = String(state.amplitude);
  elements.waves.value = String(state.waves);

  elements.innerColour.value = state.innerColour;
  elements.outerColour.value = state.outerColour;
  elements.innerHex.value = state.innerColour.toUpperCase();
  elements.outerHex.value = state.outerColour.toUpperCase();

  elements.innerHex.setAttribute("aria-invalid", "false");
  elements.outerHex.setAttribute("aria-invalid", "false");

  elements.radiusValue.value = formatValue(state.radius, 0);
  elements.fieldWidthValue.value = formatValue(state.fieldWidth, 0);
  elements.shapeValue.value = shapeLabel(state.shape);
  elements.ribbonWidthValue.value = formatValue(state.ribbonWidth, 0);
  elements.amplitudeValue.value = formatValue(state.amplitude, 0);

  const count = Math.max(1440, 96 * state.waves);
  const arcMap = buildArcLengthMap(state.shape, count);
  const perimeter = arcMap.perimeterFactor * state.radius;
  const wavelength = perimeter / state.waves;
  elements.wavesValue.value =
    state.waves + " · λ ≈ " + formatValue(wavelength, 0);

  const activePreset = activePresetName();
  for (const [name, element] of [
    ["blueGreen", elements.presetBlueGreen],
    ["redYellow", elements.presetRedYellow],
    ["blueYellow", elements.presetBlueYellow],
    ["yellowBlue", elements.presetYellowBlue],
    ["magentaGreen", elements.presetMagentaGreen],
    ["greenMagenta", elements.presetGreenMagenta],
    ["redCyan", elements.presetRedCyan],
    ["cyanRed", elements.presetCyanRed],
  ]) {
    element.classList.toggle("active", activePreset === name);
  }
}

function render() {
  clampState();

  const outerFieldRadius = state.radius;
  const innerFieldRadius = state.radius - state.fieldWidth;
  const w = state.ribbonWidth;
  const count = Math.max(1440, 96 * state.waves);
  const arcMap = buildArcLengthMap(state.shape, count);
  const arcFractions = arcMap.fractions;

  const outerFieldLocal = sampleBoundary(
    outerFieldRadius,
    state.amplitude,
    state.waves,
    state.shape,
    arcFractions,
  );
  const innerFieldLocal = sampleBoundary(
    innerFieldRadius,
    state.amplitude,
    state.waves,
    state.shape,
    arcFractions,
  );

  const outerInducingLocal = offsetClosedPolyline(
    outerFieldLocal,
    w,
  );
  const outerBarrierLocal = offsetClosedPolyline(
    outerFieldLocal,
    2 * w,
  );
  const innerInducingLocal = offsetClosedPolyline(
    innerFieldLocal,
    -w,
  );
  const innerBarrierLocal = offsetClosedPolyline(
    innerFieldLocal,
    -2 * w,
  );

  const outerField = translatePoints(outerFieldLocal, CENTRE, CENTRE);
  const innerField = translatePoints(innerFieldLocal, CENTRE, CENTRE);
  const outerInducing = translatePoints(
    outerInducingLocal,
    CENTRE,
    CENTRE,
  );
  const outerBarrier = translatePoints(
    outerBarrierLocal,
    CENTRE,
    CENTRE,
  );
  const innerInducing = translatePoints(
    innerInducingLocal,
    CENTRE,
    CENTRE,
  );
  const innerBarrier = translatePoints(
    innerBarrierLocal,
    CENTRE,
    CENTRE,
  );

  elements.field.setAttribute(
    "d",
    ringPath(innerField, outerField),
  );
  elements.field.setAttribute("fill", "#ffffff");

  elements.outerInducing.setAttribute(
    "d",
    ringPath(outerField, outerInducing),
  );
  elements.outerInducing.setAttribute("fill", state.innerColour);

  elements.outerBarrier.setAttribute(
    "d",
    ringPath(outerInducing, outerBarrier),
  );
  elements.outerBarrier.setAttribute("fill", state.outerColour);

  elements.innerInducing.setAttribute(
    "d",
    ringPath(innerInducing, innerField),
  );
  elements.innerInducing.setAttribute("fill", state.innerColour);

  elements.innerBarrier.setAttribute(
    "d",
    ringPath(innerBarrier, innerInducing),
  );
  elements.innerBarrier.setAttribute("fill", state.outerColour);

  syncControlsFromState();
}

function bindRange(element, key) {
  element.addEventListener("input", function () {
    state[key] = Number(element.value);
    render();
  });
}

function normaliseHex(value) {
  const trimmed = value.trim();
  if (!/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
    return null;
  }
  return trimmed.toLowerCase();
}

function bindColourPicker(picker, textInput, key) {
  picker.addEventListener("input", function () {
    state[key] = picker.value.toLowerCase();
    render();
  });

  textInput.addEventListener("input", function () {
    const colour = normaliseHex(textInput.value);

    if (colour === null) {
      textInput.setAttribute("aria-invalid", "true");
      return;
    }

    state[key] = colour;
    picker.value = colour;
    textInput.setAttribute("aria-invalid", "false");
    render();
  });

  textInput.addEventListener("blur", function () {
    if (normaliseHex(textInput.value) === null) {
      textInput.value = state[key].toUpperCase();
      textInput.setAttribute("aria-invalid", "false");
    }
  });
}

function applyPreset(preset) {
  state.innerColour = preset.innerColour;
  state.outerColour = preset.outerColour;
  render();
}

async function enterFocusView() {
  document.body.classList.add("focus-mode");

  if (
    document.fullscreenElement === null &&
    document.documentElement.requestFullscreen
  ) {
    try {
      await document.documentElement.requestFullscreen();
    } catch {
      // Focus mode still works inside the browser viewport.
    }
  }
}

async function exitFocusView() {
  document.body.classList.remove("focus-mode");

  if (document.fullscreenElement !== null && document.exitFullscreen) {
    try {
      await document.exitFullscreen();
    } catch {
      // Page UI is already restored.
    }
  }
}

function syncFocusMode() {
  if (document.fullscreenElement === null) {
    document.body.classList.remove("focus-mode");
  }
}

function resetExplorer() {
  Object.assign(state, DEFAULT_STATE);
  render();
}

function openPairwiseTest() {
  clampState();
  const params = new URLSearchParams({
    radius: String(state.radius),
    fieldWidth: String(state.fieldWidth),
    shape: String(state.shape),
    ribbonWidth: String(state.ribbonWidth),
    amplitude: String(state.amplitude),
    waves: String(state.waves),
  });
  window.location.href = "compare.html?" + params.toString();
}

function exportMetadata() {
  return {
    tool: "ColourShift Watercolour Explorer",
    version: 2,
    topology: "annular-field-double-boundary",
    outerFieldRadius: state.radius,
    fieldWidth: state.fieldWidth,
    shapeMorph: state.shape,
    shape: shapeLabel(state.shape),
    innerFieldRadius: state.radius - state.fieldWidth,
    ribbonWidth: state.ribbonWidth,
    amplitude: state.amplitude,
    waves: state.waves,
    innerColour: state.innerColour,
    outerColour: state.outerColour,
    fieldColour: "#ffffff",
    backgroundColour: "#ffffff",
  };
}

function serialiseCurrentSvg() {
  const clone = elements.svg.cloneNode(true);
  clone.setAttribute("xmlns", SVG_NS);
  clone.setAttribute("width", String(VIEWBOX_SIZE));
  clone.setAttribute("height", String(VIEWBOX_SIZE));

  const existingMetadata = clone.querySelector("metadata");
  if (existingMetadata !== null) {
    existingMetadata.remove();
  }

  const metadata = document.createElementNS(SVG_NS, "metadata");
  metadata.setAttribute("id", "colourshift-watercolour-parameters");
  metadata.textContent = JSON.stringify(exportMetadata(), null, 2);

  const title = clone.querySelector("title");
  if (title !== null) {
    clone.insertBefore(metadata, title.nextSibling);
  } else {
    clone.insertBefore(metadata, clone.firstChild);
  }

  const serializer = new XMLSerializer();
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    serializer.serializeToString(clone) +
    "\n"
  );
}

function filenameNumber(value) {
  return Number(value)
    .toFixed(3)
    .replace(/\.?0+$/, "")
    .replace(".", "p");
}

function exportFilename() {
  return (
    "watercolour-annulus-R" +
    filenameNumber(state.radius) +
    "-F" +
    filenameNumber(state.fieldWidth) +
    "-S" +
    filenameNumber(state.shape) +
    "-w" +
    filenameNumber(state.ribbonWidth) +
    "-A" +
    filenameNumber(state.amplitude) +
    "-n" +
    state.waves +
    "-" +
    state.innerColour.slice(1) +
    "-" +
    state.outerColour.slice(1) +
    ".svg"
  );
}

function downloadSvg() {
  render();

  const source = serialiseCurrentSvg();
  const blob = new Blob([source], {
    type: "image/svg+xml;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = exportFilename();
  document.body.appendChild(link);
  link.click();
  link.remove();

  window.setTimeout(function () {
    URL.revokeObjectURL(url);
  }, 1000);
}

bindRange(elements.radius, "radius");
bindRange(elements.fieldWidth, "fieldWidth");
bindRange(elements.shape, "shape");
bindRange(elements.ribbonWidth, "ribbonWidth");
bindRange(elements.amplitude, "amplitude");
bindRange(elements.waves, "waves");

bindColourPicker(
  elements.innerColour,
  elements.innerHex,
  "innerColour",
);
bindColourPicker(
  elements.outerColour,
  elements.outerHex,
  "outerColour",
);

elements.presetBlueGreen.addEventListener("click", function () {
  applyPreset(PRESETS.blueGreen);
});
elements.presetRedYellow.addEventListener("click", function () {
  applyPreset(PRESETS.redYellow);
});
elements.presetBlueYellow.addEventListener("click", function () {
  applyPreset(PRESETS.blueYellow);
});
elements.presetYellowBlue.addEventListener("click", function () {
  applyPreset(PRESETS.yellowBlue);
});
elements.presetMagentaGreen.addEventListener("click", function () {
  applyPreset(PRESETS.magentaGreen);
});
elements.presetGreenMagenta.addEventListener("click", function () {
  applyPreset(PRESETS.greenMagenta);
});
elements.presetRedCyan.addEventListener("click", function () {
  applyPreset(PRESETS.redCyan);
});
elements.presetCyanRed.addEventListener("click", function () {
  applyPreset(PRESETS.cyanRed);
});

elements.pairwiseTest.addEventListener("click", openPairwiseTest);
elements.focusView.addEventListener("click", enterFocusView);
elements.stage.addEventListener("click", function () {
  if (document.body.classList.contains("focus-mode")) {
    exitFocusView();
  }
});
document.addEventListener("fullscreenchange", syncFocusMode);
document.addEventListener("keydown", function (event) {
  if (
    event.key === "Escape" &&
    document.body.classList.contains("focus-mode")
  ) {
    exitFocusView();
  }
});

elements.reset.addEventListener("click", resetExplorer);
elements.saveSvg.addEventListener("click", downloadSvg);

render();
