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

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the web server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port")

    # ── Client commands ──────────────────────────────────────

    # scripts subcommands
    scripts_parser = subparsers.add_parser("scripts", help="Local script management")
    scripts_sub = scripts_parser.add_subparsers(dest="scripts_cmd")

    scripts_sub.add_parser("list", help="List locally installed scripts")

    install_p = scripts_sub.add_parser("install", help="Install script from server")
    install_p.add_argument("script_id", help="Script ID to install")

    remove_p = scripts_sub.add_parser("remove", help="Remove a local script")
    remove_p.add_argument("script_id", help="Script ID to remove")

    deploy_p = scripts_sub.add_parser("deploy", help="Deploy script to OrCAD auto-load")
    deploy_p.add_argument("script_id", help="Script ID to deploy")

    push_p = scripts_sub.add_parser("push", help="Push local TCL file to server")
    push_p.add_argument("tcl_file", help="Path to TCL file")
    push_p.add_argument("--name", required=True, help="Script name")
    push_p.add_argument("--desc", default="", help="Description")
    push_p.add_argument("--category", default="custom", help="Category")
    push_p.add_argument("--author", default="", help="Author")

    # ota subcommands
    ota_parser = subparsers.add_parser("ota", help="OTA update management")
    ota_sub = ota_parser.add_subparsers(dest="ota_cmd")

    ota_sub.add_parser("check", help="Check for updates")
    ota_sub.add_parser("update", help="Pull all available updates")
    ota_sub.add_parser("register", help="Register this client with server")

    args = parser.parse_args()

    if args.command == "list":
        _cmd_list()
    elif args.command == "run":
        selected = args.checkers.split(",") if args.checkers else None
        _cmd_run(args.design_file, args.rules, selected, args.json)
    elif args.command == "serve":
        _cmd_serve(args.host, args.port)
    elif args.command == "scripts":
        _cmd_scripts(args)
    elif args.command == "ota":
        _cmd_ota(args)
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

    if report.summary.errors > 0:
        sys.exit(1)


def _cmd_serve(host: str, port: int):
    import uvicorn
    print(f"Starting server on {host}:{port}")
    uvicorn.run("orcad_checker.web.app:app", host=host, port=port, reload=True)


def _cmd_scripts(args):
    from orcad_checker.client import script_manager

    if args.scripts_cmd == "list":
        scripts = script_manager.list_local_scripts()
        if not scripts:
            print("No local scripts installed.")
            return
        for s in scripts:
            print(f"  [{s.get('id', '?')}] {s.get('name', 'unnamed')} v{s.get('version', '?')}")
            if s.get("description"):
                print(f"          {s['description']}")

    elif args.scripts_cmd == "install":
        from orcad_checker.client.ota import pull_script
        result = pull_script(args.script_id)
        print(f"Installed: {result}")

    elif args.scripts_cmd == "remove":
        ok = script_manager.remove_script(args.script_id)
        print("Removed." if ok else "Not found.")

    elif args.scripts_cmd == "deploy":
        msg = script_manager.deploy_to_orcad(args.script_id)
        print(msg)

    elif args.scripts_cmd == "push":
        from pathlib import Path
        from orcad_checker.client.ota import push_script
        tcl_path = Path(args.tcl_file)
        if not tcl_path.exists():
            print(f"File not found: {tcl_path}", file=sys.stderr)
            sys.exit(1)
        code = tcl_path.read_text(encoding="utf-8")
        result = push_script(
            script_id="", code=code, name=args.name,
            description=args.desc, author=args.author, category=args.category,
        )
        print(f"Pushed: {result.get('meta', {}).get('id', 'unknown')}")

    else:
        print("Usage: orcad-check scripts {list|install|remove|deploy|push}")


def _cmd_ota(args):
    from orcad_checker.client import ota

    if args.ota_cmd == "check":
        result = ota.check_for_updates()
        updates = result.get("updates", [])
        if not updates:
            print("No updates available.")
        else:
            print(f"{len(updates)} update(s) available:")
            for u in updates:
                print(f"  [{u.get('id')}] {u.get('name')} v{u.get('version')}")

    elif args.ota_cmd == "update":
        results = ota.pull_all_updates()
        for r in results:
            print(f"  {r.get('script_id')}: {r.get('status')}")
        if not results:
            print("Already up to date.")

    elif args.ota_cmd == "register":
        result = ota.register_with_server()
        print(f"Registered: client_id={result.get('client_id')}")

    else:
        print("Usage: orcad-check ota {check|update|register}")


if __name__ == "__main__":
    main()
