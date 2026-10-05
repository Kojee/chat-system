import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--eval",
        action="store_true",
        default=False,
        help="run eval tests (paid OpenAI calls; cached after first run)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--eval"):
        return
    skip = pytest.mark.skip(reason="needs --eval to run")
    for item in items:
        if "eval" in item.keywords:
            item.add_marker(skip)
