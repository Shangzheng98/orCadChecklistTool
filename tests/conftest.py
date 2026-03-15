from pathlib import Path

import pytest

from orcad_checker.parser.design_parser import parse_design_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_design():
    return parse_design_file(FIXTURES_DIR / "sample_design.json")
