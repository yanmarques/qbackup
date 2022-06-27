"""
Data structures for default API
"""

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)
from uuid import uuid4

HAS_YAML = False
try:
    import yaml

    HAS_YAML = True
except ImportError:
    pass


class ModelNotFound(ValueError):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class AbstractDataConnector(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    def __enter__(self) -> "AbstractDataConnector":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: BaseException = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        return self.close()


class AbstractModel(ABC):
    @abstractmethod
    def keyid(self) -> Hashable:
        pass

    def serialize(self) -> Tuple[Hashable, Any]:
        return self.keyid(), asdict(self)


class AbstractDataManager(ABC):
    def __init__(
        self,
        prefix: str,
        connector: AbstractDataConnector,
        model_factory: Callable,
        id_field: str = "id",
    ) -> None:
        super().__init__()
        self._id = id_field
        self._prefix = prefix
        self._connector = connector
        self._model_factory = model_factory
        self._init()

    def get(self, keyid: Hashable) -> Optional[AbstractModel]:
        return self.where(self._id, keyid)

    def list(self) -> List[AbstractModel]:
        return list(map(self._build_model, self._fetch_list()))

    def get_or_fail(self, keyid: Hashable) -> AbstractModel:
        model = self.get(keyid)
        if model is None:
            raise ModelNotFound(f"Unable to find model with keyid: {keyid}")

        return model

    def where(self, field: str, value) -> Optional[AbstractModel]:
        result = self._find_data_by_field(field, value)
        if result is None:
            return None
        return self._build_model(result)

    def slow_find_all(self, **kwargs) -> Iterable[AbstractModel]:
        found_models: List[AbstractModel] = []

        for model in self.list():
            _, model_data = model.serialize()
            if all(
                model_data.get(key) == value for key, value in kwargs.items()
            ):
                found_models.append(model)
        return found_models

    def slow_find_one(self, **kwargs) -> Optional[AbstractModel]:
        for model in self.list():
            _, model_data = model.serialize()
            if all(
                model_data.get(key) == value for key, value in kwargs.items()
            ):
                return model
        return None

    @abstractmethod
    def save(self) -> None:
        pass

    @abstractmethod
    def upsert(self, model: AbstractModel) -> Hashable:
        pass

    @abstractmethod
    def delete(self, keyid: Hashable) -> None:
        pass

    @abstractmethod
    def _find_data_by_field(self, keyid: str, value) -> Optional[Any]:
        pass

    @abstractmethod
    def _fetch_list(self) -> Iterable[Dict]:
        pass

    def _init(self):
        pass

    def _build_model(self, kwargs: Dict) -> AbstractModel:
        return self._model_factory(**kwargs)


class AbstractReadWriteStream(ABC):
    def __init__(
        self,
        uri: Union[Path, str],
        default_return=None,
    ) -> None:
        self._uri = Path(uri)
        self._default = default_return

    @abstractmethod
    def load(self) -> Any:
        pass

    @abstractmethod
    def dump(self, data: Any) -> None:
        pass

    def set_default_return(self, default_return) -> None:
        self._default = default_return


if HAS_YAML:

    class YamlStream(AbstractReadWriteStream):
        def load(self) -> Any:
            if not self._uri.exists():
                return self._default

            with open(self._uri) as fp:
                data = yaml.safe_load(fp)
                return data or self._default

        def dump(self, data: Any) -> None:
            with open(self._uri, "w") as fp:
                yaml.safe_dump(data, fp)
