"use strict";

import {
  buildArcLengthMap,
  clamp,
  minimumShapeFactor,
  sampleBoundary,
  closedPath,
  translatePoints,
} from "./geometry.mjs?v=5";

const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWBOX_SIZE = 760;
const CENTRE = VIEWBOX_SIZE / 2;
const EDGE_MARGIN = 20;
const CENTRE_MARGIN = 20;
const MAX_EXTENT = CENTRE - EDGE_MARGIN;

const LIMITS = Object.freeze({
  radius: [150, 240],
  fieldWidth: [50, 150],
  shape: [0, 1],
  ribbonWidth: [2, 12],
  amplitude: [0, 35],
  waves: [2, 30],
  crenellationShape: [0.25, 1.25],
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
});

const DEFAULT_STATE = Object.freeze({
  radius: 220,
  fieldWidth: 110,
  shape: 0,
  ribbonWidth: 8,
  amplitude: 15,
  waves: 12,
  crenellationShape: 0.5,
  innerColour: PRESETS.blueGreen.innerColour,
  outerColour: PRESETS.blueGreen.outerColour,
});

const state = { ...DEFAULT_STATE };
const OKLAB_RANGE = 0.25;
let selectedColourKey = "innerColour";
const fixedColourLightness = {
  innerColour: null,
  outerColour: null,
};
const colourPlanePosition = {
  innerColour: null,
  outerColour: null,
};

function srgbChannelToLinear(channel) {
  return channel <= 0.04045
    ? channel / 12.92
    : Math.pow((channel + 0.055) / 1.055, 2.4);
}

function linearChannelToSrgb(channel) {
  return channel <= 0.0031308
    ? 12.92 * channel
    : 1.055 * Math.pow(channel, 1 / 2.4) - 0.055;
}

function hexToRgb(hex) {
  return [
    parseInt(hex.slice(1, 3), 16) / 255,
    parseInt(hex.slice(3, 5), 16) / 255,
    parseInt(hex.slice(5, 7), 16) / 255,
  ];
}

function rgbToHex(rgb) {
  return (
    "#" +
    rgb.map(function (channel) {
      return Math.round(clamp(channel, 0, 1) * 255)
        .toString(16)
        .padStart(2, "0");
    }).join("")
  );
}

function rgbToOklab(rgb) {
  const r = srgbChannelToLinear(rgb[0]);
  const g = srgbChannelToLinear(rgb[1]);
  const b = srgbChannelToLinear(rgb[2]);

  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);

  return {
    L: 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
  };
}

function oklabToLinearRgb(L, a, b) {
  const lRoot = L + 0.3963377774 * a + 0.2158037573 * b;
  const mRoot = L - 0.1055613458 * a - 0.0638541728 * b;
  const sRoot = L - 0.0894841775 * a - 1.291485548 * b;
  const l = lRoot * lRoot * lRoot;
  const m = mRoot * mRoot * mRoot;
  const s = sRoot * sRoot * sRoot;

  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

function linearRgbInGamut(rgb) {
  return rgb.every(function (channel) {
    return channel >= 0 && channel <= 1;
  });
}

function gamutMappedOklab(L, a, b) {
  let linear = oklabToLinearRgb(L, a, b);
  if (!linearRgbInGamut(linear)) {
    let low = 0;
    let high = 1;
    for (let iteration = 0; iteration < 12; iteration += 1) {
      const scale = (low + high) / 2;
      const candidate = oklabToLinearRgb(L, a * scale, b * scale);
      if (linearRgbInGamut(candidate)) {
        low = scale;
        linear = candidate;
      } else {
        high = scale;
      }
    }
  }

  return linear.map(linearChannelToSrgb);
}

function colourLab(key) {
  return rgbToOklab(hexToRgb(state[key]));
}

function syncFixedColourLightness() {
  fixedColourLightness.innerColour = colourLab("innerColour").L;
  fixedColourLightness.outerColour = colourLab("outerColour").L;
}

function syncPlanePositionsFromColours() {
  for (const key of ["innerColour", "outerColour"]) {
    const lab = colourLab(key);
    colourPlanePosition[key] = {
      x: clamp((lab.a / OKLAB_RANGE + 1) / 2, 0, 1),
      y: clamp((1 - lab.b / OKLAB_RANGE) / 2, 0, 1),
    };
  }
}

function ensureColourPlaneCells() {
  if (elements.colourPlane.childElementCount > 0) {
    return;
  }

  const cells = 24;
  const cellSize = 100 / cells;
  for (let y = 0; y < cells; y += 1) {
    for (let x = 0; x < cells; x += 1) {
      const rect = document.createElementNS(SVG_NS, "rect");
      rect.setAttribute("x", String(x * cellSize));
      rect.setAttribute("y", String(y * cellSize));
      rect.setAttribute("width", String(cellSize + 0.05));
      rect.setAttribute("height", String(cellSize + 0.05));
      rect.dataset.colourPlaneX = String(x);
      rect.dataset.colourPlaneY = String(y);
      elements.colourPlane.appendChild(rect);
    }
  }
}

function drawColourPlane() {
  const lab = colourLab(selectedColourKey);
  const lightness = fixedColourLightness[selectedColourKey] ?? lab.L;

  ensureColourPlaneCells();

  const cells = 24;
  for (const rect of elements.colourPlane.children) {
    const x = Number(rect.dataset.colourPlaneX);
    const y = Number(rect.dataset.colourPlaneY);
    const a = OKLAB_RANGE * (2 * (x + 0.5) / cells - 1);
    const b = OKLAB_RANGE * (1 - 2 * (y + 0.5) / cells);
    rect.setAttribute(
      "fill",
      rgbToHex(gamutMappedOklab(lightness, a, b)),
    );
  }

}

function setColourPlaneMarkerPosition(x, y) {
  elements.colourPlaneMarker.style.left = (100 * clamp(x, 0, 1)) + "%";
  elements.colourPlaneMarker.style.top = (100 * clamp(y, 0, 1)) + "%";
}

function updateColourPlaneMarker() {
  const position = colourPlanePosition[selectedColourKey];
  if (position !== null) {
    setColourPlaneMarkerPosition(position.x, position.y);
    return;
  }

  const lab = colourLab(selectedColourKey);
  setColourPlaneMarkerPosition(
    clamp((lab.a / OKLAB_RANGE + 1) / 2, 0, 1),
    clamp((1 - lab.b / OKLAB_RANGE) / 2, 0, 1),
  );
}

function syncColourDock() {
  elements.innerSwatch.style.background = state.innerColour;
  elements.outerSwatch.style.background = state.outerColour;
  elements.innerSummarySwatch.style.background = state.innerColour;
  elements.outerSummarySwatch.style.background = state.outerColour;
  const selectedLightness =
    fixedColourLightness[selectedColourKey] ?? colourLab(selectedColourKey).L;
  elements.colourLightnessLabel.textContent = selectedColourKey === "innerColour"
    ? "Inner lightness"
    : "Outer lightness";
  elements.colourLightness.value = String(selectedLightness);
  elements.colourLightnessValue.value = selectedLightness.toFixed(2);

  elements.editInner.checked = selectedColourKey === "innerColour";
  elements.editOuter.checked = selectedColourKey === "outerColour";

  drawColourPlane();
  updateColourPlaneMarker();
}

function selectColour(key) {
  selectedColourKey = key;
  syncColourDock();
}

function syncSelectedColourOnly() {
  // Colour edits must not rewrite or repaint the unselected colour's SVG strokes.
  const strokes = selectedColourKey === "innerColour"
    ? [elements.outerInducing, elements.innerInducing]
    : [elements.outerBarrier, elements.innerBarrier];
  for (const stroke of strokes) {
    stroke.setAttribute("stroke", state[selectedColourKey]);
  }
  syncPresetButtons();
  syncColourDock();
}

function setSelectedLightness(value) {
  const lab = colourLab(selectedColourKey);
  const L = clamp(Number(value), 0.2, 0.9);
  fixedColourLightness[selectedColourKey] = L;
  state[selectedColourKey] = rgbToHex(
    gamutMappedOklab(L, lab.a, lab.b),
  );
  syncSelectedColourOnly();
}

function setColourFromPlaneEvent(event) {
  const rect = elements.colourPlane.getBoundingClientRect();
  const x = clamp((event.clientX - rect.left) / rect.width, 0, 1);
  const y = clamp((event.clientY - rect.top) / rect.height, 0, 1);
  const a = OKLAB_RANGE * (2 * x - 1);
  const b = OKLAB_RANGE * (1 - 2 * y);
  const L = fixedColourLightness[selectedColourKey] ??
    colourLab(selectedColourKey).L;
  colourPlanePosition[selectedColourKey] = { x, y };
  setColourPlaneMarkerPosition(x, y);
  state[selectedColourKey] = rgbToHex(gamutMappedOklab(L, a, b));
  syncSelectedColourOnly();
}

function bindColourPlane() {
  let dragging = false;

  elements.colourPlane.addEventListener("pointerdown", function (event) {
    dragging = true;
    elements.colourPlane.setPointerCapture(event.pointerId);
    setColourFromPlaneEvent(event);
  });
  elements.colourPlane.addEventListener("pointermove", function (event) {
    if (dragging) {
      setColourFromPlaneEvent(event);
    }
  });
  elements.colourPlane.addEventListener("pointerup", function (event) {
    dragging = false;
    elements.colourPlane.releasePointerCapture(event.pointerId);
  });
  elements.colourPlane.addEventListener("pointercancel", function () {
    dragging = false;
  });
}

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
  crenellationShape: document.getElementById("crenellation-shape"),
  radiusValue: document.getElementById("radius-value"),
  fieldWidthValue: document.getElementById("field-width-value"),
  shapeValue: document.getElementById("shape-value"),
  ribbonWidthValue: document.getElementById("ribbon-width-value"),
  amplitudeValue: document.getElementById("amplitude-value"),
  wavesValue: document.getElementById("waves-value"),
  crenellationShapeValue: document.getElementById("crenellation-shape-value"),
  colourDock: document.getElementById("colour-dock"),
  innerSummarySwatch: document.getElementById("inner-summary-swatch"),
  outerSummarySwatch: document.getElementById("outer-summary-swatch"),
  colourPlane: document.getElementById("colour-plane"),
  colourPlaneMarker: document.getElementById("colour-plane-marker"),
  colourLightness: document.getElementById("colour-lightness"),
  colourLightnessLabel: document.getElementById("colour-lightness-label"),
  colourLightnessValue: document.getElementById("colour-lightness-value"),
  editInner: document.getElementById("edit-inner"),
  editOuter: document.getElementById("edit-outer"),
  innerSwatch: document.getElementById("inner-swatch"),
  outerSwatch: document.getElementById("outer-swatch"),
  presetBlueGreen: document.getElementById("preset-blue-green"),
  presetRedYellow: document.getElementById("preset-red-yellow"),
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
  state.crenellationShape = clamp(
    Number(state.crenellationShape),
    LIMITS.crenellationShape[0],
    LIMITS.crenellationShape[1],
  );

  const minimumFactor = minimumShapeFactor(state.shape);
  const innerClearance =
    CENTRE_MARGIN +
    state.amplitude +
    2 * state.ribbonWidth;
  const minimumInnerBaseRadius = innerClearance / minimumFactor;

  const minimumOuterRadius =
    LIMITS.fieldWidth[0] + minimumInnerBaseRadius;
  const maximumOuterRadius =
    MAX_EXTENT -
    state.amplitude -
    2 * state.ribbonWidth;

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
  if (shape >= 0.99) {
    return "Square";
  }
  return "Circle → square · " + Math.round(shape * 100) + "%";
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

function syncPresetButtons() {
  const activePreset = activePresetName();
  for (const [name, element] of [
    ["blueGreen", elements.presetBlueGreen],
    ["redYellow", elements.presetRedYellow],
  ]) {
    element.classList.toggle("active", activePreset === name);
  }
}

function syncControlsFromState() {
  elements.radius.value = String(state.radius);
  elements.fieldWidth.value = String(state.fieldWidth);
  elements.shape.value = String(state.shape);
  elements.ribbonWidth.value = String(state.ribbonWidth);
  elements.amplitude.value = String(state.amplitude);
  elements.waves.value = String(state.waves);
  elements.crenellationShape.value = String(state.crenellationShape);

  elements.radiusValue.value = formatValue(state.radius, 0);
  elements.fieldWidthValue.value = formatValue(state.fieldWidth, 0);
  elements.shapeValue.value = shapeLabel(state.shape);
  elements.ribbonWidthValue.value = formatValue(state.ribbonWidth, 0);
  elements.amplitudeValue.value = formatValue(state.amplitude, 0);

  const shapeOffset = state.crenellationShape - 0.5;
  const crenellationLabel =
    Math.abs(shapeOffset) < 0.005
      ? "Sine · 0.50"
      : state.crenellationShape < 0.5
        ? "Sharper · " + formatValue(state.crenellationShape, 2)
        : "Flatter · " + formatValue(state.crenellationShape, 2);
  elements.crenellationShapeValue.value = crenellationLabel;

  const count = 4096;
  const arcMap = buildArcLengthMap(state.shape, count);
  const perimeter = arcMap.perimeterFactor * state.radius;
  const wavelength = perimeter / state.waves;
  elements.wavesValue.value =
    formatValue(state.waves, 2) + " · λ ≈ " + formatValue(wavelength, 0);

  syncPresetButtons();
  syncColourDock();
}

function render() {
  clampState();

  const outerFieldRadius = state.radius;
  const innerFieldRadius = state.radius - state.fieldWidth;
  const w = state.ribbonWidth;
  const count = 4096;
  const arcMap = buildArcLengthMap(state.shape, count);
  const arcFractions = arcMap.fractions;

  const outerWaves = state.waves;
  const innerWaves = Math.max(
    1,
    Math.round(state.waves * (innerFieldRadius / outerFieldRadius)),
  );

  const outerFieldLocal = sampleBoundary(
    outerFieldRadius,
    state.amplitude,
    outerWaves,
    state.shape,
    arcFractions,
    state.crenellationShape,
  );
  const innerFieldLocal = sampleBoundary(
    innerFieldRadius,
    state.amplitude,
    innerWaves,
    state.shape,
    arcFractions,
    state.crenellationShape,
  );

  const outerField = translatePoints(outerFieldLocal, CENTRE, CENTRE);
  const innerField = translatePoints(innerFieldLocal, CENTRE, CENTRE);
  const outerPath = closedPath(outerField);
  const innerPath = closedPath(innerField);

  elements.outerBarrier.setAttribute("d", outerPath);
  elements.innerBarrier.setAttribute("d", innerPath);
  elements.outerInducing.setAttribute("d", outerPath);
  elements.innerInducing.setAttribute("d", innerPath);

  for (const element of [elements.outerBarrier, elements.innerBarrier]) {
    element.setAttribute("stroke", state.outerColour);
    element.setAttribute("stroke-width", String(4 * w));
  }
  for (const element of [elements.outerInducing, elements.innerInducing]) {
    element.setAttribute("stroke", state.innerColour);
    element.setAttribute("stroke-width", String(2 * w));
  }

  elements.field.setAttribute(
    "d",
    closedPath(outerField) + " " + closedPath(innerField.slice().reverse()),
  );
  elements.field.setAttribute("fill", "#ffffff");

  syncControlsFromState();
}

function bindRange(element, key) {
  element.addEventListener("input", function () {
    state[key] = Number(element.value);
    render();
  });
}

function presetColourState(hex) {
  const lab = rgbToOklab(hexToRgb(hex));
  return {
    hex,
    lightness: lab.L,
    position: {
      x: clamp((lab.a / OKLAB_RANGE + 1) / 2, 0, 1),
      y: clamp((1 - lab.b / OKLAB_RANGE) / 2, 0, 1),
    },
  };
}

function setCompleteColourState(innerHex, outerHex) {
  const inner = presetColourState(innerHex);
  const outer = presetColourState(outerHex);

  state.innerColour = inner.hex;
  state.outerColour = outer.hex;
  fixedColourLightness.innerColour = inner.lightness;
  fixedColourLightness.outerColour = outer.lightness;
  colourPlanePosition.innerColour = inner.position;
  colourPlanePosition.outerColour = outer.position;
}

function applyPreset(preset) {
  setCompleteColourState(preset.innerColour, preset.outerColour);
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
  selectedColourKey = "innerColour";
  Object.assign(state, DEFAULT_STATE);
  setCompleteColourState(state.innerColour, state.outerColour);
  render();
}

function exportMetadata() {
  return {
    tool: "ColourShift Watercolour Explorer",
    version: 10,
    topology: "annular-field-double-boundary",
    outerFieldRadius: state.radius,
    fieldWidth: state.fieldWidth,
    shapeMorph: state.shape,
    shape: shapeLabel(state.shape),
    innerFieldRadius: state.radius - state.fieldWidth,
    ribbonWidth: state.ribbonWidth,
    amplitude: state.amplitude,
    outerWaves: state.waves,
    crenellationShape: state.crenellationShape,
    innerWaves: Math.max(
      1,
      Math.round(
        state.waves * ((state.radius - state.fieldWidth) / state.radius),
      ),
    ),
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
bindRange(elements.crenellationShape, "crenellationShape");

// On narrow screens, show the artwork and geometry sliders first.
// The native disclosure preserves its state when the viewport later changes.
if (window.matchMedia("(min-width: 901px)").matches) {
  elements.colourDock.open = true;
}

setCompleteColourState(state.innerColour, state.outerColour);
bindColourPlane();
elements.colourLightness.addEventListener("input", function () {
  setSelectedLightness(elements.colourLightness.value);
});
elements.editInner.addEventListener("change", function () {
  if (elements.editInner.checked) {
    selectColour("innerColour");
  }
});
elements.editOuter.addEventListener("change", function () {
  if (elements.editOuter.checked) {
    selectColour("outerColour");
  }
});

elements.presetBlueGreen.addEventListener("click", function () {
  applyPreset(PRESETS.blueGreen);
});
elements.presetRedYellow.addEventListener("click", function () {
  applyPreset(PRESETS.redYellow);
});

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

