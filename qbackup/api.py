"""
Data structures for default API
"""

from abc import ABC, abstractclassmethod
from dataclasses import asdict, dataclass
from types import TracebackType
from typing import Any, Callable, Dict, Hashable, Iterable, List, Optional, Tuple, Union


class AbstractDataConnector(ABC):

    @abstractclassmethod
    def connect(self) -> None:
        pass

    @abstractclassmethod
    def close(self) -> None:
        pass

    @abstractclassmethod
    def load(self) -> Any:
        pass

    @abstractclassmethod
    def dump(self, data) -> None:
        pass

    def __enter__(self) -> "AbstractDataConnector":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> "AbstractDataConnector":
        self.close()


@dataclass
class AbstractModel(ABC):

    @abstractclassmethod
    def keyid(self) -> Hashable:
        pass

    def serialize(self) -> Tuple[Hashable, Any]:
        return self.keyid(), asdict(self)


class AbstractDataManager(ABC):

    def __init__(
        self,
        connector: AbstractDataConnector,
        model_factory: Callable,
        lazy: bool = False,
    ) -> None:
        super().__init__()
        self._connector = connector
        self._data = None
        self._model_factory = model_factory

        if not lazy:
            self.init()

    def init(self):
        self._data = self.copy_data(
            self._connector.load()
        )

    def save(self) -> None:
        self._connector.dump(self._data)

    @abstractclassmethod
    def upsert(self, model: AbstractModel) -> str:
        pass

    @abstractclassmethod
    def delete(self, keyid: Hashable) -> None:
        pass

    @abstractclassmethod
    def find_data_by_keyid(self, keyid: Hashable) -> Dict:
        pass

    @abstractclassmethod
    def copy_data(self, data) -> Any:
        pass

    @abstractclassmethod
    def get_list(self) -> Iterable[Dict]:
        pass

    def get(self, keyid: Hashable) -> AbstractModel:
        result = self.find_data_by_keyid(keyid)
        if result is None:
            return None
        return self._model_factory(**result)

    def list(self) -> List[AbstractModel]:
        return [
            self._model_factory(**result)
            for result in self.get_list()
        ]


class DictDataManager(AbstractDataManager):
    def upsert(self, model: AbstractModel) -> str:
        model_id, model_data = model.serialize()
        self._data[model_id] = model_data

    def delete(self, keyid: Hashable) -> None:
        if keyid not in self._data:
            raise ValueError(f"Unknow model with key: {keyid}")

        self._data.pop(keyid)

    def find_data_by_keyid(self, keyid: Hashable) -> Any:
        return self._data.get(keyid)

    def copy_data(self, data) -> Any:
        return data.copy()

    def get_list(self) -> Iterable[Dict]:
        return self._data.values()