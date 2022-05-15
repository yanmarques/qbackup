from collections import namedtuple
from pytest import fixture
import pytest
from qbackup.api import ModelNotFound
from qbackup.cli import QbackupCLIManager
from qbackup.database import StreamDataManager


@fixture
def cli_manager(request, dummy_connector, dummy_rw_stream):
    def data_manager_factory(*args, **kwargs):
        return StreamDataManager(
            dummy_rw_stream,
            *args,
            **kwargs,
        )

    manager = QbackupCLIManager(data_manager_factory)
    namespace = namedtuple("Namespace", request.param.keys())
    args = namespace(**request.param)
    manager.initialize(dummy_connector, args)
    
    return manager


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            "periods": [["monthly"],],
            "expected": ["monthly"],
        },
        {
            "periods": [["monthly", "monthly"],],
            "expected": ["monthly"],
        },
        {
            "periods": [[],],
            "expected": [],
        },
    ],
    indirect=True,
)
def test_add_periods(cli_manager):
    cli_manager.add_periods()
    period_names = [p.name for p in cli_manager.periods.list()]
    assert period_names == cli_manager.args.expected


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            "periods": [["monthly"],],
        }
    ],
    indirect=True,
)
def test_delete_periods(cli_manager):
    cli_manager.add_periods()
    cli_manager.delete_periods() 
    assert cli_manager.periods.list() == []


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            "periods": [["monthly"],],
        }
    ],
    indirect=True,
)
def test_delete_periods_fail_when_period_is_not_found(cli_manager):
    cli_manager.add_periods()
    cli_manager.delete_periods()

    with pytest.raises(ModelNotFound):
        cli_manager.delete_periods()


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "group": "foo group",
            "period": "monthly",
        }
    ],
    indirect=True,
)
def test_add_group_will_upsert_list_of_groups(cli_manager):
    cli_manager.add_periods()

    cli_manager.add_group()
    group_names = [p.name for p in cli_manager.groups.list()]
    assert group_names == ["foo group"]


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Create period first
            "periods": [["monthly"],],

            # Create group associated with period
            "period": "monthly",
            "group": "foo group",
        }
    ],
    indirect=True,
)
def test_delete_periods_fail_when_there_are_groups_associated(cli_manager):
    cli_manager.add_periods()
    cli_manager.add_group()

    with pytest.raises(ValueError):
        cli_manager.delete_periods()


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "group": "foo group",
            "period": "monthly",
        }
    ],
    indirect=True,
)
def test_add_group_will_fail_when_name_already_exists(cli_manager):
    cli_manager.add_periods()
    cli_manager.add_group()

    with pytest.raises(ValueError):
        cli_manager.add_group()


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            "group": "foo group",
            "period": "monthly",
        }
    ],
    indirect=True,
)
def test_add_group_will_fail_when_period_not_exists(cli_manager):
    with pytest.raises(ModelNotFound):
        cli_manager.add_group()


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "group": "foo group",
            "period": "monthly",

            "qubes": [["foo qube", "bar qube"]]
        }
    ],
    indirect=True,
)
def test_delete_group_will_disassociate_all_qubes(cli_manager):
    cli_manager.add_periods()
    cli_manager.add_group()
    cli_manager.add_qubes_to_group()

    assert cli_manager.qubes.list()

    cli_manager.delete_group()

    assert not cli_manager.qubes.list()


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "period": "monthly",
            "group": "foo group",
            "qubes": [["foo qube", "bar qube"]],
        }
    ],
    indirect=True,
)
def test_add_qubes_to_group(cli_manager):
    expected_qubes = [
        dict(name="foo qube", group_name="foo group"),
        dict(name="bar qube", group_name="foo group"),
    ]

    cli_manager.add_periods()
    cli_manager.add_group()
    cli_manager.add_qubes_to_group()
    
    qubes = [
        dict(name=q.name, group_name=q.group_name)
        for q in cli_manager.qubes.list()
    ]

    assert qubes == expected_qubes


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "period": "monthly",
            "group": "foo group",
            "qubes": [["foo qube", "bar qube"]],
            "deleted_qubes": [["bar qube"]],
        },
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "period": "monthly",
            "group": "foo group",
            "qubes": [["foo qube", "bar qube"]],
            "deleted_qubes": [["foo qube", "bar qube"]],
        }
    ],
    indirect=True,
)
def test_delete_qubes_from_group(cli_manager):
    deleted_qubes = set(cli_manager.args.qubes[0]) - \
        set(cli_manager.args.deleted_qubes[0])

    expected_qubes = [
        dict(name=name, group_name=cli_manager.args.group)
        for name in deleted_qubes
    ]

    cli_manager.add_periods()
    cli_manager.add_group()
    cli_manager.add_qubes_to_group()

    # Change the qubes that will be deleted at runtime
    cli_manager.args = cli_manager.args._replace(
        qubes=cli_manager.args.deleted_qubes
    )

    cli_manager.delete_qubes_from_group()
    
    qubes = [
        dict(name=q.name, group_name=q.group_name)
        for q in cli_manager.qubes.slow_find_all(group_name=cli_manager.args.group)
    ]

    assert qubes == expected_qubes


@pytest.mark.parametrize(
    "cli_manager",
    [
        {
            # Add the period before creating the group
            "periods": (["monthly"],),

            "period": "monthly",
            "group": "foo group",
            "qubes": [["foo qube"]],
        }
    ],
    indirect=True,
)
def test_delete_qubes_from_group_will_fail_when_qube_not_associated(cli_manager):
    cli_manager.add_periods()
    cli_manager.add_group()

    with pytest.raises(ModelNotFound):
        cli_manager.delete_qubes_from_group()
