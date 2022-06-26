"""
CLI interface functions
"""

import argparse
import getpass
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Iterable,
    Optional,
    Sequence,
    Set,
    TextIO,
    cast,
)

from .api import (
    HAS_YAML,
    AbstractDataConnector,
    AbstractDataManager,
    ModelNotFound,
)
from .connectors import FileBackedConnector
from .database import StreamDataManager
from .models import DestQube, Group, Password, Period, Qube
from .utils import PrettyDumpModels

INIT_SQL = """
CREATE TABLE groups (
    name VARCHAR NOT NULL PRIMARY KEY,
    period VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    dest_qube VARCHAR NOT NULL,
    FOREIGN KEY (dest_qube) REFERENCES dest_qube(id),
    FOREIGN KEY (password) REFERENCES passwords(content),
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

CREATE TABLE passwords (
    name VARCHAR NOT NULL PRIMARY KEY,
    content VARCHAR NOT NULL,
    is_default BOOLEAN NOT NULL
);

CREATE TABLE dest_qubes (
    name VARCHAR NOT NULL PRIMARY KEY,
    qube VARCHAR NOT NULL,
    executable VARCHAR NOT NULL
);
"""


class QbackupCLIManager:
    def initialize(
        self,
        data_manager_factory: Callable,
        connector: AbstractDataConnector,
        args: argparse.Namespace,
        stream: TextIO,
    ) -> None:
        self.connector = connector
        self.args = args
        self.stream = stream
        self.groups: AbstractDataManager = data_manager_factory(
            "groups", connector, Group, id_field="name"
        )
        self.periods: AbstractDataManager = data_manager_factory(
            "periods", connector, Period, id_field="name"
        )
        self.qubes: AbstractDataManager = data_manager_factory(
            "qubes", connector, Qube
        )
        self.passwords: AbstractDataManager = data_manager_factory(
            "passwords", connector, Password, id_field="name"
        )
        self.dest_qubes: AbstractDataManager = data_manager_factory(
            "dest_qubes",
            connector,
            DestQube,
            id_field="name",
        )

    def list_passwords(self) -> None:
        PrettyDumpModels(self.stream, self.passwords).fetch_and_dump_list()

    def add_password(self) -> None:
        password_model = cast(
            Optional[Password], self.passwords.get(self.args.name)
        )

        if self.args.default:
            password_list = cast(
                Iterable[Password],
                self.passwords.slow_find_all(
                    is_default=True,
                ),
            )

            # Remove default password if sets to default
            for model in password_list:
                model.is_default = False
                self.passwords.upsert(model)

        password = getpass.getpass("Password: ")
        if password_model is None:
            is_default = self.args.default

            if not self.passwords.list():
                print("Creating password as default")
                is_default = True

            password_model = Password(
                name=self.args.name,
                content=password,
                is_default=is_default,
            )
        else:
            print("Password updated!")
            password_model.content = password
            password_model.is_default = self.args.default

        self.passwords.upsert(password_model)
        self.passwords.save()

    def list_dest_qubes(self) -> None:
        PrettyDumpModels(self.stream, self.dest_qubes).fetch_and_dump_list()

    def add_dest_qube(self) -> None:
        dest_qube = cast(
            Optional[DestQube], self.dest_qubes.get(self.args.name)
        )

        if dest_qube is None:
            dest_qube = DestQube(
                name=self.args.name,
                qube=self.args.qube,
                executable=self.args.executable,
            )
        else:
            dest_qube.qube = self.args.qube
            dest_qube.executable = self.args.executable

        self.dest_qubes.upsert(dest_qube)
        self.dest_qubes.save()

    def list_groups(self) -> None:
        PrettyDumpModels(self.stream, self.groups).fetch_and_dump_list()

    def add_group(self) -> None:
        group = self.groups.get(self.args.group)
        if group is not None:
            raise ValueError("Group already exists")

        period = cast(Optional[Period], self.periods.get(self.args.period))

        if period is None:
            raise ModelNotFound(
                f"Period not found: {self.args.period}. "
                f"Please create it first."
            )

        password = cast(
            Optional[Password], self.passwords.get(self.args.passwd)
        )

        if password is None:
            default_password = cast(
                Optional[Password],
                self.passwords.slow_find_one(
                    is_default=True,
                ),
            )

            if default_password is None:
                raise ModelNotFound(
                    "No password provided and any default password availabe. "
                    "Please create a new password or provide an existing one"
                )
            password = default_password

        dest_qube = cast(
            Optional[DestQube], self.dest_qubes.get(self.args.dest_qube)
        )
        if dest_qube is None:
            raise ModelNotFound(
                f"Destionation qube not found: {self.args.dest_qube}. "
                f"Please create it first."
            )

        group = Group(
            name=self.args.group,
            period=period.name,
            password=password.name,
            dest_qube=dest_qube.name,
        )

        self.groups.upsert(group)
        self.groups.save()

    def delete_qubes_from_group(self) -> None:
        group = cast(Group, self.groups.get_or_fail(self.args.group))

        for qube in self.args.qubes[0]:
            qube_model = cast(
                Optional[Qube],
                self.qubes.slow_find_one(
                    name=qube,
                    group_name=group.name,
                ),
            )

            if qube_model is None:
                raise ModelNotFound(f"Unknown qube: {qube}")

            self.qubes.delete(qube_model.id)
        self.qubes.save()

    def delete_group(self) -> None:
        qubes = cast(
            Iterable[Qube],
            self.qubes.slow_find_all(group_name=self.args.group),
        )

        for qube in qubes:
            self.qubes.delete(qube.id)

        self.groups.delete(self.args.group)
        self.groups.save()

    def list_qubes(self) -> None:
        PrettyDumpModels(self.stream, self.qubes).fetch_and_dump_list()

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
            qube = cast(
                Optional[Qube],
                self.qubes.slow_find_one(
                    name=qube_name,
                    group_name=self.args.group,
                ),
            )

            if qube is None:
                raise ValueError("Qube is not associated with group")

            self.qubes.delete(qube.id)
        self.qubes.save()

    def list_periods(self) -> None:
        PrettyDumpModels(self.stream, self.periods).fetch_and_dump_list()

    def add_periods(self) -> None:
        for period_name in self.args.periods[0]:
            period = Period(period_name)
            self.periods.upsert(period)
        self.periods.save()

    def delete_periods(self) -> None:
        for period_name in self.args.periods[0]:
            groups = self.groups.slow_find_all(period=period_name)

            if groups:
                raise ValueError(
                    f"Period is still associated with the "
                    f"following groups: {groups}. Please disassociate them"
                )

            self.periods.delete(period_name)
        self.periods.save()

    def run_backup(self) -> None:
        groups = cast(
            Iterable[Group], self.groups.slow_find_all(period=self.args.period)
        )

        if not groups:
            raise ModelNotFound(
                f"No groups found for period: {self.args.period}"
            )

        subprocess.run(
            [
                "notify-send",
                "-u",
                "critical",
                "Automated Backup",
                f"Starting backup: {self.args.period}",
            ],
            env={"DISPLAY": ":0"},
        )

        qubes_started: Set[str] = set()
        failed_groups: Set[str] = set()

        for group in groups:
            dest_qube = cast(
                DestQube, self.dest_qubes.get_or_fail(group.dest_qube)
            )

            password = cast(
                Password, self.passwords.get_or_fail(group.password)
            )

            subprocess.run(
                [
                    "notify-send",
                    "Automated Backup",
                    f"Starting backup for group: {group.name}",
                ],
                env={"DISPLAY": ":0"},
            )

            # maybe start qube
            subprocess.run(["qvm-start", "--skip-if-running", dest_qube.qube])

            qubes_started.add(dest_qube.qube)

            try:
                self.run_backup_for(group, dest_qube, password)
            except:
                failed_groups.add(group.name)
                subprocess.run(
                    [
                        "notify-send",
                        "Automated Backup",
                        f"Failed backup for group: {group.name}",
                    ],
                    env={"DISPLAY": ":0"},
                )

        for qube_started in qubes_started:
            subprocess.run(["qvm-shutdown", qube_started])

        if failed_groups:
            group_list_str = ",".join(failed_groups)
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "critical",
                    "Automated Backup",
                    "Backup finished. The following groups "
                    f"failed: {group_list_str}",
                ],
                env={"DISPLAY": ":0"},
            )
        else:
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "critical",
                    "Automated Backup",
                    "Backup finished. All groups succeeded!",
                ],
                env={"DISPLAY": ":0"},
            )

    def run_backup_for(
        self,
        group: Group,
        dest_qube: DestQube,
        password: Password,
    ) -> None:
        qubes = cast(
            Iterable[Qube], self.qubes.slow_find_all(group_name=group.name)
        )

        now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        remote_command = dest_qube.executable.format(
            period=group.period,
            group=group.name,
            now=now,
        )

        args = [
            "qvm-backup",
            "--yes",
            "--compress",
            "--exclude",
            "dom0",
            "--passphrase-file",
            "-",
            "--dest-vm",
            dest_qube.qube,
            remote_command,
        ]

        for qube in qubes:
            args.append(qube.name)

        subprocess.run(
            args,
            input=password.content.encode() + b"\n",
            check=True,
        )


class CommandLineInterface:
    def __init__(self) -> None:
        # self.local_path: Optional[Path] = None
        # self.database: Optional[Path] = None
        # self.bootstrap_sql: Optional[str] = None
        # self.cli_manager: Optional[QbackupCLIManager] = None
        pass

    def run(self, cli_args: Sequence[str] = None) -> None:

        cli_manager = QbackupCLIManager()

        parser = self.get_parser(cli_manager)
        args = parser.parse_args(cli_args)

        if not hasattr(args, "function"):
            parser.error("Missing command")

        local_path = Path(args.config).expanduser()
        os.makedirs(local_path, exist_ok=True)

        database = local_path / "db"

        bootstrap_sql = None
        if not database.exists():
            bootstrap_sql = INIT_SQL

        connector_factory, data_manager_factory = self.deduce_database(
            bootstrap_sql
        )

        with connector_factory(database) as connector:
            cli_manager.initialize(
                data_manager_factory, connector, args, sys.stdout
            )
            args.function()

    def deduce_database(self, bootstrap_sql: Optional[str]):
        # if HAS_YAML:
        #     from .api import YamlStream

        #     def data_manager_factory(*args, **kwargs):
        #         stream = YamlStream(self.local_path)
        #         return StreamDataManager(stream, *args, **kwargs)

        #     return (FileBackedConnector, data_manager_factory)

        from .connectors import SqliteConnector
        from .database import SqliteDataManager

        def connector_factory(path):
            return SqliteConnector(path, bootstrap_sql)

        return (connector_factory, SqliteDataManager)

    def get_parser(
        self, cli_manager: QbackupCLIManager
    ) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-c",
            "--config",
            type=str,
            help="Path to configuration directory. Default is ~/.config/qbackup",
            default="~/.config/qbackup",
        )

        subparsers = parser.add_subparsers()

        # vm_parser = subparsers.add_parser("install")
        # vm_parser.set_defaults(function=install_cron)

        run_parser = subparsers.add_parser("run")
        run_parser.add_argument("period", type=str)
        run_parser.set_defaults(function=cli_manager.run_backup)

        qube_parser = subparsers.add_parser("qube")
        qube_subparsers = qube_parser.add_subparsers()

        del_qube_parser = qube_subparsers.add_parser("del")
        del_qube_parser.add_argument("group", type=str, help="Group name")
        del_qube_parser.add_argument("qubes", action="append", nargs="+")
        del_qube_parser.set_defaults(
            function=cli_manager.disassociate_qubes_from_group
        )

        add_qube_parser = qube_subparsers.add_parser("add")
        add_qube_parser.add_argument("group", type=str, help="Group name")
        add_qube_parser.add_argument("qubes", action="append", nargs="+")
        add_qube_parser.set_defaults(
            function=cli_manager.associate_qubes_to_group
        )

        ls_qube_parser = qube_subparsers.add_parser("list")
        ls_qube_parser.set_defaults(function=cli_manager.list_qubes)

        passwd_parser = subparsers.add_parser("password")
        passwd_subparsers = passwd_parser.add_subparsers()

        ls_passwd_parser = passwd_subparsers.add_parser("list")
        ls_passwd_parser.set_defaults(function=cli_manager.list_passwords)

        add_passwd_parser = passwd_subparsers.add_parser("add")
        add_passwd_parser.add_argument(
            "name", help="Password name used for identification"
        )
        add_passwd_parser.add_argument(
            "--default",
            action="store_true",
            default=False,
            help="Set this password as the default one",
        )
        add_passwd_parser.set_defaults(function=cli_manager.add_password)

        dest_qube_parser = subparsers.add_parser("dest-qube")
        dest_qube_subparsers = dest_qube_parser.add_subparsers()

        dest_qube_passwd_parser = dest_qube_subparsers.add_parser("list")
        dest_qube_passwd_parser.set_defaults(
            function=cli_manager.list_dest_qubes
        )

        add_dest_qube_parser = dest_qube_subparsers.add_parser("add")
        add_dest_qube_parser.add_argument(
            "name", help="Name to identify the qube destination"
        )
        add_dest_qube_parser.add_argument("qube", help="Qube name")
        add_dest_qube_parser.add_argument(
            "executable", help="Executable to run for receive the backup"
        )
        add_dest_qube_parser.set_defaults(function=cli_manager.add_dest_qube)

        group_parser = subparsers.add_parser("group")
        group_subparsers = group_parser.add_subparsers()

        add_group_parser = group_subparsers.add_parser("add")
        add_group_parser.add_argument("group", type=str, help="Group name")
        add_group_parser.add_argument("period", type=str, help="Period")
        add_group_parser.add_argument("dest_qube", help="Destination qube")
        add_group_parser.add_argument(
            "--passwd",
            help=(
                "Password name. If not provided, we will try "
                "to use the default password"
            ),
        )
        add_group_parser.set_defaults(function=cli_manager.add_group)

        del_group_parser = group_subparsers.add_parser("del")
        del_group_parser.add_argument("group", help="Group name")
        del_group_parser.set_defaults(function=cli_manager.delete_group)

        ls_group_parser = group_subparsers.add_parser("list")
        ls_group_parser.set_defaults(function=cli_manager.list_groups)

        period_subparsers = subparsers.add_parser("period").add_subparsers()

        del_period_parser = period_subparsers.add_parser("del")
        del_period_parser.add_argument(
            "periods", action="append", nargs="+", help="Period name"
        )
        del_period_parser.set_defaults(function=cli_manager.delete_periods)

        add_period_parser = period_subparsers.add_parser("add")
        add_period_parser.add_argument(
            "periods", action="append", nargs="+", help="Period name"
        )
        add_period_parser.set_defaults(function=cli_manager.add_periods)

        ls_period_parser = period_subparsers.add_parser("list")
        ls_period_parser.set_defaults(function=cli_manager.list_periods)

        return parser


def main(args: Sequence[str] = None):
    cli = CommandLineInterface()
    cli.run(args)
