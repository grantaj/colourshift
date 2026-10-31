# ColourShift cleanup and exhibition web app roadmap

## Purpose

ColourShift now contains two related kinds of work:

1. a Python reference implementation for contextual colour-shift searches using CIECAM02/CAM02-UCS; and
2. browser-based experimental tools under `docs/`, including the Watercolour Explorer.

The next major goal is an exhibition-oriented ColourShift web app that lets visitors design and explore their own colour shifts. Before implementing that app, the Python colour-shift core should be brought to a trustworthy stopping point: numerically unambiguous, explicit about search semantics, reproducible, and covered by portable reference tests.

This roadmap is deliberately not a proposal to turn the Tk application into a heavily engineered desktop product. Once the reference implementation is sound, new feature work should move to the browser app.

## Current repository state

The May package refactor remains a useful foundation:

- `colourshift/core/` contains colour-model and search logic;
- `colourshift/io/` contains export logic;
- `colourshift/ui/` contains the Tk UI;
- `colourshift/cli.py` provides headless/reproducible searches;
- tests cover the core, CLI and exports.

Since that refactor, the repository has also gained the Watercolour Effect model and a fully client-side Watercolour Explorer under `docs/watercolour/`. That explorer is an important precedent for the exhibition app: it is static, runs entirely in the browser, is served by GitHub Pages, and has JavaScript checks/tests in CI.

The existing paper remains at `docs/index.html` and should not be displaced by the new app.

## Cleanup before the web app

The umbrella issue is #10. The individual issues are ordered below by dependency rather than issue number alone.

### Phase 1 — numerical and application correctness

#### #2 — Audit CIECAM02 viewing-condition parameter usage

This is the highest-priority item.

The current `XYZ_to_CIECAM02()` call passes the configuration values positionally. The names in `Config` suggest that `background_luminance` and `adapting_luminance` may be mapped to `Y_b` and `L_A` in the wrong order.

Resolve this before treating any current numerical output as authoritative.

Required outcome:

- verify the intended physical/model meanings and units;
- make the `colour-science` call unambiguous, preferably with keywords;
- correct the mapping if necessary;
- add a regression test that would detect an interchange;
- regenerate/re-check affected examples and paper values if the numerical output changes.

#### #3 — Fix GUI result state and JSON export

The GUI currently updates `self.results` only on the maximal-shift result path. Sensitive-base and strongest-surround searches can therefore leave export state empty or stale.

Required outcome:

- displayed results and exported results always describe the same completed search;
- result state includes the mode/configuration that generated it;
- stale results cannot silently be exported as current.

#### #4 — Apply search configuration consistently

The `Min ΔE` slider is explicitly passed by the maximal-shift path, but other GUI search modes currently fall back to default configuration.

Required outcome:

- construct one search configuration from the current UI state;
- use it for every search mode;
- export the configuration actually used.

#### #5 — Prevent stale asynchronous GUI results

Tk searches run in a background thread, but the inputs can change while a search is in flight. A result can therefore be calculated for one colour pair and displayed against another.

Required outcome:

- either lock relevant inputs while a search is running, or version searches and discard obsolete completions;
- invalidate old results when their inputs/configuration no longer match the current state;
- keep Tk operations on the main thread.

These GUI fixes are intentionally bounded. They should make the existing application correct, not initiate a large UI rewrite.

### Phase 2 — make the Python core a reference implementation

#### #6 — Replace boolean search semantics with named operations

`find_extreme_shift_colors(..., fixed_as_base=True/False)` hides domain semantics behind a boolean.

Expose explicit operations such as:

```python
find_maximal_surround_shift(...)
find_strongest_surrounds(...)
find_sensitive_bases(...)
```

Shared grid/evaluation/filtering machinery can remain private.

The important result is that a caller — including a browser implementation — can understand each search without reproducing knowledge about what a boolean flag means.

#### #7 — Add language-neutral numerical regression fixtures

After #2 is settled, add a small JSON reference suite that can be consumed by both Python and browser code.

The fixture set should cover representative cases for:

- sRGB/hex conversion;
- sRGB to XYZ;
- CIECAM02 JMh under the chosen viewing conditions;
- CAM02-UCS conversion;
- CAM02-UCS ΔE;
- each search operation on a small deterministic RGB grid;
- candidate ordering;
- minimum-separation filtering.

These fixtures are the compatibility oracle for the browser port. The browser implementation does not need to share code with Python if it agrees with the same reference vectors.

#### #9 — Document the numerical contract

Once #2 and #6 are resolved, document the implementation-facing algorithm independently of the broader paper.

The contract should specify:

```text
sRGB
  -> XYZ
  -> CIECAM02 JMh under explicit viewing conditions
  -> CAM02-UCS
  -> ΔE_CAM02-UCS
  -> candidate ranking
  -> perceptual-separation filtering
```

It should also define the reference appearance used by each search operation and distinguish adjustable search defaults from properties of the perceptual model itself.

### Phase 3 — repository support

Issue #8 proposed minimal GitHub Actions CI. Current `main` now already contains `.github/workflows/ci.yml` running Python lint/format/tests plus JavaScript checks for the Watercolour Explorer.

Therefore #8 should be verified against its acceptance criteria and closed if satisfied rather than reimplemented.

## Definition of done for the Python cleanup

Start the web implementation when:

- there is no known ambiguity in the CIECAM02 parameter mapping;
- each search mode has explicit core semantics;
- representative numerical outputs are locked down in portable fixtures;
- Python tests consume those fixtures;
- CI enforces the relevant checks;
- the numerical algorithm is documented well enough to reproduce independently;
- the Tk app no longer knowingly exports stale or incorrectly configured results.

At that point, avoid further Tk refactoring unless it directly supports correctness or reference-model clarity.

---

# Exhibition web app

## Goal

Build a simple, immediate browser experience in which an exhibition visitor can choose colours and design a contextual colour shift without needing to understand CIECAM02 or the research implementation.

The visitor-facing interaction should be much simpler than the research/Tk interface.

A plausible core flow is:

```text
choose a target colour
        ↓
choose a starting surround
        ↓
find strong alternative surrounds
        ↓
inspect a few large visual comparisons
        ↓
choose / adjust / try again
```

The exact exhibition interaction can evolve during UI design, but the scientific calculation should remain traceable to the Python reference implementation.

## Deployment constraints

The app should:

- be served from GitHub Pages;
- run entirely client-side;
- require no server, API, account or database;
- have no runtime dependency on the Python desktop application;
- be touch-friendly and work well on phones and tablets;
- keep the existing paper at `docs/index.html` intact;
- coexist with the existing `docs/watercolour/` explorer.

A dedicated path such as `docs/shift/` would keep the new experience separate from both the paper and the Watercolour Explorer.

## Recommended architecture

Start with the simplest architecture that can reproduce the reference results:

```text
GitHub Pages
    |
    +-- HTML/CSS
    |
    +-- browser UI
    |
    +-- native JavaScript ES modules
            |
            +-- colour conversion
            +-- CIECAM02 / CAM02-UCS
            +-- ColourShift search
```

This mirrors the successful static pattern already used by the Watercolour Explorer.

The current default search grid is small enough that performance should be measured before adding infrastructure. If search work causes noticeable UI blocking, move the numerical search into a Web Worker while keeping the same pure numerical module.

### WASM / Pyodide

Do not make WebAssembly a requirement for the first implementation.

Pyodide/WASM remains a useful fallback if direct browser reproduction of the Python numerical behaviour proves difficult. It would allow the Python reference implementation (or a close subset) to run client-side, at the cost of a much larger runtime and slower startup.

Use WASM/Pyodide only if one of these becomes true:

- a native JavaScript implementation cannot reproduce the reference fixtures reliably;
- a required numerical dependency is impractical to implement/use in JavaScript;
- measured performance shows a real need.

For the exhibition experience, a small native browser implementation is preferable if it agrees with the reference vectors.

## Browser implementation boundaries

The browser numerical code should be a pure module with no DOM dependency. This makes it testable in Node as well as in the browser.

For example:

```text
docs/shift/
    index.html
    shift.css
    app.js
    colourshift-core.js
```

If a worker is needed later:

```text
    search-worker.js
```

The UI should call named domain operations corresponding to the Python reference API rather than reproducing generic boolean modes.

## Cross-language verification

The most important engineering rule for the web port is that Python and browser implementations share **test data**, not necessarily implementation code.

The JSON fixtures from #7 should be exercised in both environments:

```text
reference fixture
      /     \
 Python     browser/Node
   |             |
 expected == observed
```

Test intermediate colour-model values as well as final search outputs. This makes numerical disagreements easy to localise.

Suggested tolerances should be explicit and chosen for floating-point colour calculations rather than exact string/bit equality.

## Web-app testing

Extend the existing CI rather than introducing a separate test system.

At minimum:

- syntax/module checks for browser JavaScript;
- Node tests for the pure numerical module;
- fixture parity tests against #7;
- focused DOM/UI tests for important state transitions if needed.

A full browser automation stack is not required initially unless real interaction bugs justify it.

## Exhibition-specific design principles

The public app should hide research controls that visitors do not need.

Prefer:

- large colour fields and comparisons;
- a small number of obvious actions;
- touch-sized controls;
- immediate visual feedback;
- good behaviour at narrow phone widths;
- no requirement to understand `J`, `M`, `h`, viewing-condition constants or grid density.

Scientific/configuration details can be exposed behind an optional information panel if useful, but should not dominate the experience.

The app should make clear that it is a model-driven exploration of contextual colour appearance, not a guarantee that every observer/display/lighting environment will experience an identical magnitude of shift.

## Out of scope for the first exhibition version

Unless a concrete exhibition requirement changes this, the first version does not need:

- server-side computation;
- accounts or saved cloud state;
- a database;
- parity with every Tk control;
- integration with the Watercolour Effect model;
- a large JavaScript framework;
- Rust/C++ WASM;
- Pyodide merely to avoid writing the small required colour-model subset.

## Implementation sequence

1. Complete/verify the Python cleanup, especially #2.
2. Create and lock down the portable reference fixtures (#7).
3. Implement the pure browser numerical core.
4. Run the same fixtures against Python and JavaScript until they agree.
5. Build the minimal exhibition UI around the verified core.
6. Benchmark search responsiveness on representative phones/tablets.
7. Add a Web Worker only if needed.
8. Consider WASM/Pyodide only if parity or performance provides a concrete reason.
9. Add the new static app under `docs/` and include it in the existing CI/Pages workflow.
10. Test the actual exhibition path (QR code, phone/tablet, network conditions, display appearance) before freezing the installation.

## Relationship to the Watercolour Explorer

The Watercolour Explorer is useful as an engineering precedent, not as part of the same user workflow.

Reuse its successful repository/deployment conventions where appropriate:

- static files under `docs/`;
- GitHub Pages hosting;
- no backend;
- deterministic browser-side generation;
- simple JavaScript checks/tests in the existing CI.

Keep the two experiences conceptually separate. The ColourShift exhibition app is about surround-induced colour appearance shift; the Watercolour Explorer is about the Watercolour Effect and has its own model and experimental controls.
