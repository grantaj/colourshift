# Watercolour Effect optimisation design

Status: implementation handoff  
Base branch: `main` after PR #12  
Target implementation module: `colourshift/watercolour/optimisation.py`

## 1. Purpose

Add an optimiser for the single supported Watercolour Effect (WCE) forward
model.

The artistic/scientific goal is to find physically realisable contour colours
that maximise the predicted chromatic shift of a fixed field colour, while
remaining explicit about the model's limits.

The optimiser must use the existing public model:

```python
from colourshift.watercolour import WatercolourGeometry, predict_watercolour
```

It must not introduce a second WCE model or bypass the calibrated public model
with a parallel approximation.

## 2. Current model contract

`predict_watercolour(...)` takes:

- `field_rgb`: physical field colour, sRGB in [0, 1]
- `inner_rgb`: inner contour colour, sRGB in [0, 1]
- `outer_rgb`: outer contour colour, sRGB in [0, 1]
- optional `background_rgb`, also sRGB in [0, 1]
- `WatercolourGeometry`

It returns:

- `chromatic_shift_uv`: CIE 1976 u'v' displacement of the predicted field
  appearance relative to the physical field
- `relative_luminance_shift`: predicted relative luminance change
- `predicted_rgb_unclipped`: model appearance coordinate; this can be outside
  display gamut and must not be silently clipped for scoring
- `geometry_gain`
- `opponent_shift`: internal diagnostic only

The optimiser must treat `chromatic_shift_uv` as the supported chromatic WCE
score. It must not use Euclidean norm in raw opponent coordinates as a
perceptual objective.

There is deliberately no unified perceptual Delta E for WCE at present.
Chromatic shift and luminance shift are separate quantities.

## 3. Scope

### In scope for the first implementation

1. Fix the field colour.
2. Optionally fix the background colour; default background = field.
3. Optimise the inner and outer contour colours jointly.
4. Allow either contour colour to be fixed by the caller while optimising the
   other.
5. Use the existing calibrated geometry, with a caller-supplied
   `WatercolourGeometry` or the model default.
6. Maximise `chromatic_shift_uv`.
7. Optionally impose a caller-specified maximum absolute luminance shift:
   `abs(relative_luminance_shift) <= limit`.
8. Return the best candidate plus useful alternative candidates and complete
   reproducibility metadata.
9. Be deterministic for a fixed seed/configuration.
10. Add tests and documentation.

### Explicitly out of scope

- fitting or changing the WCE forward model
- inventing a combined chromatic/luminance perceptual score
- optimising outside the calibrated geometry domain
- straight contours
- separated contours
- modulation-amplitude optimisation
- paint-name/Dulux mapping
- physical spectral reflectance optimisation
- observer-specific calibration
- matching the phantom colour with a second physical paint
- GUI integration in the first optimiser PR

Those can be separate later steps.

## 4. Do not numerically optimise geometry in this first optimiser

The current model is explicitly factorised:

```
colour/luminance drive × geometry_gain
```

and the geometry term is independent of contour colour.

Within the calibrated model, the reference/default geometry is already the
model maximum by construction:

- total double-contour width = 15 arcmin
- inner:outer width ratio = 1:1
- diameter = 3.2 degrees
- frequency >= 12 cycles/revolution gives the calibrated frequency plateau

The default `WatercolourGeometry()` chooses 12 cpr, the lowest frequency on
that plateau and therefore the least geometrically elaborate maximiser.

Consequently a general-purpose continuous geometry optimiser would merely
rediscover calibration assumptions and would misrepresent that result as a new
prediction.

For the first implementation:

- geometry is an input, not an optimisation variable;
- default to `WatercolourGeometry()`;
- document that this is the model's calibrated maximum-strength geometry;
- if a future artistic objective trades WCE strength against execution
  simplicity, line density, or another real cost, that should be a separate
  multi-objective geometry problem.

## 5. Optimisation variables

Optimise physical contour sRGB values directly.

When both contours are free:

```
x = (
    inner_r, inner_g, inner_b,
    outer_r, outer_g, outer_b,
)
```

with each component constrained to [0, 1].

When one contour is fixed, remove its three variables from the optimiser rather
than optimising variables that are ignored.

Do not optimise `predicted_rgb_unclipped`; it is an output appearance
coordinate, not a physical input colour.

### Why optimise sRGB first

The production model already defines its physical colour inputs in sRGB.
Optimising directly in that domain:

- cannot produce invalid physical input coordinates;
- avoids introducing another gamut mapping layer;
- keeps the first implementation easy to audit.

A future optimiser may use a perceptually more uniform parameterisation if
there is evidence that it materially improves convergence, but the objective
must still be evaluated by `predict_watercolour()`.

## 6. Objective and luminance handling

### Primary objective

Maximise:

```
prediction.chromatic_shift_uv
```

or equivalently minimise its negative.

### Luminance is a constraint, not a hidden penalty

Do not combine chromatic shift and luminance shift with an arbitrary weighted
sum.

Add an optional configuration value:

```python
max_abs_relative_luminance_shift: float | None = None
```

If it is `None`, optimise chromatic shift irrespective of luminance shift and
report the signed luminance result.

If supplied, candidates must satisfy:

```
abs(prediction.relative_luminance_shift)
    <= max_abs_relative_luminance_shift
```

A caller who cares about a predominantly chromatic phantom colour can therefore
state that constraint explicitly. There must be no undocumented default
threshold.

If no feasible candidate is found, return a clear unsuccessful result rather
than silently relaxing the constraint.

## 7. Search algorithm

Use SciPy's `differential_evolution`.

Reasons:

- the forward model is nonlinear;
- gradients are not available;
- the dimension is only 3 or 6;
- bounds are simple;
- SciPy is already a project dependency;
- deterministic seeded runs are available.

Do not add a new optimisation dependency.

Suggested default configuration:

```python
@dataclass(frozen=True)
class WatercolourOptimiserConfig:
    seed: int = 0
    population_size: int = 12
    max_generations: int = 40
    tolerance: float = 1e-5
    polish: bool = True
    alternatives: int = 8
    max_abs_relative_luminance_shift: float | None = None
```

Map `population_size` to SciPy's `popsize` deliberately and document that
SciPy interprets it as a multiplier of parameter dimension.

The exact defaults may be adjusted after a small runtime/convergence benchmark,
but keep them explicit and deterministic.

### Constraint implementation

Prefer a real nonlinear constraint or a cached feasibility evaluator rather
than a magic penalty coefficient.

If SciPy's constraint API makes the implementation unnecessarily complicated,
a finite penalty is acceptable only if:

- the penalty is structurally guaranteed to rank every infeasible candidate
  below every feasible candidate;
- the reason is documented;
- tests cover it.

Do not use arbitrary coefficients such as
`score = chromatic_shift - 10 * luminance_shift`.

## 8. Avoid duplicate expensive model evaluations

One call to `predict_watercolour()` runs the internal 256×256 edge/filling-in
reference model. Optimisation will make many calls.

Implement a small evaluation object that:

1. maps an optimiser vector to inner/outer RGB;
2. calls `predict_watercolour()` once;
3. caches the prediction for that exact candidate;
4. exposes objective and constraint values from the same prediction.

The cache can be process-local and bounded/simple. Exact tuple keys are
sufficient; do not introduce approximate floating-point cache matching.

Before attempting more invasive performance work, benchmark this implementation.
Do not duplicate or reimplement the private colour-drive engine merely for
speed.

## 9. Result API

Add public dataclasses similar to:

```python
@dataclass(frozen=True)
class WatercolourCandidate:
    inner_rgb: tuple[float, float, float]
    outer_rgb: tuple[float, float, float]
    prediction: WatercolourPrediction

@dataclass(frozen=True)
class WatercolourOptimisationResult:
    best: WatercolourCandidate | None
    alternatives: tuple[WatercolourCandidate, ...]
    success: bool
    message: str
    evaluations: int
    seed: int
```

The exact names may change if a cleaner design emerges, but retain these
semantics.

The best candidate is the feasible candidate with maximum
`chromatic_shift_uv`.

### Alternatives

The optimiser should return several useful alternatives rather than only a
single point.

Use the final differential-evolution population and any polished optimum:

1. evaluate all candidates;
2. discard infeasible candidates;
3. sort by descending `chromatic_shift_uv`;
4. remove numerically duplicate RGB pairs;
5. return up to `config.alternatives`.

For the first implementation, exact/numerical deduplication is enough.
Do not invent a perceptual diversity metric as part of this PR.

A later feature can deliberately select visually diverse Pareto alternatives.

## 10. Public function

Target API:

```python
def optimise_watercolour(
    *,
    field_rgb: RGB,
    background_rgb: RGB | None = None,
    geometry: WatercolourGeometry | None = None,
    fixed_inner_rgb: RGB | None = None,
    fixed_outer_rgb: RGB | None = None,
    config: WatercolourOptimiserConfig | None = None,
) -> WatercolourOptimisationResult:
    ...
```

Rules:

- at least one of inner/outer must be free;
- supplied fixed colours are validated through the same [0, 1] contract as the
  forward model;
- `geometry=None` means `WatercolourGeometry()`;
- do not mutate the caller's values;
- no GUI side effects;
- no files written by the library function.

Export the optimiser API from `colourshift.watercolour.__init__`.

Use British spelling consistently with `colour`:
`optimise_watercolour`, `WatercolourOptimiserConfig`,
`WatercolourOptimisationResult`.

## 11. Candidate validity and failure handling

The optimiser must never silently clip physical input colours.

Every inner/outer colour evaluated must already be in [0, 1].

The forward model may return `predicted_rgb_unclipped` outside [0, 1].
That is not by itself a failed candidate; it is an internal predicted appearance
coordinate and is already part of the model contract.

A candidate is infeasible only when:

- the public forward model raises for invalid inputs/domain;
- a configured luminance constraint is violated;
- the resulting objective is non-finite.

Numerical exceptions should be contained at the optimiser boundary and reported
as failed evaluations, not crash the whole global search unless they indicate a
programming error.

Do not broadly catch `Exception`. Catch only expected numerical/model-domain
errors.

## 12. Geometry helper

It is useful to make the calibrated geometry recommendation explicit, but do
not pretend it was numerically discovered.

A small helper is acceptable:

```python
def recommended_watercolour_geometry() -> WatercolourGeometry:
    return WatercolourGeometry()
```

Its docstring should state that it returns the model's calibrated
maximum-strength reference geometry, including the lowest cpr on the frequency
plateau.

This helper is optional; simply documenting the default may be cleaner.

## 13. Tests

Add focused tests in `tests/test_watercolour_optimisation.py`.

Required tests:

1. **Determinism**
   Two runs with the same small test configuration and seed return the same
   best RGB pair and score within numerical tolerance.

2. **Valid bounds**
   Every returned physical contour channel is in [0, 1].

3. **Forward-model consistency**
   Re-evaluating the returned best colours with `predict_watercolour()`
   reproduces the stored prediction.

4. **Improvement over a fixed baseline**
   With a deliberately modest baseline contour pair, a small optimiser run
   returns a chromatic score at least as large.

5. **Fixed inner contour**
   When `fixed_inner_rgb` is supplied, every returned candidate has exactly
   that inner colour.

6. **Fixed outer contour**
   Analogous test.

7. **Both fixed is rejected**
   No meaningless zero-dimensional optimisation.

8. **Luminance constraint**
   Returned candidates obey a supplied feasible luminance bound.

9. **Infeasible luminance constraint**
   Produces a clean unsuccessful result if no feasible candidate is found.
   Choose a deterministic fixture rather than an unrealistically tiny
   floating-point threshold if necessary.

10. **Geometry unchanged**
    Returned predictions use exactly the caller's geometry.

11. **Default geometry**
    Omitting geometry uses `WatercolourGeometry()`.

12. **No alternate objective**
    Tests should compare `chromatic_shift_uv`, never raw opponent norm.

Keep CI runtime reasonable by using much smaller `population_size` and
`max_generations` in tests than production defaults.

## 14. Benchmark before choosing production defaults

Add a small developer-only benchmark or record a manual benchmark in the PR
description:

- one `predict_watercolour()` call;
- a 3-variable optimisation;
- a 6-variable optimisation with proposed defaults.

Do not put wall-clock assertions in pytest.

If the 6-D defaults are unreasonably slow, first reduce/population generations
based on convergence evidence. Only then consider deeper changes to the forward
model evaluation.

## 15. CLI after the library core works

After the library optimiser and tests are complete, add an optional CLI command:

```
uv run colourshift-watercolour optimise \
    --field 1.0,1.0,1.0 \
    --seed 0
```

CLI output should include:

- best inner RGB
- best outer RGB
- geometry
- chromatic shift u'v'
- relative luminance shift
- predicted unclipped appearance RGB
- success/message/evaluation count
- alternatives

JSON output is preferable for reproducibility.

Do not add GUI integration in this PR.

## 16. Scientific interpretation of an optimum

An optimiser result means:

> Within the current WCE forward model, the calibrated geometry domain, the
> specified physical sRGB search bounds, and any explicit luminance constraint,
> this contour pair produces the largest chromatic u'v' displacement found by
> the configured numerical search.

It does **not** mean:

- a proven global psychophysical optimum for human observers;
- a calibrated Delta E magnitude;
- a spectral paint optimum;
- a guarantee that an out-of-gamut predicted appearance can be physically
  matched;
- validation outside the encoded WCE geometry domain.

Keep this wording, or equivalent limitations, in the optimiser documentation.

## 17. Implementation sequence for the next agent

Recommended order:

1. Add `colourshift/watercolour/optimisation.py` with configuration/result
   dataclasses and RGB vector mapping.
2. Implement a cached evaluator around `predict_watercolour()`.
3. Implement one-free-contour and two-free-contour differential-evolution
   search.
4. Add luminance constraint handling.
5. Collect/sort/deduplicate alternatives.
6. Export the public API.
7. Add the tests above.
8. Run:
   `uv run ruff check .`,
   `uv run ruff format --check .`,
   `uv run pytest`.
9. Benchmark representative 3-D and 6-D runs and adjust only optimiser defaults
   if needed.
10. Add the CLI command and concise README documentation.
11. Pre-PR review before merging.

## 18. Acceptance criteria

The implementation is ready for review when all of the following hold:

- there is still only one supported WCE forward model;
- optimisation calls `predict_watercolour()` rather than reproducing its
  internals;
- no raw opponent-space norm is used as the optimisation score;
- geometry is supplied/calibrated, not misleadingly rediscovered;
- all physical input RGB values remain in gamut;
- optional luminance constraints are explicit and enforced;
- fixed inner/outer modes work;
- runs are reproducible from a seed;
- alternatives are returned;
- CI is green;
- runtime is measured and documented;
- no GUI, paint database, or new perceptual-model work has leaked into the PR.

## 19. Later work

Once the colour optimiser is reliable, the most useful follow-on tasks are:

1. generate a physical control colour that perceptually matches the phantom
   WCE field for paired paintings;
2. map chosen contour/control colours to available paint colours by perceptual
   proximity;
3. add observer-specific psychophysical calibration of effect magnitude;
4. add genuinely multi-objective artistic optimisation (chromatic strength,
   luminance neutrality, execution complexity, pigment area);
5. explore spectral paint/illuminant optimisation.

Those should build on the optimiser rather than being folded into its first
implementation.
