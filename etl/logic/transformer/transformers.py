from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Type, cast

from etl.logic.storage.storage import Storage

from .dataclasses import ESBulk, MoviesContainer, SQLContainerInt


class TransformerInt(ABC):
    dataclass: Type[SQLContainerInt]

    input_topic: str
    output_topic: str

    storage: Storage

    @abstractmethod
    def transform(self) -> None:
        ...


class BaseTrasformer(TransformerInt):
    storage = Storage()

    def transform(self) -> None:
        sql_data = self.storage.get(self.input_topic)
        if not sql_data:
            return
        es_data = self.dataclass(batch=sql_data.pop())
        self.storage.set(self.output_topic, es_data.transform())


class MoviesTransformer(BaseTrasformer):
    dataclass = MoviesContainer

    input_topic = "movies_sql_data"
    output_topic = "movies_es_data"


@lru_cache
def get_transformers() -> list[TransformerInt]:
    mergers = [merger() for merger in BaseTrasformer.__subclasses__()]
    return cast(list[TransformerInt], mergers)


def run_transformers() -> None:
    for transformer in get_transformers():
        transformer.transform()
