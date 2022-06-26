from functools import cached_property
import sqlite3
from typing import Any, Dict, Hashable, Iterable, Optional, cast

from qbackup.connectors import SqliteConnector

from .api import AbstractDataManager, AbstractModel, AbstractReadWriteStream

__all__ = ["SqliteDataManager", "StreamDataManager"]


class SqliteDataManager(AbstractDataManager):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not isinstance(self._connector, SqliteConnector):
            raise TypeError(
                f"Invalid connector class: "
                f"expected `SqliteConnector`, found {type(self._connector)}"
            )

        # Setup sqlite connection
        self._sqlite_connection.row_factory = sqlite3.Row

    def save(self) -> None:
        self._sqlite_connection.commit()

    def upsert(self, model: AbstractModel) -> Hashable:
        model_id, model_data = model.serialize()

        if not isinstance(model_data, Dict):
            raise TypeError(
                f"Unknow model data type: "
                f"expected `Dict`, found {type(model_data)}"
            )

        fields = model_data.keys()

        if self.get(model_id) is None:
            fields_str = ",".join(fields)
            placeholders_str = ",".join("?" for _ in range(len(fields)))

            self._execute_sql(
                f"""
                INSERT INTO
                    {self._prefix}
                ({fields_str})
                VALUES
                    ({placeholders_str})
            """,
                list(model_data.values()),
            )
        else:
            placeholders_data = []
            for field in fields:
                # remove id from actual fields
                if field != self._id:
                    placeholders_data.append(f"{field} = ?")

            placeholders_str = ",".join(placeholders_data)

            # remove id from actual data
            model_data.pop(self._id)

            self._execute_sql(
                f"""
                UPDATE
                    {self._prefix}
                SET
                    {placeholders_str}
                WHERE
                    {self._id} = ?
            """,
                [*model_data.values(), model_id],
            )
        return model_id

    def delete(self, keyid: Hashable) -> None:
        self.get_or_fail(keyid)

        self._execute_sql(
            f"""
            DELETE FROM 
                {self._prefix}
            WHERE
                {self._id} = ?
        """,
            [keyid],
        )

    def _find_data_by_field(
        self, field: Hashable, value
    ) -> Optional[sqlite3.Row]:
        cursor = self._execute_sql(
            f"""
            SELECT
                *
            FROM
                {self._prefix}
            WHERE
                {field} = ?
        """,
            [value],
        )

        return cursor.fetchone()

    def _fetch_list(self) -> Iterable[Dict]:
        cursor = self._execute_sql(
            f"""
            SELECT
                *
            FROM
                {self._prefix}
        """
        )

        return cursor.fetchall()

    def _build_model(self, kwargs: Dict) -> AbstractModel:
        if isinstance(kwargs, sqlite3.Row):
            kwargs = dict(kwargs)

        return super()._build_model(kwargs)

    @property
    def _sqlite_connection(self) -> sqlite3.Connection:
        connector: SqliteConnector = cast(SqliteConnector, self._connector)

        if not connector._conn:
            raise RuntimeError("Missing Sqlite connection object")

        return connector._conn

    def _execute_sql(self, sql_str: str, *args, **kwargs) -> sqlite3.Cursor:
        return self._sqlite_connection.execute(sql_str, *args, **kwargs)


class StreamDataManager(AbstractDataManager):
    def __init__(
        self, stream: AbstractReadWriteStream, *args, **kwargs
    ) -> None:
        self._stream = stream
        self._stream.set_default_return({})
        super().__init__(*args, **kwargs)

    def _init(self):
        data = self._stream.load()
        if not isinstance(data, Dict):
            raise TypeError(
                f"Unknown loaded data from stream: "
                f"expected data type `Dict`, found {type(data)}"
            )
        self._data: Dict = data.copy()

    def save(self) -> None:
        self._stream.dump(self._data)

    def upsert(self, model: AbstractModel) -> Hashable:
        model_id, model_data = model.serialize()
        self._branch[model_id] = model_data
        return model_id

    def delete(self, keyid: Hashable) -> None:
        self.get_or_fail(keyid)
        self._branch.pop(keyid)

    def _find_data_by_field(self, field: Hashable, value) -> Optional[Any]:
        # Just be smart, use O(1) when we are looking for the id
        if field == self._id:
            return self._branch.get(value)

        for item in self._fetch_list():
            if item.get(field) == value:
                return item
        return None

    def _fetch_list(self) -> Iterable[Dict]:
        return self._branch.values()

    @property
    def _branch(self) -> Dict:
        if self._prefix not in self._data:
            self._data[self._prefix] = {}

        return self._data[self._prefix]
