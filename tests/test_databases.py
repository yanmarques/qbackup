from dataclasses import dataclass
from typing import Hashable

from pytest import fixture
import pytest
from qbackup.api import AbstractModel, YamlStream
from qbackup.connectors import FileBackedConnector, SqliteConnector
from qbackup.database import SqliteDataManager, StreamDataManager


TEST_SQL = """
DROP TABLE IF EXISTS test;

CREATE TABLE test (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL
);
"""


@dataclass
class Foo(AbstractModel):
    id: str
    name: str

    def keyid(self) -> Hashable:
        return self.id


@fixture(params=["sqlite", "stream"])
def data_manager(request, tmpdir):
    uri = tmpdir / "db"

    if request.param == "sqlite":
        connector = SqliteConnector(uri, TEST_SQL)

        # `SqliteDataManager` requires the connector to be
        # already connected before instantiating
        connector.connect()

        manager = SqliteDataManager("test", connector, Foo)
    elif request.param == "stream":
        connector = FileBackedConnector(tmpdir)
        connector.connect()
        manager = StreamDataManager(
            YamlStream(uri),
            "test",
            connector,
            Foo,
        )
    else:
        raise ValueError(f"pytest: unknown data manager: {request.param}")

    yield manager
    connector.close()


def test_database_list_all_items_when_empty(data_manager):
    assert data_manager.list() == []


def test_database_returns_data_when_looking_for_with_custom_field(data_manager):
    model = Foo(id="key", name="baz")
    data_manager.upsert(model)

    assert data_manager.where("name", "baz") == model


def test_database_returns_none_when_finding_nonexistent_item(data_manager):
    assert data_manager.where("name", "baz") is None


def test_database_get_model_when_existent(data_manager):
    model = Foo(id="key", name="baz")
    data_manager.upsert(model)
    assert data_manager.get("key") == model


def test_database_get_model_returns_none_when_nonexistent(data_manager):
    assert data_manager.get("does not exists") is None


def test_database_inserts_item_when_nonexistent(data_manager):
    model = Foo(id="key", name="baz")
    data_manager.upsert(model)

    assert data_manager.get("key") == model


def test_database_updates_item_when_existent(data_manager):
    model = Foo(id="key", name="baz")
    data_manager.upsert(model)

    new_model = Foo(id="key", name="new baz")
    data_manager.upsert(new_model)

    assert data_manager.get("key") == new_model


def test_database_updates_item_when_existent(data_manager):
    model = Foo(id="key", name="baz")
    data_manager.upsert(model)

    new_model = Foo(id="key", name="new baz")
    data_manager.upsert(new_model)

    assert data_manager.get("key") == new_model


def test_database_list_all_items(data_manager):
    model1 = Foo(id="key1", name="baz")
    model2 = Foo(id="key2", name="bar")

    data_manager.upsert(model1)
    data_manager.upsert(model2)

    assert data_manager.list() == [model1, model2]


def test_database_deletes_item_when_existent(data_manager):
    model = Foo(id="key", name="baz")
    data_manager.upsert(model)
    data_manager.delete("key")

    assert data_manager.get("key") is None


def test_database_deletes_item_raise_error_when_nonexistent(data_manager):
    with pytest.raises(ValueError):
        data_manager.delete("key")


def test_database_slow_find_all_models_with_condition(data_manager):
    model1 = Foo(id="key1", name="baz")
    model2 = Foo(id="key2", name="bar")

    data_manager.upsert(model1)
    data_manager.upsert(model2)

    models = data_manager.slow_find_all(
        id="key1",
        name="baz",
    )

    assert models == [model1]


def test_database_slow_find_all_returns_empty_when_no_model_matches_all_conditions(data_manager):
    model1 = Foo(id="key1", name="baz")
    model2 = Foo(id="key2", name="bar")

    data_manager.upsert(model1)
    data_manager.upsert(model2)

    models = data_manager.slow_find_all(
        id="abc",
        name="baz",
    )

    assert models == []


def test_database_slow_find_one_return_model_that_matches_condition(data_manager):
    model1 = Foo(id="key1", name="baz")
    model2 = Foo(id="key2", name="bar")

    data_manager.upsert(model1)
    data_manager.upsert(model2)

    found_model = data_manager.slow_find_one(
        id="key2",
        name="bar",
    )

    assert found_model == model2


def test_database_slow_find_one_return_none_when_no_model_matches_condition(data_manager):
    model1 = Foo(id="key1", name="baz")
    model2 = Foo(id="key2", name="bar")

    data_manager.upsert(model1)
    data_manager.upsert(model2)

    found_model = data_manager.slow_find_one(
        id="abc",
        name="bar",
    )

    assert found_model is None
