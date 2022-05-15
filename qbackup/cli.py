"""
CLI interface functions
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
from pprint import pprint
from re import M
import subprocess
from typing import Dict

from .api import AbstractDataManager, ModelNotFound, YamlStream
from .connectors import FileBackedConnector
from .database import StreamDataManager
from .models import Group, Period, Qube


INIT_SQL = """
CREATE TABLE groups (
    name VARCHAR NOT NULL PRIMARY KEY,
    period VARCHAR NOT NULL,
    FOREIGN KEY (period) REFERENCES periods(name)
);

CREATE TABLE periods (
    name VARCHAR NOT NULL PRIMARY KEY
);

CREATE TABLE qubes (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    group_name VARCHAR NOT NULL,
    FOREIGN KEY (group_name) REFERENCES groups(name)
);
"""


class QbackupCLIManager:
    def __init__(self, data_manager_factory) -> None:
        self.data_manager_factory = data_manager_factory

    def initialize(self, connector, args) -> None:
        self.connector = connector
        self.args = args
        self.groups: AbstractDataManager = self.data_manager_factory(
            "groups",
            connector,
            Group,
            id_field="name"
        )
        self.periods: AbstractDataManager = self.data_manager_factory(
            "periods",
            connector,
            Period,
            id_field="name"
        )
        self.qubes: AbstractDataManager = self.data_manager_factory(
            "qubes",
            connector,
            Qube
        )

    def list_groups(self) -> None:
        pprint(self.groups.list())

    def add_group(self) -> None:
        group = self.groups.get(self.args.group)
        if group is not None:
            raise ValueError("Group already exists")

        period = self.periods.get(self.args.period)
        if period is None:
            raise ModelNotFound(
                f"Period not found: {self.args.period}. "
                f"Please create it first."
            )

        group = Group(name=self.args.group, period=period.name)

        self.groups.upsert(group)
        self.groups.save()

    def delete_qubes_from_group(self) -> None:
        group = self.groups.get_or_fail(self.args.group)

        for qube in self.args.qubes[0]:
            qube_model = self.qubes.slow_find_one(
                name=qube,
                group_name=group.name,
            )

            if qube_model is None:
                raise ModelNotFound(
                    f"Unknown qube: {qube}"
                )

            self.qubes.delete(qube_model.id)
        self.qubes.save()

    def delete_group(self) -> None:
        for qube in self.qubes.slow_find_all(
            group_name=self.args.group
        ):
            self.qubes.delete(qube.id)

        self.groups.delete(self.args.group)
        self.groups.save()

    def list_qubes(self) -> None:
        pprint(self.qubes.list())

    def associate_qubes_to_group(self) -> None:
        self.groups.get_or_fail(self.args.group)

        for qube_name in self.args.qubes[0]:
            qube = self.qubes.slow_find_one(
                name=qube_name,
                group_name=self.args.group,
            )

            if qube is not None:
                raise ValueError("Qube is already associated with group")

            qube = Qube(name=qube_name, group_name=self.args.group)

            self.qubes.upsert(qube)
        self.qubes.save()

    def disassociate_qubes_from_group(self) -> None:
        for qube_name in self.args.qubes[0]:
            qube = self.qubes.slow_find_one(
                name=qube_name,
                group_name=self.args.group,
            )

            if qube is None:
                raise ValueError("Qube is not associated with group")

            self.qubes.delete(qube.id)
        self.qubes.save()

    def list_periods(self) -> None:
        pprint(self.periods.list())

    def add_periods(self) -> None:
        for period_name in self.args.periods[0]:
            period = Period(period_name)
            self.periods.upsert(period)
        self.periods.save()

    def delete_periods(self) -> None:
        for period_name in self.args.periods[0]:
            groups = self.groups.slow_find_all(
                period=period_name
            )

            if groups:
                raise ValueError(
                    f"Period is still associated with the "
                    f"following groups: {groups}. Please disassociate them"
                )

            self.periods.delete(period_name)
        self.periods.save()

    def run_backup(self) -> None:
        groups = self.groups.slow_find_all(
            period=self.args.period
        )

        if not groups:
            raise ModelNotFound(
                f"No groups found for period: {self.args.period}"
            )

        subprocess.run([
            "notify-send",
            "-u",
            "critical",
            "Automated Backup",
            f"Starting backup: {self.args.period}"
        ], env={"DISPLAY": ":0"})

        for group in groups:
            self.run_backup_for_group(group)

    def run_backup_for_group(self, group: Group) -> None:
        qubes = self.qubes.slow_find_all(
            group_name=group.name
        )

        subprocess.run([
            "notify-send",
            "Automated Backup",
            f"Starting backup for group: {group.name}"
        ], env={"DISPLAY": ":0"})

        now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        remote_command = " ; ".join([
            ". ~/.bash_profile",
            f"ssh $SSH_CONN {group.name}-{now}.backup",
        ])

        dest_vm = "home-backups"

        args = [
            "qvm-backup",
            "--yes",
            "--compress",
            "--exclude",
            "dom0",
            "--dest-vm",
            dest_vm,
            f"sh -c '{remote_command}'",
        ]

        for qube in qubes:
            args.append(qube.name)

        password = b"abc"
        subprocess.run(args, input=password + b"\n")


class CommandLineInterface:
    def __init__(self) -> None:
        self.local_path: Path = None
        self.database: Path = None
        self.bootstrap_sql: str = None
        self.cli_manager: QbackupCLIManager = None

    def run(self, cli_args: Dict[str, str] = None) -> None:
        connector_factory, data_manager_factory = self.deduce_database()

        self.cli_manager = QbackupCLIManager(data_manager_factory)

        parser = self.get_parser()
        args = parser.parse_args(cli_args)

        if not hasattr(args, "function"):
            parser.error("Missing command")

        self.local_path = Path(args.config).expanduser()
        os.makedirs(self.local_path, exist_ok=True)

        self.database = self.local_path / "db"

        self.bootstrap_sql = None
        if not self.database.exists():
            self.bootstrap_sql = INIT_SQL

        with connector_factory(self.database) as connector:
            self.cli_manager.initialize(connector, args)
            args.function()

    def deduce_database(self):
        try:
            import sqlite3
            from .database import SqliteDataManager
            from .connectors import SqliteConnector

            def connector_factory(path):
                return SqliteConnector(path, self.bootstrap_sql)

            return (
                connector_factory,
                SqliteDataManager
            )
        except ImportError:
            pass

        def data_manager_factory(*args, **kwargs):
            stream = YamlStream(self.local_path)
            return StreamDataManager(
                stream,
                *args,
                **kwargs
            )

        return (
            FileBackedConnector,
            data_manager_factory
        )

    def get_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-c",
            "--config",
            type=str,
            help="Path to configuration directory. Default is ~/.config/qbackup",
            default="~/.config/qbackup"
        )

        subparsers = parser.add_subparsers()

        # vm_parser = subparsers.add_parser("install")
        # vm_parser.set_defaults(function=install_cron)

        run_parser = subparsers.add_parser("run")
        run_parser.add_argument("period", type=str)
        run_parser.set_defaults(
            function=self.cli_manager.run_backup
        )

        qube_parser = subparsers.add_parser("qube")
        qube_subparsers = qube_parser.add_subparsers()

        del_qube_parser = qube_subparsers.add_parser("del")
        del_qube_parser.add_argument("group", type=str, help="Group name")
        del_qube_parser.add_argument("qubes", action="append", nargs="+")
        del_qube_parser.set_defaults(
            function=self.cli_manager.disassociate_qubes_from_group
        )

        add_qube_parser = qube_subparsers.add_parser("add")
        add_qube_parser.add_argument("group", type=str, help="Group name")
        add_qube_parser.add_argument("qubes", action="append", nargs="+")
        add_qube_parser.set_defaults(
            function=self.cli_manager.associate_qubes_to_group
        )

        ls_qube_parser = qube_subparsers.add_parser("list")
        ls_qube_parser.set_defaults(
            function=self.cli_manager.list_qubes
        )

        group_parser = subparsers.add_parser("group")
        group_subparsers = group_parser.add_subparsers()

        add_group_parser = group_subparsers.add_parser("add")
        add_group_parser.add_argument("group", type=str, help="Group name")
        add_group_parser.add_argument("period", type=str, help="Period")
        add_group_parser.set_defaults(
            function=self.cli_manager.add_group
        )

        del_group_parser = group_subparsers.add_parser("del")
        del_group_parser.add_argument("group", help="Group name")
        del_group_parser.set_defaults(
            function=self.cli_manager.delete_group
        )

        ls_group_parser = group_subparsers.add_parser("list")
        ls_group_parser.set_defaults(
            function=self.cli_manager.list_groups
        )

        period_subparsers = subparsers.add_parser("period").add_subparsers()

        del_period_parser = period_subparsers.add_parser("del")
        del_period_parser.add_argument(
            "periods",
            action="append",
            nargs="+",
            help="Period name"
        )
        del_period_parser.set_defaults(
            function=self.cli_manager.delete_periods
        )

        add_period_parser = period_subparsers.add_parser("add")
        add_period_parser.add_argument(
            "periods",
            action="append",
            nargs="+",
            help="Period name"
        )
        add_period_parser.set_defaults(
            function=self.cli_manager.add_periods
        )

        ls_period_parser = period_subparsers.add_parser("list")
        ls_period_parser.set_defaults(
            function=self.cli_manager.list_periods
        )

        return parser


def main(args: Dict[str, str] = None):
    cli = CommandLineInterface()
    cli.run(args)
