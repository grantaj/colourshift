"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const VIEWBOX_SIZE = 760;
const CENTRE = VIEWBOX_SIZE / 2;
const EDGE_MARGIN = 20;
const MAX_EXTENT = CENTRE - EDGE_MARGIN;

const LIMITS = Object.freeze({
  radius: [90, 240],
  ribbonWidth: [2, 30],
  amplitude: [0, 60],
  waves: [2, 30],
});

const DEFAULT_STATE = Object.freeze({
  radius: 180,
  ribbonWidth: 10,
  amplitude: 18,
  waves: 10,
  innerColour: "#ff8a16",
  outerColour: "#4f2a78",
});

const state = { ...DEFAULT_STATE };

const elements = {
  svg: document.getElementById("stimulus"),
  field: document.getElementById("field"),
  innerRibbon: document.getElementById("inner-ribbon"),
  outerRibbon: document.getElementById("outer-ribbon"),
  radius: document.getElementById("radius"),
  ribbonWidth: document.getElementById("ribbon-width"),
  amplitude: document.getElementById("amplitude"),
  waves: document.getElementById("waves"),
  radiusValue: document.getElementById("radius-value"),
  ribbonWidthValue: document.getElementById("ribbon-width-value"),
  amplitudeValue: document.getElementById("amplitude-value"),
  wavesValue: document.getElementById("waves-value"),
  innerColour: document.getElementById("inner-colour"),
  outerColour: document.getElementById("outer-colour"),
  innerHex: document.getElementById("inner-hex"),
  outerHex: document.getElementById("outer-hex"),
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

  const maximumRadiusForCurrentShape =
    MAX_EXTENT - state.amplitude - 2 * state.ribbonWidth;
  state.radius = clamp(
    Number(state.radius),
    LIMITS.radius[0],
    Math.min(LIMITS.radius[1], maximumRadiusForCurrentShape),
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

function syncControlsFromState() {
  elements.radius.value = String(state.radius);
  elements.ribbonWidth.value = String(state.ribbonWidth);
  elements.amplitude.value = String(state.amplitude);
  elements.waves.value = String(state.waves);

  elements.innerColour.value = state.innerColour;
  elements.outerColour.value = state.outerColour;
  elements.innerHex.value = state.innerColour.toUpperCase();
  elements.outerHex.value = state.outerColour.toUpperCase();

  elements.innerHex.setAttribute("aria-invalid", "false");
  elements.outerHex.setAttribute("aria-invalid", "false");

  elements.radiusValue.value = formatValue(state.radius, 0) + " units";
  elements.ribbonWidthValue.value =
    formatValue(state.ribbonWidth, 0) + " units";
  elements.amplitudeValue.value =
    formatValue(state.amplitude, 0) + " units";

  const wavelength = (2 * Math.PI * state.radius) / state.waves;
  elements.wavesValue.value =
    state.waves +
    " waves · λ ≈ " +
    formatValue(wavelength, 1) +
    " units";
}

function render() {
  clampState();

  const boundary0 = sampleBoundary(
    state.radius,
    state.amplitude,
    state.waves,
    0,
  );
  const boundary1 = sampleBoundary(
    state.radius,
    state.amplitude,
    state.waves,
    state.ribbonWidth,
  );
  const boundary2 = sampleBoundary(
    state.radius,
    state.amplitude,
    state.waves,
    2 * state.ribbonWidth,
  );

  elements.outerRibbon.setAttribute(
    "d",
    ringPath(boundary1, boundary2),
  );
  elements.outerRibbon.setAttribute("fill", state.outerColour);

  elements.innerRibbon.setAttribute(
    "d",
    ringPath(boundary0, boundary1),
  );
  elements.innerRibbon.setAttribute("fill", state.innerColour);

  elements.field.setAttribute("d", closedPath(boundary0));
  elements.field.setAttribute("fill", "#ffffff");

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
    textInput.value = state[key].toUpperCase();
    textInput.setAttribute("aria-invalid", "false");
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

function resetExplorer() {
  Object.assign(state, DEFAULT_STATE);
  render();
}

function exportMetadata() {
  return {
    tool: "ColourShift Watercolour Explorer",
    version: 1,
    radius: state.radius,
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
    "watercolour-R" +
    filenameNumber(state.radius) +
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

elements.reset.addEventListener("click", resetExplorer);
elements.saveSvg.addEventListener("click", downloadSvg);

render();
