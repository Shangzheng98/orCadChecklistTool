from pathlib import Path

import pytest

from orcad_checker.parser.design_parser import parse_design_dict, parse_design_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_design_file():
    design = parse_design_file(FIXTURES_DIR / "sample_design.json")
    assert design.design_name == "TestBoard"
    assert design.schema_version == "1.0.0"
    assert len(design.components) == 6
    assert len(design.nets) == 6


def test_parse_components(sample_design):
    u1 = sample_design.components[0]
    assert u1.refdes == "U1"
    assert u1.part_name == "LM1117"
    assert u1.footprint == "SOT-223"
    assert len(u1.pins) == 3
    assert u1.pins[0].net == "GND"


def test_parse_nets(sample_design):
    vcc = sample_design.nets[0]
    assert vcc.name == "VCC_3V3"
    assert vcc.is_power is True
    assert len(vcc.connections) == 4


def test_parse_hierarchy(sample_design):
    assert sample_design.hierarchy.top_level == "SCHEMATIC1"
    assert len(sample_design.hierarchy.pages) == 2


def test_parse_power_nets(sample_design):
    assert "GND" in sample_design.power_nets
    assert "VCC_3V3" in sample_design.power_nets


def test_parse_unconnected_pins(sample_design):
    assert len(sample_design.unconnected_pins) == 1
    assert sample_design.unconnected_pins[0].refdes == "U2"


def test_parse_invalid_data():
    with pytest.raises(ValueError):
        parse_design_dict({"components": "not a list"})


def test_parse_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_design_file("/nonexistent/file.json")
