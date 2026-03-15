from __future__ import annotations

import uuid
from datetime import datetime, timezone

from orcad_checker.engine.registry import discover_checkers, list_checkers
from orcad_checker.engine.rule_loader import load_rules
from orcad_checker.models.design import Design
from orcad_checker.models.results import Report, ReportSummary, Severity


def run_checks(
    design: Design,
    rules_path: str | None = None,
    selected_checkers: list[str] | None = None,
) -> Report:
    """Run selected checkers against a design and return a Report.

    Args:
        design: Parsed design data.
        rules_path: Optional path to YAML rules config for overrides.
        selected_checkers: List of checker IDs to run. None = run all.
    """
    discover_checkers()
    rule_overrides = load_rules(rules_path)
    all_checkers = list_checkers()

    # Determine which checkers to run
    if selected_checkers:
        checker_ids = [cid for cid in selected_checkers if cid in all_checkers]
    else:
        checker_ids = list(all_checkers.keys())

    # Filter out disabled checkers from YAML config
    checker_ids = [
        cid for cid in checker_ids
        if rule_overrides.get(cid, {}).get("enabled", True)
    ]

    results = []
    for cid in checker_ids:
        checker_cls = all_checkers[cid]
        config = rule_overrides.get(cid, {}).get("params", {})
        checker = checker_cls(config=config)

        # Apply severity override from YAML
        severity_override = rule_overrides.get(cid, {}).get("severity")

        check_results = checker.check(design)
        for cr in check_results:
            if severity_override:
                cr.severity = Severity(severity_override.upper())
        results.extend(check_results)

    # Build summary
    summary = ReportSummary(
        total_checks=len(checker_ids),
        passed=sum(1 for cid in checker_ids if not any(r.rule_id == cid for r in results)),
        errors=sum(1 for r in results if r.severity == Severity.ERROR),
        warnings=sum(1 for r in results if r.severity == Severity.WARNING),
        infos=sum(1 for r in results if r.severity == Severity.INFO),
    )

    return Report(
        result_id=str(uuid.uuid4()),
        design_name=design.design_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        results=results,
    )
