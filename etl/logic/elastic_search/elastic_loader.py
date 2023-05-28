import json
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, cast

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as es_bulk
from loguru import logger

from etl.logic.backoff.backoff import etl_backoff
from etl.logic.storage.storage import Storage
from etl.logic.transformer.dataclasses import ESBulkInt
from etl.settings.settings import ES_SCHEMAS_PATH


class ElasticSearchLoaderInt(ABC):
    schema: str
    index: str

    storage: Storage

    input_topic: str

    @abstractmethod
    def load_schema(self, client: Elasticsearch) -> None:
        ...

    @abstractmethod
    def load_bulk(self, client: Elasticsearch) -> None:
        ...


class BasicElasticSearchLoader(ElasticSearchLoaderInt):
    storage = Storage()

    def load_schema(self, client: Elasticsearch) -> None:
        index_schema: dict[str, Any]

        logger.info("loading ES schema")

        path_to_schema = ES_SCHEMAS_PATH.joinpath(self.schema).absolute()
        with open(path_to_schema, "r") as file:
            index_schema = json.load(file)

        client.options(ignore_status=400).indices.create(
            index=self.index, **index_schema
        )

    def load_bulk(self, client: Elasticsearch) -> None:
        es_data: list[ESBulkInt] = self.storage.get(self.input_topic)

        if not es_data:
            return

        data = es_data.pop()

        es_bulk(client, actions=data.to_actions(self.index))
        logger.info("Successfully loaded bulk")


class ElasticSearchMoviesLoader(BasicElasticSearchLoader):
    schema = "es_movies_schema.json"
    index = "movies"

    input_topic = "movies_es_data"


@lru_cache
def get_es_loaders() -> list[ElasticSearchLoaderInt]:
    es_loaders = [
        es_loader() for es_loader in BasicElasticSearchLoader.__subclasses__()
    ]
    return cast(list[ElasticSearchLoaderInt], es_loaders)


@etl_backoff()
def load_es_schemas(client: Elasticsearch) -> None:
    for es_loader in get_es_loaders():
        es_loader.load_schema(client)


@etl_backoff()
def run_es_loaders(client: Elasticsearch) -> None:
    for es_loader in get_es_loaders():
        es_loader.load_bulk(client)
