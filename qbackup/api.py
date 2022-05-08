"""
Data structures for default API
"""

from abc import ABC, abstractclassmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Dict, Hashable, Iterable, List, Optional, Tuple, Union
from uuid import uuid4

import yaml


class AbstractDataConnector(ABC):

    @abstractclassmethod
    def connect(self) -> None:
        pass

    @abstractclassmethod
    def close(self) -> None:
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


def genuuid() -> str:
    return str(uuid4())


@dataclass
class UUIDModelIdentifier:
    id: str = field(default_factory=genuuid)

    def keyid(self) -> Hashable:
        return self.id


class AbstractDataManager(ABC):

    def __init__(
        self,
        prefix: str,
        connector: AbstractDataConnector,
        model_factory: Callable,
    ) -> None:
        super().__init__()
        self._prefix = prefix
        self._connector = connector
        self._data = None
        self._model_factory = model_factory
        self._init()

    def get(self, keyid: Hashable) -> Optional[AbstractModel]:
        result = self._find_data_by_keyid(keyid)
        if result is None:
            return None
        return self._build_model(result)

    def list(self) -> List[AbstractModel]:
        return list(map(self._build_model, self._fetch_list()))

    def get_or_fail(self, keyid: Hashable) -> AbstractModel:
        model = self.get(keyid)
        if model is None:
            raise ValueError(
                f"Unable to find model with keyid: {keyid}"
            )

        return model

    @abstractclassmethod
    def save(self) -> None:
        pass

    @abstractclassmethod
    def upsert(self, model: AbstractModel) -> str:
        pass

    @abstractclassmethod
    def delete(self, keyid: Hashable) -> None:
        pass

    @abstractclassmethod
    def _find_data_by_keyid(self, keyid: Hashable) -> Dict:
        pass

    @abstractclassmethod
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
        default_return = None,
    ) -> None:
        self._uri = Path(uri)
        self._default = default_return

    @abstractclassmethod
    def load(self) -> Any:
        pass

    @abstractclassmethod
    def dump(self, data) -> None:
        pass

    def set_default_return(self, default_return) -> None:
        self._default = default_return


class YamlStream(AbstractReadWriteStream):
    def load(self) -> Dict:
        if not self._uri.exists():
            return self._default

        with open(self._uri) as fp:
            data = yaml.safe_load(fp)
            return data or self._default

    def dump(self, data) -> None:
        with open(self._uri, 'w') as fp:
            yaml.safe_dump(data, fp)