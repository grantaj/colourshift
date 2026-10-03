"""Published Watercolour Effect datasets used as validation targets.

The first dataset encoded here is Devinck et al. (Vision Research, 2005),
Experiment 2.  Table 1 reports the CIE 1976 u'v' chromaticities; Appendix A
reports mean effect-vector magnitude and angular deviation for each inducing
colour.  The experiment used an 80 cd/m^2 white background, with the inner
(brighter) contour at 55 cd/m^2 and the outer contour at 20 cd/m^2.

Keeping these values as data rather than baking them into the model makes the
validation target explicit and prevents accidental tuning of the implementation
to undocumented constants.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChromaticityUV:
    u_prime: float
    v_prime: float


@dataclass(frozen=True)
class PublishedEffect:
    """Mean psychophysical WCE effect relative to the inducing-colour vector."""

    shift_ratio: float
    angle_difference_deg: float


DEVINCK_2005_BACKGROUND_LUMINANCE = 80.0
DEVINCK_2005_INNER_LUMINANCE = 55.0
DEVINCK_2005_OUTER_LUMINANCE = 20.0

# Table 1, Devinck et al. (2005).
DEVINCK_2005_CHROMATICITIES: dict[str, ChromaticityUV] = {
    "white": ChromaticityUV(0.1887, 0.4670),
    "blue": ChromaticityUV(0.1978, 0.4058),
    "green": ChromaticityUV(0.1423, 0.4724),
    "orange": ChromaticityUV(0.2490, 0.5301),
    "purple": ChromaticityUV(0.2109, 0.3745),
    "red": ChromaticityUV(0.2341, 0.4616),
    "yellow": ChromaticityUV(0.1765, 0.5489),
}

# Appendix A, Experiment 2 mean values.
DEVINCK_2005_EFFECTS: dict[str, PublishedEffect] = {
    "orange": PublishedEffect(shift_ratio=0.0321, angle_difference_deg=8.58),
    "purple": PublishedEffect(shift_ratio=0.0379, angle_difference_deg=5.92),
    "blue": PublishedEffect(shift_ratio=0.0339, angle_difference_deg=4.66),
    "yellow": PublishedEffect(shift_ratio=0.0181, angle_difference_deg=9.11),
    "green": PublishedEffect(shift_ratio=0.0321, angle_difference_deg=3.18),
    "red": PublishedEffect(shift_ratio=0.0438, angle_difference_deg=7.61),
}

# Conditions shown in the model-comparison figure: each colour serves once as
# the inner inducing contour and once as the outer contour.
DEVINCK_2005_CONDITIONS: tuple[tuple[str, str], ...] = (
    ("orange", "purple"),
    ("purple", "orange"),
    ("red", "green"),
    ("green", "red"),
    ("blue", "yellow"),
    ("yellow", "blue"),
)


# Devinck et al. (2014), Spatial selectivity of the watercolor effect.
# The paper reports *total double-contour widths*: with equal ribbons, each
# individual ribbon is half the stated width.
DEVINCK_2014_BACKGROUND_XY = (0.29, 0.32)
DEVINCK_2014_BACKGROUND_LUMINANCE = 134.0
DEVINCK_2014_OUTER_PURPLE_XY = (0.31, 0.11)
DEVINCK_2014_OUTER_PURPLE_LUMINANCE = 24.1
DEVINCK_2014_INNER_ORANGE_XY = (0.40, 0.43)
DEVINCK_2014_INNER_ORANGE_LUMINANCE_RANGE = (70.2, 109.6)
DEVINCK_2014_TOTAL_WIDTHS_ARCMIN = (6.0, 11.0, 15.0, 19.0, 24.0)
DEVINCK_2014_OPTIMAL_TOTAL_WIDTH_ARCMIN = 15.0
DEVINCK_2014_INNER_OUTER_RATIOS = (0.5, 1.0, 2.0)
DEVINCK_2014_RADIUS_DEG = 1.6
DEVINCK_2014_MODULATION_DEG = 0.11
DEVINCK_2014_FREQUENCY_CPR = 10
DEVINCK_2014_CRITERION_LUMINANCE_ELEVATION = 0.72

# Devinck & Spillmann (2009), radial spacing experiment.
DEVINCK_2009_BACKGROUND_XY = (0.33, 0.36)
DEVINCK_2009_BACKGROUND_LUMINANCE = 89.0
DEVINCK_2009_INNER_ORANGE_XY = (0.434, 0.391)
DEVINCK_2009_INNER_ORANGE_LUMINANCE = 31.4
DEVINCK_2009_OUTER_PURPLE_XY = (0.212, 0.134)
DEVINCK_2009_OUTER_PURPLE_LUMINANCE = 14.2
DEVINCK_2009_CONTOUR_WIDTH_ARCMIN = 0.8
DEVINCK_2009_RADIAL_GAPS_ARCMIN = (0.0, 1.24, 2.48, 6.22, 12.43)


# Gerardin et al. (2014), contour frequency/amplitude conjoint measurement.
# Exact contour luminances for a fixed geometric sweep are not tabulated in
# cd/m^2 because luminance was manipulated in DKL elevation. Geometry tests
# therefore use these published chromaticities plus a fixed representative
# luminance ordering, documented in the Gate 2B report.
GERARDIN_2014_BACKGROUND_XY = (0.29, 0.30)
GERARDIN_2014_BACKGROUND_LUMINANCE = 128.0
GERARDIN_2014_OUTER_PURPLE_XY = (0.32, 0.19)
GERARDIN_2014_INNER_ORANGE_XY = (0.48, 0.34)
GERARDIN_2014_TOTAL_WIDTH_ARCMIN = 16.0
GERARDIN_2014_DIAMETER_DEG = 4.0
GERARDIN_2014_FREQUENCIES_CPR = (4.0, 8.0, 12.0, 16.0, 20.0)
GERARDIN_2014_AMPLITUDES_DEG = (0.04, 0.08, 0.12, 0.16, 0.20)
GERARDIN_2014_FREQUENCY_PLATEAU_CPR = 12.0
GERARDIN_2014_AMPLITUDE_PLATEAU_DEG = 0.08

# Devinck et al. (2014), size-by-width interaction (Figure 7).
DEVINCK_2014_SIZE_DIAMETERS_DEG = (2.3, 3.2, 4.5)
DEVINCK_2014_SIZE_WIDTHS_ARCMIN = (6.0, 15.0, 24.0)
