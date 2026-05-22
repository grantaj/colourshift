import tomllib

from colourshift.ui.tk_app import main


def test_console_script_points_to_tk_main():
    with open("pyproject.toml", "rb") as pyproject:
        metadata = tomllib.load(pyproject)

    assert metadata["project"]["scripts"]["colourshift"] == "colourshift.ui.tk_app:main"
    assert callable(main)
