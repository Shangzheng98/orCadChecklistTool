from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orcad_checker.checkers.base import BaseChecker

_CHECKER_REGISTRY: dict[str, type[BaseChecker]] = {}


def register_checker(rule_id: str):
    """Decorator to register a checker class.

    Usage:
        @register_checker("duplicate_refdes")
        class DuplicateRefDesChecker(BaseChecker):
            ...
    """
    def decorator(cls):
        _CHECKER_REGISTRY[rule_id] = cls
        cls._rule_id = rule_id
        return cls
    return decorator


def get_checker(rule_id: str) -> type[BaseChecker]:
    return _CHECKER_REGISTRY[rule_id]


def list_checkers() -> dict[str, type[BaseChecker]]:
    return dict(_CHECKER_REGISTRY)


def discover_checkers():
    """Auto-discover all checker plugins in the checkers package."""
    import orcad_checker.checkers as checkers_pkg

    package_path = Path(checkers_pkg.__file__).parent

    for module_info in pkgutil.iter_modules([str(package_path)]):
        if module_info.name == "base":
            continue
        importlib.import_module(f"orcad_checker.checkers.{module_info.name}")
