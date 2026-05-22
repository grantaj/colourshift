import warnings


def suppress_colour_optional_dependency_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r'.*"(SciPy|Matplotlib)" related API features are not available.*',
    )
