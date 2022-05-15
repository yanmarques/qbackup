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
    password: str
    dest_qube: str

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


@dataclass
class Password(AbstractModel):
    name: str
    content: str
    is_default: bool = field(default=False)

    def keyid(self) -> Hashable:
        return self.name

@dataclass
class DestQube(AbstractModel):
    name: str
    qube: str
    executable: str

    def keyid(self) -> Hashable:
        return self.name
