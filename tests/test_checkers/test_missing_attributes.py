from orcad_checker.models.results import Status


def test_finds_missing_attributes(sample_design):
    from orcad_checker.checkers.missing_attributes import MissingAttributesChecker

    checker = MissingAttributesChecker()
    results = checker.check(sample_design)
    assert results[0].status == Status.FAIL
    # U2 missing footprint and value, second R1 missing part_number, C2 missing part_number
    refdes_with_issues = {f.refdes for f in results[0].findings}
    assert "U2" in refdes_with_issues


def test_all_present():
    from orcad_checker.checkers.missing_attributes import MissingAttributesChecker
    from orcad_checker.models.design import Component, Design

    design = Design(
        design_name="clean",
        components=[
            Component(refdes="U1", value="3.3V", footprint="SOT-223", part_number="LM1117"),
        ],
    )
    checker = MissingAttributesChecker()
    results = checker.check(design)
    assert results[0].status == Status.PASS
