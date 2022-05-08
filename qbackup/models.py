"""
Models used for configuration
"""

from dataclasses import dataclass, field
from typing import Hashable

from .api import AbstractModel, UUIDModelIdentifier


@dataclass
class Group(AbstractModel):
    name: str
    period: str

    def keyid(self) -> Hashable:
        return self.name


@dataclass
class Period(AbstractModel):
    name: str

    def keyid(self) -> Hashable:
        return self.name


@dataclass
class Qube(UUIDModelIdentifier, AbstractModel):
    name: str = field(default=None)
    group_name: str = field(default=None)
