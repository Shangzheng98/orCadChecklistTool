"""CLI entry point for orcad-check command."""
from __future__ import annotations

import argparse
import json
import sys

from orcad_checker.engine.registry import discover_checkers, list_checkers
from orcad_checker.engine.runner import run_checks
from orcad_checker.parser.design_parser import parse_design_file


def main():
    parser = argparse.ArgumentParser(
        prog="orcad-check",
        description="OrCAD Capture schematic checklist tool",
    )
    subparsers = parser.add_subparsers(dest="command")

    # run command
    run_parser = subparsers.add_parser("run", help="Run checklist against a design export JSON")
    run_parser.add_argument("design_file", help="Path to the design export JSON file")
    run_parser.add_argument("--rules", help="Path to YAML rules config file")
    run_parser.add_argument(
        "--checkers",
        help="Comma-separated list of checker IDs to run (default: all)",
    )
    run_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # list command
    subparsers.add_parser("list", help="List all available checkers")

    args = parser.parse_args()

    if args.command == "list":
        _cmd_list()
    elif args.command == "run":
        selected = args.checkers.split(",") if args.checkers else None
        _cmd_run(args.design_file, args.rules, selected, args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_list():
    discover_checkers()
    checkers = list_checkers()
    print(f"Available checkers ({len(checkers)}):\n")
    for rule_id, cls in sorted(checkers.items()):
        severity = getattr(cls, "default_severity", "WARNING")
        print(f"  [{severity:7s}] {rule_id}")
        if cls.description:
            print(f"           {cls.description}")
        print()


def _cmd_run(design_file: str, rules_path: str | None, selected: list[str] | None, as_json: bool):
    try:
        design = parse_design_file(design_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    report = run_checks(design, rules_path=rules_path, selected_checkers=selected)

    if as_json:
        print(report.model_dump_json(indent=2))
        return

    # Pretty print
    print(f"Design: {report.design_name}")
    print(f"Checks: {report.summary.total_checks} | "
          f"Passed: {report.summary.passed} | "
          f"Errors: {report.summary.errors} | "
          f"Warnings: {report.summary.warnings} | "
          f"Info: {report.summary.infos}")
    print("-" * 60)

    for result in report.results:
        icon = "PASS" if result.status.value == "PASS" else "FAIL"
        print(f"[{icon}] [{result.severity.value:7s}] {result.rule_name or result.rule_id}")
        for finding in result.findings:
            print(f"       - {finding.message}")

    # Exit with error code if any errors found
    if report.summary.errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
