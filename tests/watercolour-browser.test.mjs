import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import test from "node:test";

const ROOT = new URL("../docs/watercolour/", import.meta.url);
const FILES = {
  "/": "index.html",
  "/watercolour.js": "watercolour.js",
  "/geometry.mjs": "geometry.mjs",
  "/watercolour.css": "watercolour.css",
};

const PROBE = [
  'document.addEventListener("DOMContentLoaded", function () {',
  ' const plane = document.getElementById("colour-plane");',
  ' const fills = () => Array.from(plane.querySelectorAll("rect"), el => el.getAttribute("fill"));',
  ' const before = fills();',
  ' const outerPathBefore = document.getElementById("outer-barrier").getAttribute("d");',
  ' const innerPathBefore = document.getElementById("inner-barrier").getAttribute("d");',
  ' const waveShape = document.getElementById("crenellation-shape");',
  ' waveShape.value = "1.25";',
  ' waveShape.dispatchEvent(new Event("input", { bubbles: true }));',
  ' const bothBoundariesUpdated = document.getElementById("outer-barrier").getAttribute("d") !== outerPathBefore && document.getElementById("inner-barrier").getAttribute("d") !== innerPathBefore;',
  ' const shapeLabelText = document.getElementById("crenellation-shape-value").value;',
  ' const shapeLabelUpdated = shapeLabelText.includes("Flatter");',
  ' const first = plane.querySelector("rect");',
  ' const painted = first && getComputedStyle(first).fill;',
  ' const dock = document.getElementById("colour-dock");',
  ' const summary = dock.querySelector("summary");',
  ' const mobile = matchMedia("(max-width: 900px)").matches;',
  ' const initiallyFolded = !dock.open;',
  ' const imageBottom = document.getElementById("stage").getBoundingClientRect().bottom;',
  ' const geometryTop = document.getElementById("radius").getBoundingClientRect().top;',
  ' const geometryVisibleWithImage = geometryTop < innerHeight && imageBottom < geometryTop;',
  ' const foldedHeight = dock.getBoundingClientRect().height;',
  ' summary.click();',
  ' const expandedBySummary = dock.open;',
  ' const expandedHeight = dock.getBoundingClientRect().height;',
  ' const firstWidth = first && first.getBoundingClientRect().width;',
  ' const initialLightness = Number(document.getElementById("colour-lightness").value);',
  ' const innerButton = document.getElementById("edit-inner");',
  ' const outerButton = document.getElementById("edit-outer");',
  ' const chosen = (input) => input.checked;',
  ' const radioCount = document.querySelectorAll(\'input[type="radio"][name="edit-colour"]\').length;',
  ' const customDots = document.querySelectorAll(".target-selection-dot").length;',
  ' const initialInnerSelected = innerButton.type === "radio" && outerButton.type === "radio" && chosen(innerButton) && !chosen(outerButton);',
  ' const innerStroke = () => document.getElementById("inner-inducing").getAttribute("stroke");',
  ' const outerStroke = () => document.getElementById("outer-barrier").getAttribute("stroke");',
  ' const originalInnerStroke = innerStroke();',
  ' const originalOuterStroke = outerStroke();',
  ' document.getElementById("edit-outer").click();',
  ' const outer = fills();',
  ' document.getElementById("edit-inner").click();',
  ' const again = fills();',
  ' const slider = document.getElementById("colour-lightness");',
  ' slider.value = "0.45";',
  ' slider.dispatchEvent(new Event("input", { bubbles: true }));',
  ' const editedInner = innerStroke();',
  ' const innerSummaryAfterEdit = getComputedStyle(document.getElementById("inner-summary-swatch")).backgroundColor;',
  ' const innerOnly = editedInner !== originalInnerStroke && outerStroke() === originalOuterStroke && chosen(innerButton) && !chosen(outerButton);',
  ' outerButton.click();',
  ' const outerSelected = chosen(outerButton) && !chosen(innerButton);',
  ' const innerBeforeOuterEdit = innerStroke();',
  ' slider.value = "0.82";',
  ' slider.dispatchEvent(new Event("input", { bubbles: true }));',
  ' const outerOnly = outerStroke() !== originalOuterStroke && innerStroke() === innerBeforeOuterEdit;',
  ' innerButton.click();',
  ' const lightnessRestored = Math.abs(Number(slider.value) - 0.45) < 0.006;',
  ' const swatchCurrent = getComputedStyle(document.getElementById("inner-summary-swatch")).backgroundColor === innerSummaryAfterEdit;',
  ' summary.click();',
  ' const foldedAfterEditing = !dock.open && dock.getBoundingClientRect().height < expandedHeight / 2;',
  ' summary.click();',
  ' const reopenedPreservesColours = dock.open && innerStroke() === editedInner && outerStroke() !== originalOuterStroke;',
  ' document.getElementById("reset").click();',
  ' const resetCorrect = chosen(innerButton) && !chosen(outerButton) && innerStroke() === originalInnerStroke && outerStroke() === originalOuterStroke;',
  ' const report = { count: before.length,',
  '   populated: before.every(c => /^#[0-9a-f]{6}$/.test(c)),',
  '   changedOnOuter: before.some((c, i) => c !== outer[i]),',
  '   restored: before.length === again.length && before.every((c, i) => c === again[i]),',
  '   initialLightness, initialInnerSelected, radioCount, customDots, innerOnly, outerSelected, outerOnly, lightnessRestored, resetCorrect,',
  '   mobile, initiallyFolded, foldedHeight, expandedHeight, expandedBySummary, geometryVisibleWithImage, foldedAfterEditing, reopenedPreservesColours, swatchCurrent, bothBoundariesUpdated, shapeLabelUpdated, shapeLabelText,',
  '   firstWidth, painted,',
  '   selectedInner: document.getElementById("edit-inner").checked',
  ' };',
  ' const result = document.createElement("pre");',
  ' result.id = "browser-probe-result"; result.textContent = JSON.stringify(report);',
  ' document.body.appendChild(result);',
  '});',
].join("\n");

function findBrowser() {
  for (const name of [
    process.env.CHROME_BIN,
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
  ]) {
    if (name && spawnSync("which", [name], { stdio: "ignore" }).status === 0) {
      return name;
    }
  }
  return null;
}

test("Chromium paints the default chooser and preserves it across Outer → Inner", async (t) => {
  const browser = findBrowser();
  assert.ok(browser, "Chromium or Google Chrome must be installed for the browser smoke test");

  const server = createServer(async (req, res) => {
    const path = new URL(req.url, "http://localhost").pathname;
    const name = FILES[path];
    if (!name) {
      res.writeHead(404).end();
      return;
    }
    try {
      let content = await readFile(new URL(name, ROOT), "utf8");
      if (name === "index.html") {
        // Avoid an external font download delaying the browser smoke test.
        content = content.replace(/<link rel="stylesheet" href="https:\/\/cdn\.jsdelivr\.net[^"]*" \/>/, "");
        content = content.replace("</body>", "<script>" + PROBE + "</script></body>");
      }
      res.setHeader(
        "Content-Type",
        name.endsWith(".html") ? "text/html" : name.endsWith(".css") ? "text/css" : "text/javascript",
      );
      res.end(content);
    } catch (error) {
      res.writeHead(500).end(String(error));
    }
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));

  const url = "http://127.0.0.1:" + server.address().port + "/";
  const result = await new Promise((resolve, reject) => {
    const child = spawn(browser, [
      "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
      "--disable-background-networking", "--no-first-run", "--virtual-time-budget=5000",
      "--window-size=390,844", "--dump-dom", url,
    ]);
    let stdout = "", stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", chunk => { stdout += chunk; });
    child.stderr.on("data", chunk => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", code => resolve({ code, stdout, stderr }));
  });
  assert.equal(result.code, 0, result.stderr.slice(-1000));
  const match = result.stdout.match(/<pre id="browser-probe-result">([^<]*)<\/pre>/);
  assert.ok(match, "Browser probe did not run; inspect browser console and module loading");
  const report = JSON.parse(match[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&"));
  assert.equal(report.count, 576);
  assert.ok(report.populated);
  assert.ok(report.firstWidth > 0, "SVG cells must be visible");
  assert.match(report.painted, /^rgb\(/);
  assert.ok(report.initialLightness > 0.74 && report.initialLightness < 0.76);
  assert.ok(report.changedOnOuter);
  assert.ok(report.restored);
  assert.ok(report.selectedInner);
  assert.ok(report.initialInnerSelected, "Native Inner radio must start checked");
  assert.ok(report.mobile, "Browser regression must use a mobile-width viewport");
  assert.ok(report.bothBoundariesUpdated, "Crenellation slider should reshape both inner and outer ribbon boundaries");
  assert.ok(report.shapeLabelUpdated, "Crenellation slider should report flatter crests and valleys, got " + JSON.stringify(report.shapeLabelText));
  assert.ok(report.initiallyFolded, "Colour picker should start folded on mobile");
  assert.ok(report.expandedBySummary, "Tapping Colours should expand the picker");
  assert.ok(report.expandedHeight > report.foldedHeight + 150, "Folding should reclaim substantial vertical space");
  assert.ok(report.geometryVisibleWithImage, "First geometry slider should be visible beneath the image at phone height");
  assert.ok(report.foldedAfterEditing, "Picker should collapse on second summary tap");
  assert.ok(report.reopenedPreservesColours, "Folding must not reset edited colour state");
  assert.ok(report.swatchCurrent, "Folded summary swatches must reflect the edited colour");
  assert.equal(report.radioCount, 2, "There must be exactly two native radio inputs");
  assert.equal(report.customDots, 0, "No simulated selection markers allowed");
  assert.ok(report.innerOnly, "Lightness slider should change Inner but not Outer");
  assert.ok(report.outerSelected, "Outer native radio must become checked on selection");
  assert.ok(report.outerOnly, "Lightness slider should change Outer but not Inner");
  assert.ok(report.lightnessRestored, "Switching back to Inner should restore Inner slider position");
  assert.ok(report.resetCorrect, "Reset should restore both colours and select Inner");
});
