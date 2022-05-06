from dataclasses import dataclass
from typing import Hashable
from qbackup.api import DictDataManager, AbstractModel


@dataclass
class Foo(AbstractModel):
    name: str
    age: int

    def keyid(self) -> Hashable:
        return self.name


def test_dict_data_manager_keeps_model(test_connector):
    with test_connector:
        data_manager = DictDataManager(test_connector, Foo)
        model = Foo("baz", 321)
        data_manager.upsert(model)

        assert data_manager.get("baz") == model


def test_dict_data_manager_saves_raw_data_to_connector(test_connector):
    with test_connector:
        data_manager = DictDataManager(test_connector, Foo)
        model = Foo("baz", 321)

        data_manager.upsert(model)
        data_manager.save()

        assert test_connector.load() == {
            "baz": {
                "name": "baz",
                "age": 321
            }
        }


def test_dict_data_manager_keeps_model_in_memory_when_save_is_not_called(test_connector):
    with test_connector:
        data_manager = DictDataManager(test_connector, Foo)
        model = Foo("bar", 123)

        data_manager.upsert(model)

        assert test_connector.load() == {}


def test_dict_data_manager_lists_all_models(test_connector):
    with test_connector:
        data_manager = DictDataManager(test_connector, Foo)
        model1 = Foo("foo", 123)
        model2 = Foo("bar", 321)
        expected = [model1, model2]

        data_manager.upsert(model1)
        data_manager.upsert(model2)

        assert data_manager.list() == expected


def test_dict_data_manager_delete_model(test_connector):
    with test_connector:
        data_manager = DictDataManager(test_connector, Foo)
        model = Foo("foo", 123)

        data_manager.upsert(model)
        data_manager.delete("foo")

        assert data_manager.get("foo") is None