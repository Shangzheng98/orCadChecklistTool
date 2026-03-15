from orcad_checker.models.results import Status


def test_finds_duplicate_refdes(sample_design):
    from orcad_checker.checkers.duplicate_refdes import DuplicateRefDesChecker

    checker = DuplicateRefDesChecker()
    results = checker.check(sample_design)
    assert len(results) == 1
    assert results[0].status == Status.FAIL
    assert any("R1" in f.message for f in results[0].findings)


def test_no_duplicates():
    from orcad_checker.checkers.duplicate_refdes import DuplicateRefDesChecker
    from orcad_checker.models.design import Component, Design

    design = Design(
        design_name="clean",
        components=[
            Component(refdes="U1"),
            Component(refdes="U2"),
            Component(refdes="R1"),
        ],
    )
    checker = DuplicateRefDesChecker()
    results = checker.check(design)
    assert results[0].status == Status.PASS
