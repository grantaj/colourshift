import { hexToRgb, rgbToHex, search } from "./colourshift-core.js?v=2";

const target = document.querySelector("#target");
const surround = document.querySelector("#surround");
const minDelta = document.querySelector("#min-delta");
const minDeltaValue = document.querySelector("#min-delta-value");
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
    const count = document.createElement("span"); count.className = "candidate-count"; count.textContent = `${index + 1} of ${result.candidates.length} · separation ${result.config.minDelta}`;
    const fullscreen = document.createElement("button"); fullscreen.type = "button"; fullscreen.className = "fullscreen"; fullscreen.textContent = "Full screen";
    previous.addEventListener("click", () => { index -= 1; render(); });
    next.addEventListener("click", () => { index += 1; render(); });
    fullscreen.addEventListener("click", async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await card.requestFullscreen();
      } catch (error) {
        console.error("Could not enter full screen", error);
      }
    });
    const nav = document.createElement("div"); nav.className = "candidate-nav"; nav.append(previous, count, next, fullscreen);
    const choices = document.createElement("div"); choices.className = "candidate-choices";
    for (const [choiceIndex, choice] of result.candidates.entries()) {
      const choiceButton = document.createElement("button");
      choiceButton.type = "button";
      choiceButton.textContent = choice.hex;
      choiceButton.className = "candidate-choice";
      choiceButton.style.background = choice.hex;
      choiceButton.classList.toggle("selected", choiceIndex === index);
      choiceButton.setAttribute("aria-label", `Show candidate ${choiceIndex + 1}: ${choice.hex}`);
      choiceButton.addEventListener("click", () => { index = choiceIndex; render(); });
      choices.append(choiceButton);
    }
    results.replaceChildren(card, nav, choices);
  };
  render();
}

function run() {
  const targetHex = target.value.toLowerCase();
  const startHex = surround.value.toLowerCase();
  try {
    const result = search("maximal-surround-shift", hexToRgb(targetHex), hexToRgb(startHex), { objective: "chromatic", gridPoints: 12, minDelta: Number(minDelta.value), maxCandidates: 3 });
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
minDelta.addEventListener("input", () => { minDeltaValue.value = minDelta.value; });
minDelta.addEventListener("change", () => {
  if (results.querySelector(".comparison")) run();
});
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
