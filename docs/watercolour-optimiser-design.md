# Watercolour Effect Optimiser — design note

## Status

Implementation handoff for the next development step after PR #12.

The Watercolour Effect (WCE) forward model is now merged on `main`. This note
defines the optimiser to be built on top of that model. It is intentionally a
design/implementation contract rather than another model proposal.

**Do not introduce a parallel WCE model.** The optimiser must use
`colourshift.watercolour.predict_watercolour()` as the authoritative forward
prediction API.

## 1. Goal

Given a fixed physical field colour, find physically valid inner- and
outer-contour sRGB colours that maximise the modelled **chromatic Watercolour
Effect** within the calibrated geometry domain.

The primary artistic use case is:

> For a chosen neutral or coloured field, find a double-contour colour pair
> predicted to create the largest phantom chromatic shift in the enclosed
> surface.

The optimiser should also return the geometry that maximises the calibrated
geometry response, but geometry and colour must remain factorised exactly as
they are in the forward model.

The first implementation should be usable programmatically and from the
`colourshift-watercolour` CLI. A GUI is explicitly out of scope for this
step.

## 2. Existing model contract

The public forward API is:

```python
from colourshift.watercolour import WatercolourGeometry, predict_watercolour

prediction = predict_watercolour(
    field_rgb=(1.0, 1.0, 1.0),
    inner_rgb=(1.0, 0.72, 0.0),
    outer_rgb=(0.32, 0.36, 0.85),
    geometry=WatercolourGeometry(),
)
```

The relevant prediction outputs are:

- `chromatic_shift_uv`: Euclidean displacement in CIE 1976 `u'v'`.
- `relative_luminance_shift`: predicted luminance change, reported separately.
- `predicted_rgb_unclipped`: model appearance output; may lie outside display
  gamut and **must not be silently clipped for scoring**.
- `geometry_gain`: scalar strength of the calibrated geometry stage.

The forward model deliberately does **not** expose a unified perceptual
`Delta E`. The filling-in magnitude is not calibrated to human observers and
can produce appearance coordinates outside display gamut. The optimiser must
therefore not reintroduce CAM02-UCS, raw opponent-vector norm, clipped RGB
distance, or another invented scalar as the primary objective.

## 3. Scientific guardrails

The optimiser is only as valid as the forward model. It must preserve the
following boundaries.

### Supported physical geometry

`WatercolourGeometry` already enforces:

- total double-contour width: 6–24 arcmin;
- inner:outer width ratio: 1:2–2:1;
- figure diameter: 2.3–4.5 degrees;
- contour frequency: 4–20 cycles/revolution.

The model represents adjacent, visibly wavy double contours.

Do not optimise:

- straight contours;
- separated contours / gaps;
- contour modulation amplitude;
- geometry outside the encoded psychophysical domain.

Those are not supported by the current public model.

### Supported colour inputs

Physical colours supplied to `predict_watercolour()` are sRGB triples with
all channels in `[0, 1]`.

The optimiser may search the full sRGB cube for both contours. It must not
clip invalid candidates after evaluation: candidates must be generated inside
the valid domain.

### Calibration versus validation

The geometry response encodes published psychophysical scales plus explicit
modelling assumptions. Its maxima are therefore **calibrated model behaviour**,
not independently discovered optimisation results. Optimiser output and docs
must not describe the geometry optimum as a new empirical prediction.

## 4. Key architectural consequence: do not build a 10-D joint optimiser

The merged forward model is intentionally factorised:

```text
colour/luminance drive × geometry gain -> final WCE shift
```

Geometry gain is independent of contour colour.

Therefore a numerical optimiser over six RGB variables plus four geometry
variables would:

1. waste expensive forward-model evaluations;
2. obscure the model architecture;
3. make convergence harder to interpret;
4. risk reintroducing the monolithic design that PR #12 deliberately removed.

The optimisation must instead be decomposed.

### 4.1 Geometry subproblem

Within the full supported domain, the calibrated geometry maximum is known by
construction:

- total width = 15 arcmin;
- inner width = outer width = 7.5 arcmin;
- diameter = 3.2 degrees;
- curvature-frequency gain reaches its plateau at 12 cpr.

Any frequency in `[12, 20]` has the same frequency gain. Use **12 cpr as the
canonical tie-break** because it is the lowest contour frequency that achieves
the calibrated plateau and therefore the least geometrically elaborate
solution.

The default optimal geometry is consequently:

```python
WatercolourGeometry(
    inner_width_arcmin=7.5,
    outer_width_arcmin=7.5,
    diameter_deg=3.2,
    frequency_cpr=12.0,
)
```

Implement this as a named helper, e.g.:

```python
def optimal_watercolour_geometry() -> WatercolourGeometry:
    ...
```

Do not use a numerical optimiser to rediscover these values under the default
domain.

A future extension may optimise geometry under user-imposed physical
constraints, such as a fixed canvas diameter or fixed contour width. That is
not part of the first implementation.

### 4.2 Colour subproblem

The expensive numerical search is only over:

```text
inner_r, inner_g, inner_b,
outer_r, outer_g, outer_b
```

with each variable bounded to `[0, 1]`.

For every colour candidate, evaluate the authoritative forward model at either:

- the canonical optimal geometry; or
- a caller-supplied fixed `WatercolourGeometry`.

## 5. Objective

### Primary objective

Maximise:

```python
prediction.chromatic_shift_uv
```

This is the explicit chromatic WCE score used by the current model and is in
the same CIE 1976 `u'v'` coordinate system used for the published quantitative
comparison.

For minimisation APIs, use:

```python
objective = -prediction.chromatic_shift_uv
```

### Luminance is not part of the scalar objective

Always report `relative_luminance_shift` for the optimum.

Do **not** combine chromatic shift and luminance into a weighted sum in v1.
There is no validated weight relating them.

The implementation should be structured so a later optional constraint such
as

```text
abs(relative_luminance_shift) <= L_max
```

could be added, but no arbitrary default threshold should be invented now.

### No silent clipping

If `predicted_rgb_unclipped` is outside `[0, 1]`, retain it as diagnostic
output. The objective remains `chromatic_shift_uv`.

Do not clip the modelled appearance and then rescore it.

## 6. Search algorithm

Use `scipy.optimize.differential_evolution` for the first implementation.

Reasons:

- six-dimensional bounded continuous black-box search;
- forward model is nonlinear and not guaranteed convex;
- gradients are neither exposed nor justified;
- SciPy is already a project dependency;
- deterministic seeded runs are supported;
- the method is simple enough to audit.

Recommended initial configuration:

```python
bounds = [(0.0, 1.0)] * 6

differential_evolution(
    objective,
    bounds,
    seed=config.seed,
    popsize=config.popsize,
    maxiter=config.maxiter,
    tol=config.tol,
    polish=config.polish,
    updating="immediate",
    workers=1,
)
```

Do not enable multiprocessing in the first implementation. It complicates
determinism, packaging, tests and GUI integration. Parallelism can be added
after profiling.

### Evaluation budget

The raster colour-drive calculation is substantially more expensive than the
geometry functions. The optimiser configuration must therefore expose the
search budget rather than burying a very large default.

Suggested defaults:

```python
seed = 0
popsize = 8
maxiter = 20
tol = 1e-4
polish = True
```

For six dimensions this is already a nontrivial number of forward evaluations.
Benchmark it before increasing the defaults.

Do not weaken the forward model resolution or substitute a surrogate simply to
make optimisation faster in the first PR.

## 7. Proposed public API

Add `colourshift/watercolour/optimise.py` (British spelling to match the
project language) with roughly the following public types.

```python
@dataclass(frozen=True)
class WatercolourOptimisationConfig:
    seed: int = 0
    popsize: int = 8
    maxiter: int = 20
    tol: float = 1e-4
    polish: bool = True


@dataclass(frozen=True)
class WatercolourOptimisationResult:
    field_rgb: RGB
    background_rgb: RGB
    inner_rgb: RGB
    outer_rgb: RGB
    geometry: WatercolourGeometry
    prediction: WatercolourPrediction
    evaluations: int
    success: bool
    message: str
    seed: int


def optimal_watercolour_geometry() -> WatercolourGeometry:
    ...


def optimise_watercolour(
    *,
    field_rgb: RGB,
    background_rgb: RGB | None = None,
    geometry: WatercolourGeometry | None = None,
    config: WatercolourOptimisationConfig | None = None,
) -> WatercolourOptimisationResult:
    ...
```

Semantics:

- `geometry=None`: use `optimal_watercolour_geometry()`.
- supplied `geometry`: hold that geometry fixed and optimise only contour
  colours.
- `background_rgb=None`: retain the forward model convention that background
  equals the field.
- result `prediction` must be generated by a final direct call to
  `predict_watercolour()` using the returned colours and geometry.
- `evaluations` should report the actual objective evaluation count if
  available from SciPy.

Export the public optimiser symbols from `colourshift.watercolour.__init__`.

## 8. Internal implementation requirements

### One source of truth

The objective function must call `predict_watercolour()`. Do not duplicate:

- the edge model;
- opponent conversion;
- geometry gain;
- `u'v'` conversion;
- model constraints.

Validation belongs in the existing forward API.

### Candidate decoding

Keep decoding explicit:

```python
def _decode_colours(x):
    inner = tuple(float(v) for v in x[:3])
    outer = tuple(float(v) for v in x[3:])
    return inner, outer
```

Avoid hidden colour-space transformations in v1.

### Objective failures

A valid in-bounds colour candidate should normally evaluate successfully. If a
candidate produces a non-finite score, treat it as a bad candidate using a
large finite penalty and count/report it. Do not let one numerical exception
terminate the whole global search unless it indicates a programming error.

Do not broadly catch all exceptions around `predict_watercolour()`; input and
programming errors should remain visible.

### Reproducibility

A run with the same:

- field;
- background;
- fixed geometry;
- optimiser configuration;
- seed

must return the same result within numerical tolerance on the same SciPy
version/platform.

Include the seed and optimiser settings in CLI JSON output.

## 9. CLI

Extend the existing `colourshift-watercolour` CLI with an `optimise`
subcommand.

Suggested interface:

```bash
uv run colourshift-watercolour optimise \
    --field "#ffffff" \
    --output result.json \
    --seed 0
```

Optional:

```text
--background "#ffffff"
--inner-width-arcmin ...
--outer-width-arcmin ...
--diameter-deg ...
--frequency-cpr ...
--popsize ...
--maxiter ...
--tol ...
--no-polish
```

Geometry arguments should be **all-or-none** for v1. If none are supplied, use
the canonical optimal geometry. If custom geometry is supplied, construct
`WatercolourGeometry` and allow its existing validation to reject unsupported
values.

JSON output should contain:

- field/background RGB and hex;
- optimal inner/outer RGB and hex;
- geometry;
- `chromatic_shift_uv`;
- `relative_luminance_shift`;
- `predicted_rgb_unclipped`;
- optimiser configuration;
- evaluation count;
- success/message.

Do not add a GUI in this implementation.

## 10. Tests

The optimiser PR should add focused tests without turning CI into a full
expensive optimisation benchmark.

### Geometry tests

1. `optimal_watercolour_geometry()` returns:
   - 7.5 / 7.5 arcmin;
   - 3.2 degrees;
   - 12 cpr.
2. Its `geometry_gain` is approximately 1.
3. The helper returns a valid `WatercolourGeometry`.

### Orchestration tests

Use monkeypatching for most optimiser-control tests so they are fast.

Test that:

1. candidate vectors decode to the correct inner/outer RGB triples;
2. objective is the negative of `chromatic_shift_uv`;
3. caller-supplied geometry is passed unchanged;
4. final result is re-evaluated through `predict_watercolour()`;
5. fixed seed/config is propagated to SciPy;
6. optimiser metadata/evaluation count is preserved;
7. invalid field/background input still fails through the normal model
   validation rather than being swallowed.

### One real-model smoke test

Include one deliberately small-budget real optimisation, for example
`maxiter=1`, with a fixed seed.

It should assert only robust properties:

- returned channels are in `[0, 1]`;
- returned geometry is valid;
- final score is finite and non-negative;
- result prediction exactly matches a direct `predict_watercolour()` call for
  the returned candidate.

Do **not** assert a particular RGB optimum from a tiny optimisation budget.

### CLI tests

Test parsing and JSON schema with the optimiser function monkeypatched. Do not
run a full differential-evolution search in CLI tests.

### Existing regression suite

All existing tests must remain unchanged/passing unless an API export requires
a minimal update.

Required gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## 11. Performance and profiling

Before changing the search algorithm, record:

- time for one `predict_watercolour()` evaluation;
- total evaluations and wall-clock time for the default optimiser;
- fraction of time spent in the internal edge model.

If default optimisation is impractically slow, open a separate optimisation
issue. Do not solve performance by introducing a second approximate forward
model in the same PR.

Possible later approaches, only after profiling:

- cache fixed reference masks;
- cache constant field/background transforms;
- expose an internal colour-drive evaluator that preserves exactly the same
  mathematics;
- parallel objective evaluation;
- surrogate/coarse-to-fine search.

Any acceleration must be regression-tested against
`predict_watercolour()`.

## 12. Important design implications for the artwork

The model's unconstrained geometry optimum is not something the colour
optimiser needs to discover. It is already encoded by the calibration. The
scientifically interesting numerical search is the colour pair.

This also means the optimiser can later support practical painting constraints
cleanly:

- fix the geometry dictated by a composition and optimise only colour;
- fix one contour colour because a particular paint is desired;
- restrict colours to a real paint catalogue;
- search for a target phantom hue rather than maximum shift;
- add a luminance-shift constraint;
- convert angular contour widths to physical millimetres for a chosen viewing
  distance.

Those should be later, explicit extensions of the same optimiser, not alternate
models.

## 13. Explicit non-goals for the first optimiser PR

Do not:

- modify `predict_watercolour()` merely to make optimisation easier;
- add a second WCE forward model;
- refit geometry parameters;
- numerically optimise the default geometry;
- optimise modulation amplitude;
- extrapolate to straight or separated contours;
- use raw opponent-vector norm as an objective;
- reintroduce CAM02-UCS `Delta E` for the WCE output;
- clip `predicted_rgb_unclipped` before scoring;
- add paint-name lookup;
- add viewing-distance-to-mm conversion;
- add GUI controls;
- claim human-observer calibrated magnitude.

## 14. Suggested implementation sequence

1. Add `optimise.py` dataclasses and `optimal_watercolour_geometry()`.
2. Add candidate decoder and objective wrapper around
   `predict_watercolour()`.
3. Implement seeded SciPy differential evolution.
4. Add unit/orchestration tests.
5. Add one low-budget real-model smoke test.
6. Export optimiser API.
7. Add CLI `optimise` command and JSON output.
8. Add CLI tests.
9. Run lint, format and full tests.
10. Benchmark the default configuration and record the result in the PR.

## 15. Acceptance criteria

The optimiser implementation is complete when:

- there remains exactly one public WCE forward model;
- default geometry selection is deterministic and contains no numerical search;
- only the six contour-colour channels are globally optimised by default;
- the objective is exactly `chromatic_shift_uv`;
- luminance is reported separately, not silently weighted into the objective;
- no modelled appearance clipping affects the score;
- custom fixed geometry is supported through `WatercolourGeometry`;
- seeded optimisation is reproducible;
- CLI JSON contains enough metadata to reproduce a run;
- the full existing test suite plus optimiser tests passes;
- Ruff lint and formatting checks pass;
- no unsupported scientific claim is added to README or API docs.

## 16. Likely files

Expected additions/changes:

```text
colourshift/watercolour/optimise.py          # new
colourshift/watercolour/__init__.py          # export optimiser API
colourshift/watercolour/cli.py               # add optimise command
tests/test_watercolour_optimise.py           # new
tests/test_watercolour_cli.py                # extend CLI tests if appropriate
README.md                                     # brief usage example only
```

Avoid touching the internal edge model or geometry calibration modules unless a
genuine bug is discovered.
