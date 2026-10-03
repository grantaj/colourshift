from colourshift.watercolour.published import (
    DEVINCK_2005_BACKGROUND_LUMINANCE,
    DEVINCK_2005_CHROMATICITIES,
    DEVINCK_2005_CONDITIONS,
    DEVINCK_2005_EFFECTS,
    DEVINCK_2005_INNER_LUMINANCE,
    DEVINCK_2005_OUTER_LUMINANCE,
)


def test_devinck_2005_table_contains_six_chromatic_colours_and_white():
    assert set(DEVINCK_2005_CHROMATICITIES) == {
        "white",
        "blue",
        "green",
        "orange",
        "purple",
        "red",
        "yellow",
    }


def test_devinck_2005_experiment_2_has_six_reversed_pair_conditions():
    assert len(DEVINCK_2005_CONDITIONS) == 6
    inducing_colours = {inner for inner, _ in DEVINCK_2005_CONDITIONS}
    assert inducing_colours == set(DEVINCK_2005_EFFECTS)


def test_devinck_2005_published_reference_values():
    assert DEVINCK_2005_CHROMATICITIES["orange"].u_prime == 0.2490
    assert DEVINCK_2005_CHROMATICITIES["purple"].v_prime == 0.3745
    assert DEVINCK_2005_EFFECTS["yellow"].shift_ratio == 0.0181
    assert DEVINCK_2005_EFFECTS["red"].angle_difference_deg == 7.61
    assert DEVINCK_2005_BACKGROUND_LUMINANCE == 80.0
    assert DEVINCK_2005_INNER_LUMINANCE == 55.0
    assert DEVINCK_2005_OUTER_LUMINANCE == 20.0
