import { hexToRgb, rgbToHex, search } from "./colourshift-core.js";

const target = document.querySelector("#target");
const surround = document.querySelector("#surround");
const results = document.querySelector("#results");

function comparisonCard(candidate, index, targetHex, startHex) {
  const card = document.createElement("article");
  card.className = "comparison";
  const swatches = document.createElement("div");
  swatches.className = "swatches";
  for (const colour of [startHex, candidate.hex]) {
    const field = document.createElement("div"); field.className = "swatch"; field.style.background = colour;
    const chip = document.createElement("div"); chip.className = "chip"; chip.style.background = targetHex; chip.setAttribute("aria-label", `Target ${targetHex} on ${colour}`);
    field.append(chip); swatches.append(field);
  }
  const caption = document.createElement("p");
  caption.innerHTML = `<strong>${index + 1}. ${candidate.hex}</strong><br>${candidate.chromatic_shift.toFixed(1)} chromatic shift`;
  card.append(swatches, caption); return card;
}

function renderResults(result, targetHex, startHex) {
  let index = 0;
  const render = () => {
    const card = comparisonCard(result.candidates[index], index, targetHex, startHex);
    const previous = document.createElement("button"); previous.type = "button"; previous.textContent = "Previous"; previous.disabled = index === 0;
    const next = document.createElement("button"); next.type = "button"; next.textContent = "Next"; next.disabled = index === result.candidates.length - 1;
    const count = document.createElement("span"); count.className = "candidate-count"; count.textContent = `${index + 1} of ${result.candidates.length}`;
    previous.addEventListener("click", () => { index -= 1; render(); });
    next.addEventListener("click", () => { index += 1; render(); });
    const nav = document.createElement("div"); nav.className = "candidate-nav"; nav.append(previous, count, next);
    results.replaceChildren(card, nav);
  };
  render();
}

function run() {
  const targetHex = target.value.toLowerCase();
  const startHex = surround.value.toLowerCase();
  try {
    const result = search("maximal-surround-shift", hexToRgb(targetHex), hexToRgb(startHex), { objective: "chromatic", gridPoints: 7, minDelta: 8, minRgbDelta: 0.35, maxCandidates: 3 });
    renderResults(result, targetHex, startHex);
  } catch (error) {
    results.replaceChildren();
    const message = document.createElement("p");
    message.className = "hint";
    message.textContent = "The search could not be calculated. Please try again.";
    results.append(message);
    console.error("ColourShift search failed", error);
  }
}

const searchButton = document.querySelector("#search");
searchButton.addEventListener("click", () => {
  searchButton.disabled = true;
  searchButton.textContent = "Searching…";
  results.replaceChildren();
  const message = document.createElement("p");
  message.className = "hint";
  message.textContent = "Searching the colour field…";
  results.append(message);
  // Yield to painting so the status is visible before the CPU-bound search.
  window.setTimeout(() => {
    try { run(); } finally {
      searchButton.disabled = false;
      searchButton.textContent = "Go";
    }
  }, 30);
});
