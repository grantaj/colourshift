import json
import subprocess
import sys
from pathlib import Path


def test_watercolour_baseline_script_smoke(tmp_path):
    script = Path("scripts/watercolour_optimisation_baseline.py")
    output = tmp_path / "baseline"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--hue-steps",
            "4",
            "--contrast-steps",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads((output / "baseline_report.json").read_text())
    assert set(report) == {
        "purpose",
        "field_rgb",
        "published_conditions",
        "contrast_sweep",
        "fixed_luminance_fixed_chroma_hue_map",
        "double_contour_controls",
    }
    assert len(report["published_conditions"]["rows"]) == 6
    assert len(report["contrast_sweep"]["rows"]) == 6
    assert len(report["fixed_luminance_fixed_chroma_hue_map"]["rows"]) == 16
    assert len(report["double_contour_controls"]["rows"]) == 14

    for filename in (
        "published_conditions.csv",
        "contrast_sweep.csv",
        "hue_map.csv",
        "controls.csv",
        "contrast_sweep.svg",
        "hue_map.svg",
    ):
        assert (output / filename).is_file()
