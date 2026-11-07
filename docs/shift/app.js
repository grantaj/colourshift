import { hexToRgb, rgbToHex, search } from "./colourshift-core.js?v=4";

const target = document.querySelector("#target");
const surround = document.querySelector("#surround");
const results = document.querySelector("#results");
let searchTimer;

function updateReference() {
  for (const patch of document.querySelectorAll(".reference-target")) patch.style.background = target.value;
  for (const field of document.querySelectorAll(".reference-field")) field.style.background = surround.value;
}

function openPicker(picker) {
  if (picker.showPicker) picker.showPicker();
  else picker.click();
}

function bindReferenceEditor(editor) {
  editor.querySelector(".reference-target").addEventListener("click", () => openPicker(target));
  editor.querySelector(".reference-field").addEventListener("click", () => openPicker(surround));
}

function referenceEditor() {
  const editor = document.createElement("div");
  editor.className = "reference-editor";
  editor.setAttribute("role", "group");
  editor.setAttribute("aria-label", "Starting colour comparison");
  const field = document.createElement("button");
  field.type = "button"; field.className = "reference-field"; field.setAttribute("aria-label", "Choose surrounding colour");
  field.style.background = surround.value;
  const patch = document.createElement("button");
  patch.type = "button"; patch.className = "reference-target"; patch.setAttribute("aria-label", "Choose target colour");
  patch.style.background = target.value;
  editor.append(field, patch);
  bindReferenceEditor(editor);
  return editor;
}

function comparisonCard(candidate, index, targetHex, startHex) {
  const card = document.createElement("article");
  card.className = "comparison";
  const swatches = document.createElement("div");
  swatches.className = "swatches";
  for (const [position, colour] of [startHex, candidate.hex].entries()) {
    if (position === 0) {
      swatches.append(referenceEditor());
      continue;
    }
    const field = document.createElement("div"); field.className = "swatch"; field.style.background = colour;
    const chip = document.createElement("div"); chip.className = "chip"; chip.style.background = targetHex; chip.setAttribute("aria-label", `Target ${targetHex} on ${colour}`);
    field.append(chip); swatches.append(field);
  }
  card.append(swatches); return card;
}

function unavailableCard(targetHex, startHex) {
  const card = document.createElement("article");
  card.className = "comparison unavailable-comparison";
  const swatches = document.createElement("div");
  swatches.className = "swatches";
  swatches.append(referenceEditor());
  const empty = document.createElement("div");
  empty.className = "empty-result";
  empty.textContent = "No comparable surround was found for these settings.";
  swatches.append(empty);
  const caption = document.createElement("p");
  caption.textContent = "Choose another target or surrounding colour to continue.";
  card.append(swatches, caption);
  return card;
}

function renderResults(result, targetHex, startHex) {
  if (result.candidates.length === 0) {
    results.replaceChildren(unavailableCard(targetHex, startHex));
    return;
  }
  let index = 0;
  const render = () => {
    const card = comparisonCard(result.candidates[index], index, targetHex, startHex);
    const fullscreen = document.createElement("button"); fullscreen.type = "button"; fullscreen.className = "fullscreen"; fullscreen.textContent = "Full screen";
    fullscreen.addEventListener("click", async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await card.requestFullscreen();
      } catch (error) {
        console.error("Could not enter full screen", error);
      }
    });
    const choices = document.createElement("div"); choices.className = "candidate-choices";
    const references = document.createElement("div");
    references.className = "reference-choices";
    const targetChoice = document.createElement("button");
    targetChoice.type = "button";
    targetChoice.textContent = targetHex;
    targetChoice.className = "candidate-choice target-choice";
    targetChoice.style.background = targetHex;
    targetChoice.setAttribute("aria-label", `Choose target colour: ${targetHex}`);
    targetChoice.addEventListener("click", () => openPicker(target));
    const surroundChoice = document.createElement("button");
    surroundChoice.type = "button";
    surroundChoice.textContent = startHex;
    surroundChoice.className = "candidate-choice surround-choice";
    surroundChoice.style.background = startHex;
    surroundChoice.setAttribute("aria-label", `Choose surrounding colour: ${startHex}`);
    surroundChoice.addEventListener("click", () => openPicker(surround));
    references.append(targetChoice, surroundChoice);
    choices.append(references);
    const solutions = document.createElement("div");
    solutions.className = "solution-choices";
    for (const [choiceIndex, choice] of result.candidates.entries()) {
      const solution = document.createElement("div");
      solution.className = "solution-choice";
      const choiceButton = document.createElement("button");
      choiceButton.type = "button";
      choiceButton.textContent = choice.hex;
      choiceButton.className = "candidate-choice";
      choiceButton.style.background = choice.hex;
      choiceButton.classList.toggle("selected", choiceIndex === index);
      choiceButton.setAttribute("aria-label", `Show candidate ${choiceIndex + 1}: ${choice.hex}`);
      choiceButton.addEventListener("click", () => { index = choiceIndex; render(); });
      const shift = document.createElement("span");
      shift.className = "candidate-shift";
      shift.textContent = choice.chromatic_shift.toFixed(1);
      solution.append(choiceButton, shift);
      solutions.append(solution);
    }
    choices.append(solutions);
    const resultControls = document.createElement("div");
    resultControls.className = "result-controls";
    resultControls.append(choices, fullscreen);
    results.replaceChildren(card, resultControls);
  };
  render();
}

function run() {
  const targetHex = target.value.toLowerCase();
  const startHex = surround.value.toLowerCase();
  try {
    const result = search("maximal-surround-shift", hexToRgb(targetHex), hexToRgb(startHex), { objective: "chromatic", gridPoints: 12, minDelta: 10, maxCandidates: 3 });
    renderResults(result, targetHex, startHex);
  } catch (error) {
    console.error("ColourShift search failed", error);
  }
}

function scheduleSearch() {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(run, 180);
}

for (const editor of document.querySelectorAll(".reference-editor")) bindReferenceEditor(editor);
target.addEventListener("input", () => { updateReference(); scheduleSearch(); });
surround.addEventListener("input", () => { updateReference(); scheduleSearch(); });
updateReference();
scheduleSearch();
