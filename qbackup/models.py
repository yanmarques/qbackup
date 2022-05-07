"""
Models used for configuration
"""

from dataclasses import dataclass, field
from typing import Hashable, Set

from .api import AbstractModel


@dataclass
class Group(AbstractModel):
    name: str
    period: str
    qubes: Set[str] = field(default_factory=set)

    def __post_init__(self):
        self.qubes = set(self.qubes)

    def keyid(self) -> Hashable:
        return self.name
