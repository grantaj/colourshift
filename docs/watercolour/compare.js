"use strict";

import {
  buildArcLengthMap,
  offsetClosedPolyline,
  ringPath,
  sampleBoundary,
  translatePoints,
} from "./geometry.mjs";

const CENTRE = 380;

const PRESETS = [
  { name: "Blue / green", inner: "#6ec66a", outer: "#3155a4" },
  { name: "Red / yellow", inner: "#f0cf45", outer: "#a93232" },
  { name: "Blue / yellow", inner: "#0000ff", outer: "#ffff00" },
  { name: "Yellow / blue", inner: "#ffff00", outer: "#0000ff" },
  { name: "Magenta / green", inner: "#ff00ff", outer: "#00ff00" },
  { name: "Green / magenta", inner: "#00ff00", outer: "#ff00ff" },
  { name: "Red / cyan", inner: "#ff0000", outer: "#00ffff" },
  { name: "Cyan / red", inner: "#00ffff", outer: "#ff0000" },
];

function numberParam(params, name, fallback) {
  const value = Number(params.get(name));
  return Number.isFinite(value) ? value : fallback;
}

const params = new URLSearchParams(window.location.search);
const geometry = Object.freeze({
  radius: numberParam(params, "radius", 220),
  fieldWidth: numberParam(params, "fieldWidth", 110),
  shape: numberParam(params, "shape", 0),
  ribbonWidth: numberParam(params, "ribbonWidth", 8),
  amplitude: numberParam(params, "amplitude", 15),
  waves: Math.round(numberParam(params, "waves", 12)),
});

const elements = {
  match: document.getElementById("match"),
  progress: document.getElementById("progress"),
  choiceA: document.getElementById("choice-a"),
  choiceB: document.getElementById("choice-b"),
  stimulusA: document.getElementById("stimulus-a"),
  stimulusB: document.getElementById("stimulus-b"),
  results: document.getElementById("results"),
  resultsText: document.getElementById("results-text"),
  copyResults: document.getElementById("copy-results"),
  restartTest: document.getElementById("restart-test"),
};

function renderStimulus(svg, preset) {
  const outerFieldRadius = geometry.radius;
  const innerFieldRadius = geometry.radius - geometry.fieldWidth;
  const width = geometry.ribbonWidth;
  const count = Math.max(1440, 96 * geometry.waves);
  const arcMap = buildArcLengthMap(geometry.shape, count);

  const outerFieldLocal = sampleBoundary(
    outerFieldRadius,
    geometry.amplitude,
    geometry.waves,
    geometry.shape,
    arcMap.fractions,
  );
  const innerFieldLocal = sampleBoundary(
    innerFieldRadius,
    geometry.amplitude,
    geometry.waves,
    geometry.shape,
    arcMap.fractions,
  );

  const outerInducingLocal = offsetClosedPolyline(outerFieldLocal, width);
  const outerBarrierLocal = offsetClosedPolyline(outerFieldLocal, 2 * width);
  const innerInducingLocal = offsetClosedPolyline(innerFieldLocal, -width);
  const innerBarrierLocal = offsetClosedPolyline(innerFieldLocal, -2 * width);

  const outerField = translatePoints(outerFieldLocal, CENTRE, CENTRE);
  const innerField = translatePoints(innerFieldLocal, CENTRE, CENTRE);
  const outerInducing = translatePoints(outerInducingLocal, CENTRE, CENTRE);
  const outerBarrier = translatePoints(outerBarrierLocal, CENTRE, CENTRE);
  const innerInducing = translatePoints(innerInducingLocal, CENTRE, CENTRE);
  const innerBarrier = translatePoints(innerBarrierLocal, CENTRE, CENTRE);

  svg.querySelector(".field").setAttribute("d", ringPath(innerField, outerField));

  const outerInducingPath = svg.querySelector(".outer-inducing");
  outerInducingPath.setAttribute("d", ringPath(outerField, outerInducing));
  outerInducingPath.setAttribute("fill", preset.inner);

  const outerBarrierPath = svg.querySelector(".outer-barrier");
  outerBarrierPath.setAttribute("d", ringPath(outerInducing, outerBarrier));
  outerBarrierPath.setAttribute("fill", preset.outer);

  const innerInducingPath = svg.querySelector(".inner-inducing");
  innerInducingPath.setAttribute("d", ringPath(innerInducing, innerField));
  innerInducingPath.setAttribute("fill", preset.inner);

  const innerBarrierPath = svg.querySelector(".inner-barrier");
  innerBarrierPath.setAttribute("d", ringPath(innerBarrier, innerInducing));
  innerBarrierPath.setAttribute("fill", preset.outer);
}

function shuffled(items) {
  const result = items.slice();
  for (let index = result.length - 1; index > 0; index -= 1) {
    const other = Math.floor(Math.random() * (index + 1));
    [result[index], result[other]] = [result[other], result[index]];
  }
  return result;
}

function buildRound(candidates) {
  const round = [];
  for (let index = 0; index < candidates.length; index += 2) {
    round.push([candidates[index], candidates[index + 1]]);
  }
  return round;
}

let roundNumber = 1;
let currentRound = buildRound(shuffled(PRESETS));
let matchIndex = 0;
let winners = [];
let currentMatch = null;
const history = [];

function totalMatchesRemaining() {
  return currentRound.length - matchIndex;
}

function showCurrentMatch() {
  currentMatch = currentRound[matchIndex];
  if (Math.random() < 0.5) {
    currentMatch = [currentMatch[1], currentMatch[0]];
  }

  const [left, right] = currentMatch;
  renderStimulus(elements.stimulusA, left);
  renderStimulus(elements.stimulusB, right);

  const remaining = totalMatchesRemaining();
  elements.progress.textContent =
    "Round " + roundNumber + " · " + remaining + " comparison" +
    (remaining === 1 ? "" : "s") + " remaining in this round";
}

function geometrySummary() {
  return [
    "radius=" + geometry.radius,
    "fieldWidth=" + geometry.fieldWidth,
    "shape=" + geometry.shape,
    "ribbonWidth=" + geometry.ribbonWidth,
    "amplitude=" + geometry.amplitude,
    "waves=" + geometry.waves,
  ].join(", ");
}

function finish() {
  const champion = winners[0];
  const lines = [
    "Watercolour pairwise test",
    "Geometry: " + geometrySummary(),
    "Winner: " + champion.name +
      " (inner " + champion.inner.toUpperCase() +
      ", outer " + champion.outer.toUpperCase() + ")",
    "",
    "Choices:",
  ];

  history.forEach(function (entry, index) {
    lines.push(
      (index + 1) + ". " +
      entry.left.name + " vs " + entry.right.name +
      " -> " + entry.winner.name,
    );
  });

  elements.resultsText.value = lines.join("\n");
  elements.match.hidden = true;
  elements.results.hidden = false;
  elements.progress.textContent = "Complete · 7 pairwise choices";
}

function choose(winner) {
  const [left, right] = currentMatch;
  history.push({ left, right, winner });
  winners.push(winner);
  matchIndex += 1;

  if (matchIndex < currentRound.length) {
    showCurrentMatch();
    return;
  }

  if (winners.length === 1) {
    finish();
    return;
  }

  currentRound = buildRound(winners);
  winners = [];
  matchIndex = 0;
  roundNumber += 1;
  showCurrentMatch();
}

elements.choiceA.addEventListener("click", function () {
  choose(currentMatch[0]);
});

elements.choiceB.addEventListener("click", function () {
  choose(currentMatch[1]);
});

elements.copyResults.addEventListener("click", async function () {
  try {
    await navigator.clipboard.writeText(elements.resultsText.value);
    elements.copyResults.textContent = "Copied";
  } catch {
    elements.resultsText.select();
  }
});

elements.restartTest.addEventListener("click", function () {
  window.location.reload();
});

showCurrentMatch();
