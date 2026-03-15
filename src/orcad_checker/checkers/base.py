from __future__ import annotations

from abc import ABC, abstractmethod

from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult


class BaseChecker(ABC):
    """Abstract base class for all checklist checkers.

    To create a new checker, subclass this and use the @register_checker decorator.
    """

    name: str = ""
    description: str = ""
    default_severity: str = "WARNING"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def check(self, design: Design) -> list[CheckResult]:
        ...
