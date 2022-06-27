"""
Models used for configuration
"""

from dataclasses import dataclass, field
from typing import Hashable
from uuid import uuid4

from .api import AbstractModel


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


def genuuid() -> str:
    return str(uuid4())


@dataclass
class Qube(AbstractModel):
    name: str
    group_name: str
    id: str = field(default_factory=genuuid)

    def keyid(self) -> Hashable:
        return self.id


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
