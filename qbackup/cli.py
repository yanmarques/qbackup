"""
CLI interface functions
"""

import argparse
import os
from pathlib import Path

from .models import Group
from .database import SqliteDataManager
from .connectors import SqliteConnector


class QbackupManager:
    def initialize(self, connector, args) -> None:
        self.connector = connector
        self.args = args
        self.data_manager = SqliteDataManager(connector, Group)
        
    def list_groups(self) -> None:
        print(self.data_manager.list())

    def add_group(self) -> None:
        model = self.data_manager.get(self.args.group)
        if model is None:
            model = Group(name=self.args.group, period=self.args.period)
        self.data_manager.upsert(model)
        self.data_manager.save()

    def delete_qubes_from_group(self) -> None:
        model = self.data_manager.get(self.args.group)
        if model is None:
            raise ValueError(f"Unknown group: {self.args.group}")

        for qube in self.args.qubes[0]:
            model.qubes.remove(qube)

        self.data_manager.upsert(model)
        self.data_manager.save()

    def add_qubes_to_group(self) -> None:
        model = self.data_manager.get(self.args.group)
        if model is None:
            raise ValueError(f"Unknown group: {self.args.group}")

        for qube in self.args.qubes[0]:
            model.qubes.add(qube)

        self.data_manager.upsert(model)
        self.data_manager.save()

    def delete_group(self) -> None:
        model = self.data_manager.get(self.args.group)
        if model is None:
            raise ValueError(f"Unknown group: {self.args.group}")
        model.qubes.remove(self.args.qube)
        self.data_manager.upsert(model)
        self.data_manager.save()

    def run_backup(self) -> None:
        groups_to_run = []
        for group in self.data_manager.list():
            if group.period == self.args.period:
                groups_to_run.append(group)

        print(groups_to_run)


def main():
    manager = QbackupManager()
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    # vm_parser = subparsers.add_parser("install")
    # vm_parser.set_defaults(function=install_cron)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("period", type=str)

    qube_parser = subparsers.add_parser("qube")
    qube_subparsers = qube_parser.add_subparsers()

    del_qube_parser = qube_subparsers.add_parser("del")
    del_qube_parser.add_argument("group", type=str, help="Group name")
    del_qube_parser.add_argument("qubes", action="append", nargs="+")
    del_qube_parser.set_defaults(function=manager.delete_qubes_from_group)

    add_qube_parser = qube_subparsers.add_parser("add")
    add_qube_parser.add_argument("group", type=str, help="Group name")
    add_qube_parser.add_argument("qubes", action="append", nargs="+")
    add_qube_parser.set_defaults(function=manager.add_qubes_to_group)

    group_parser = subparsers.add_parser("group")
    group_subparsers = group_parser.add_subparsers()

    add_group_parser = group_subparsers.add_parser("add")
    add_group_parser.add_argument("group", type=str, help="Group name")
    add_group_parser.add_argument("period", type=str, help="Period")
    add_group_parser.set_defaults(function=manager.add_group)

    del_group_parser = group_subparsers.add_parser("del")
    del_group_parser.add_argument("group", type=str, help="Group name")
    del_group_parser.set_defaults(function=manager.delete_group)

    ls_group_parser = group_subparsers.add_parser("list")
    ls_group_parser.set_defaults(function=manager.list_groups)

    args = parser.parse_args()

    local_path = Path("~/.config/qbackup").expanduser()
    os.makedirs(local_path, exist_ok=True)

    with SqliteConnector(local_path, {}) as connector:
        manager.initialize(connector, args)
        args.function()

