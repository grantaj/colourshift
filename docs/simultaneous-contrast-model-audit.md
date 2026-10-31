# Simultaneous-contrast model audit

## Context

ColourShift is intended to automate an Albers-style colour interaction problem:

> For a fixed target colour and a chosen starting surround, which alternative surround is predicted to cause the greatest perceptual shift in the target?

The current implementation gives useful-looking surround pairs, but repeated extreme results involving black raised a concern that part of the ranking may be a modelling artefact rather than genuine simultaneous contrast.

This note records the findings from the audit around issue #2 and a small exploratory comparison with a model designed specifically for simultaneous colour contrast.

## 1. The current CIECAM02 call contains a real parameter-order bug

The current core calls `XYZ_to_CIECAM02()` positionally:

```python
XYZ_to_CIECAM02(
    stimulus_XYZ,
    surround_XYZ,
    config.background_luminance,
    config.adapting_luminance,
    surround=_viewing_condition(config),
)
```

The `colour-science` API expects the arguments in the order:

```text
XYZ, XYZ_w, L_A, Y_b, ...
```

The configuration and paper state the intended defaults as:

- adapting-field luminance: `L_A = 64`
- background luminous factor: `Y_b = 20`

The current positional call therefore supplies these two values in the opposite order.

This should be corrected independently of any larger model change, and future calls should use explicit keywords.

There is also a terminology issue: `Y_b` is a relative background luminous factor, not an absolute background luminance. A clearer configuration name would be `background_luminous_factor`.

## 2. The more important issue is the centre-surround model itself

The current implementation passes

```text
XYZ_w = XYZ_surround
```

to CIECAM02.

That is not the standard meaning of `XYZ_w`. In CIECAM02/CAM16 it is the reference white. The model's normal `surround` parameter only selects broad viewing conditions such as Average, Dim or Dark; it does not accept an arbitrary coloured surround in the Albers sense.

The present code is therefore best understood as an **adaptation-based proxy** for simultaneous contrast:

> treat the local coloured surround as though it were the adapting/reference white, then measure how the target appearance changes.

This proxy appears to be useful in practice, but it is not a canonical CIECAM02 model of simultaneous contrast.

That distinction is important before the Python implementation is frozen as the numerical reference for a browser port.

## 3. Why the repeated black result is suspicious

Using the surround as the reference white becomes pathological for very dark surrounds. As the surround approaches black, the supposed reference-white tristimulus values also approach zero, even though the model expects a meaningful adapting white.

This gives a plausible explanation for the observation that searches frequently return black or near-black as an extreme surround.

Black can still produce a genuine and strong **lightness-contrast** effect, so it should not simply be excluded. However, the magnitude produced by the current reference-white substitution should not be trusted as evidence that black is perceptually optimal.

## 4. Models that explicitly address simultaneous contrast

### Zhu and Luo (2019): refined CAM16 / CAM16cc-style model

Zhu and Luo developed fitted simultaneous-contrast corrections on top of CAM16 using psychophysical measurements.

Their model explicitly treats a target and background as separate colours and adds corrections for:

- lightness contrast;
- hue contrast.

The published fitted functions are:

```text
ΔJ'_predict =
    9.17 / (0.36 + exp(-0.05 ΔJ'_(b-r))) - 5.80
```

and

```text
ΔH'_predict =
    0.0833 ΔH'_(b-r) exp(-0.001 (ΔH'_(b-r))²)
```

The correction is applied after ordinary CAM16. The 2019 model did not introduce an independent chroma-contrast term.

This makes it a useful, reproducible benchmark for ColourShift, but probably not the final model.

### Pei, Farnand and Fairchild (2025): extended CIECAM16

A more recent model was published specifically to extend CIECAM16 for simultaneous contrast.

Unlike the 2019 model, it experimentally investigates and models all three relevant appearance dimensions:

- lightness;
- hue;
- chroma.

The paper reports substantially improved agreement with observed simultaneous-contrast data compared with ordinary colour appearance models.

This is the most promising candidate found so far for the next ColourShift appearance engine.

## 5. Preliminary comparison on an existing ColourShift example

The existing paper example was used as a simple test case:

- target: `#950000`
- starting surround: `#964301`
- search grid: the existing `12^3` sRGB grid.

### Current ColourShift method

The existing calculation gives the same leading results recorded in the paper:

| Rank | Surround | Current-model shift |
| ---: | --- | ---: |
| 1 | `#175ca2` | 100.68 |
| 2 | `#8b00a2` | 97.19 |
| 3 | `#5c4545` | 91.16 |

These are visually plausible chromatic alternatives, which is one reason the current proxy remains worth retaining as a baseline.

### Exploratory 2019 simultaneous-contrast model

A preliminary calculation using the 2019 CAM16 simultaneous-contrast corrections gave a very different ranking when **total appearance shift** was maximised:

| Rank | Surround | Predicted total shift |
| ---: | --- | ---: |
| 1 | `#ffffff` | 38.65 |
| 2 | `#ffffe7` | 36.71 |
| 3 | `#ffffd0` | 36.23 |

The white winner is dominated by predicted lightness contrast. For `#ffffff`, the exploratory decomposition was approximately:

```text
total shift      38.65
lightness part   37.22
chromatic part   10.43
```

When the same exploratory model was ranked by **chromatic displacement only**, the leading result moved toward magenta:

| Rank | Surround | Chromatic shift |
| ---: | --- | ---: |
| 1 | `#e72e8b` | 10.90 |
| 2 | `#730045` | 10.90 |
| 3 | `#ffa2d0` | 10.90 |

Under this model black was not the total-shift optimum for the example.

These numbers are exploratory, not golden reference values. The CAM16 simultaneous-contrast implementation should be checked into the repository and independently reproduced before these values are used as regression fixtures. The useful result here is the **qualitative divergence between models**.

## 6. Recommendation

Do not treat issue #2 as only a two-line CIECAM02 parameter fix.

The recommended path is:

1. **Fix the unambiguous `L_A` / `Y_b` reversal** and use keyword arguments.
2. **Preserve the current algorithm as a named legacy/baseline model**, because it has already produced useful studio candidates.
3. **Implement the 2019 refined CAM16 simultaneous-contrast model** as a reproducible comparison model.
4. **Implement the 2025 Pei-Farnand-Fairchild extension** if its complete equations and parameters can be reproduced reliably; this should be the preferred research target because it includes chroma as well as hue and lightness.
5. Compare the models over a small bank of target / starting-surround cases for which visual judgement is available.
6. Do not create the language-neutral golden fixtures from issue #7 until the centre-surround model decision is settled.

## 7. Search objective should expose total and chromatic shift separately

The experiment also exposes an important product-level distinction.

For a predicted target appearance in CAM16-UCS-like coordinates, two useful objectives are:

```text
total shift =
    sqrt(ΔJ'² + Δa'² + Δb'²)
```

and

```text
chromatic shift =
    sqrt(Δa'² + Δb'²)
```

The first answers:

> Which surround makes the target look most different overall?

The second answers:

> Which surround changes what colour the target appears to be most strongly, apart from lightness?

For studio use both are meaningful. A white or black surround may legitimately dominate total shift because of lightness contrast, while a coloured surround may be much more interesting when the objective is chromatic induction.

The implementation should therefore report the decomposition rather than silently mixing the two effects.

## 8. Scope and caveats

The published simultaneous-contrast models were developed primarily using controlled display experiments. ColourShift is ultimately intended to inform physical painting, so absolute predicted effect sizes should not be interpreted as gallery psychophysics.

The practical objective is more modest:

> obtain a useful ranking of candidate surrounds that reliably finds strong perceptual interactions for subsequent studio testing.

That can be evaluated empirically against painted or calibrated-display examples without requiring the numerical model to be a complete theory of vision.

## References

- ColourShift issue #2: https://github.com/grantaj/colourshift/issues/2
- Zhu, Y. and Luo, M. R. (2019), *Modelling of Simultaneous Contrast Effects Using Memory Colour Matching Method to Revise the CIECAM16 Colour Appearance Model*, CIE x046:2019, OP06. https://doi.org/10.25039/x46.2019.OP06
- Pei, E., Farnand, S. and Fairchild, M. D. (2025), *Extending CIECAM16 to Account for Simultaneous Contrast*, Color Research & Application 50(5), 406-423. https://doi.org/10.1002/col.22980
