"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWBOX_SIZE = 760;
const CENTRE = VIEWBOX_SIZE / 2;
const EDGE_MARGIN = 20;
const CENTRE_MARGIN = 20;
const MAX_EXTENT = CENTRE - EDGE_MARGIN;

const LIMITS = Object.freeze({
  radius: [150, 240],
  fieldWidth: [50, 150],
  ribbonWidth: [2, 20],
  amplitude: [0, 45],
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
});

const DEFAULT_STATE = Object.freeze({
  radius: 220,
  fieldWidth: 110,
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
  ribbonWidth: document.getElementById("ribbon-width"),
  amplitude: document.getElementById("amplitude"),
  waves: document.getElementById("waves"),
  radiusValue: document.getElementById("radius-value"),
  fieldWidthValue: document.getElementById("field-width-value"),
  ribbonWidthValue: document.getElementById("ribbon-width-value"),
  amplitudeValue: document.getElementById("amplitude-value"),
  wavesValue: document.getElementById("waves-value"),
  innerColour: document.getElementById("inner-colour"),
  outerColour: document.getElementById("outer-colour"),
  innerHex: document.getElementById("inner-hex"),
  outerHex: document.getElementById("outer-hex"),
  presetBlueGreen: document.getElementById("preset-blue-green"),
  presetRedYellow: document.getElementById("preset-red-yellow"),
  focusView: document.getElementById("focus-view"),
  reset: document.getElementById("reset"),
  saveSvg: document.getElementById("save-svg"),
};

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function clampState() {
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

  const maximumOuterRadius =
    MAX_EXTENT - state.amplitude - 2 * state.ribbonWidth;
  state.radius = clamp(
    Number(state.radius),
    LIMITS.radius[0],
    Math.min(LIMITS.radius[1], maximumOuterRadius),
  );

  const maximumFieldWidth =
    state.radius -
    state.amplitude -
    2 * state.ribbonWidth -
    CENTRE_MARGIN;
  state.fieldWidth = clamp(
    Number(state.fieldWidth),
    LIMITS.fieldWidth[0],
    Math.min(LIMITS.fieldWidth[1], maximumFieldWidth),
  );
}

function pointOnBoundary(radius, amplitude, waves, theta, offset) {
  const r = radius + amplitude * Math.sin(waves * theta) + offset;
  return [
    CENTRE + r * Math.cos(theta),
    CENTRE + r * Math.sin(theta),
  ];
}

function sampleBoundary(radius, amplitude, waves, offset) {
  const count = Math.max(720, 48 * waves);
  const points = [];

  for (let index = 0; index < count; index += 1) {
    const theta = (2 * Math.PI * index) / count;
    points.push(pointOnBoundary(radius, amplitude, waves, theta, offset));
  }

  return points;
}

function formatCoordinate(value) {
  return Number(value.toFixed(3)).toString();
}

function closedPath(points) {
  if (points.length === 0) {
    return "";
  }

  const commands = points.map(function (point, index) {
    const prefix = index === 0 ? "M" : "L";
    return (
      prefix +
      " " +
      formatCoordinate(point[0]) +
      " " +
      formatCoordinate(point[1])
    );
  });

  return commands.join(" ") + " Z";
}

function ringPath(innerPoints, outerPoints) {
  return (
    closedPath(outerPoints) +
    " " +
    closedPath(innerPoints.slice().reverse())
  );
}

function formatValue(value, fractionDigits) {
  return Number(value.toFixed(fractionDigits)).toString();
}

function activePresetName() {
  const matchesBlueGreen =
    state.innerColour === PRESETS.blueGreen.innerColour &&
    state.outerColour === PRESETS.blueGreen.outerColour;
  const matchesRedYellow =
    state.innerColour === PRESETS.redYellow.innerColour &&
    state.outerColour === PRESETS.redYellow.outerColour;

  if (matchesBlueGreen) {
    return "blueGreen";
  }
  if (matchesRedYellow) {
    return "redYellow";
  }
  return null;
}

function syncControlsFromState() {
  elements.radius.value = String(state.radius);
  elements.fieldWidth.value = String(state.fieldWidth);
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
  elements.ribbonWidthValue.value = formatValue(state.ribbonWidth, 0);
  elements.amplitudeValue.value = formatValue(state.amplitude, 0);

  const wavelength = (2 * Math.PI * state.radius) / state.waves;
  elements.wavesValue.value =
    state.waves + " · λ ≈ " + formatValue(wavelength, 0);

  const activePreset = activePresetName();
  elements.presetBlueGreen.classList.toggle(
    "active",
    activePreset === "blueGreen",
  );
  elements.presetRedYellow.classList.toggle(
    "active",
    activePreset === "redYellow",
  );
}

function render() {
  clampState();

  const outerFieldRadius = state.radius;
  const innerFieldRadius = state.radius - state.fieldWidth;
  const w = state.ribbonWidth;

  const outerField = sampleBoundary(
    outerFieldRadius,
    state.amplitude,
    state.waves,
    0,
  );
  const outerInducingOuter = sampleBoundary(
    outerFieldRadius,
    state.amplitude,
    state.waves,
    w,
  );
  const outerBarrierOuter = sampleBoundary(
    outerFieldRadius,
    state.amplitude,
    state.waves,
    2 * w,
  );

  const innerField = sampleBoundary(
    innerFieldRadius,
    state.amplitude,
    state.waves,
    0,
  );
  const innerInducingInner = sampleBoundary(
    innerFieldRadius,
    state.amplitude,
    state.waves,
    -w,
  );
  const innerBarrierInner = sampleBoundary(
    innerFieldRadius,
    state.amplitude,
    state.waves,
    -2 * w,
  );

  elements.field.setAttribute(
    "d",
    ringPath(innerField, outerField),
  );
  elements.field.setAttribute("fill", "#ffffff");

  elements.outerInducing.setAttribute(
    "d",
    ringPath(outerField, outerInducingOuter),
  );
  elements.outerInducing.setAttribute("fill", state.innerColour);

  elements.outerBarrier.setAttribute(
    "d",
    ringPath(outerInducingOuter, outerBarrierOuter),
  );
  elements.outerBarrier.setAttribute("fill", state.outerColour);

  elements.innerInducing.setAttribute(
    "d",
    ringPath(innerInducingInner, innerField),
  );
  elements.innerInducing.setAttribute("fill", state.innerColour);

  elements.innerBarrier.setAttribute(
    "d",
    ringPath(innerBarrierInner, innerInducingInner),
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

function exportMetadata() {
  return {
    tool: "ColourShift Watercolour Explorer",
    version: 2,
    topology: "annular-field-double-boundary",
    outerFieldRadius: state.radius,
    fieldWidth: state.fieldWidth,
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
