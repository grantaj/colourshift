# ColourShift numerical contract

The supported model is `zhu-luo-cam16cc-2019-v1`, labelled **Zhu–Luo CAM16
simultaneous contrast (2019)**. It implements the lightness and hue functions
published in Zhu and Luo, *Proposed Modification to the CAM16 Colour Appearance
Model to Predict the Simultaneous Colour Contrast Effect*, Color and Imaging
Conference 27, paper 34, DOI `10.2352/ISSN.2169-2629.2019.27.34`. This is the
final 2019 CAM16cc fit, not the earlier fit reported at the CIE session.

The model was fitted to controlled self-luminous-display experiments. Its
rankings are useful hypotheses for studio evaluation, not observer-independent
predictions for physical paint.

## CAM16 mapping

Target and background sRGB colours are converted independently to XYZ and then
CAM16-UCS under the same viewing condition:

- D65 reference white, normalized to `Y = 100`;
- configurable CAM16 adapting luminance `L_A` (default 23 cd/m², matching the
  adapting field reported by Zhu and Luo);
- configurable background luminous factor `Y_b` (default 20);
- configurable CAM16 surround condition (default Average).

The coloured background is never used as CAM16's adapting white.

For target coordinates `(J′t, a′t, b′t)` and background coordinates
`(J′b, a′b, b′b)`, the lightness correction is:

```text
ΔJ′cc = 16.0067 / (0.0837 + exp(-0.0240 ΔJ′b-t)) - 13.4455
ΔJ′b-t = J′b - J′t
```

The signed hue-metric difference follows the paper's Equation 1:

```text
ΔH′b-t = 2 sqrt(C′b C′t) sin((h′b - h′t) / 2)
```

and its fitted hue correction is:

```text
ΔH′cc = 0.4408 ΔH′b-t exp(-0.001 (ΔH′b-t)²)
```

`ΔH′cc` is converted to a hue-angle rotation at the target's CAM16-UCS
chroma. The target's chroma radius is unchanged because the 2019 model did not
fit an independent chroma-contrast term. The corrected target coordinate is
therefore `(J′t + ΔJ′cc, a′corrected, b′corrected)`.

## Search operations

- `find_maximal_surround_shift` compares a fixed target under candidate
  surrounds with that target under an initial surround.
- `find_strongest_surrounds` compares a fixed target under candidate surrounds
  with that target surrounded by its own colour.
- `find_sensitive_bases` compares each candidate target under a fixed surround
  with that target surrounded by its own colour.

Every operation returns an immutable `SearchResult` containing the model,
mode, objective, complete configuration, computational input colours, and
ranked candidates.

## Objectives and selection

The `total` objective is Euclidean CAM16-UCS distance. The `chromatic`
objective is distance in the CAM16-UCS a′b′ plane, excluding J′. Candidate
ranking and minimum-separation filtering use the selected objective. Equal
scores are ordered lexicographically by RGB, making ties deterministic.

The RGB search grid includes both endpoints in each channel. Invalid or
non-finite CAM16 results are omitted. The greedy separation filter walks the
ranked list and keeps a candidate only when it is at least `min_delta` from
every already-selected candidate.

## Portability

JSON exports use schema `colourshift-search-result-v1`. The reference fixture
at `tests/fixtures/colourshift_reference.json` fixes conversion, ordinary
CAM16-UCS, corrected appearance, and all three modes under both objectives on
a small grid. Another implementation should reproduce that fixture within the
tolerances in `tests/test_reference_fixture.py` before it is considered
compatible.
