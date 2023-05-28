from abc import ABC, abstractmethod
from functools import lru_cache
from typing import cast
from uuid import UUID

from loguru import logger
from psycopg2._psycopg import connection as pg_connection

from etl.logic.storage.storage import Storage


class ProducerInt(ABC):
    table: str
    input_topic: str
    output_topic: str
    storage: Storage

    @abstractmethod
    def produce(self, connection: pg_connection) -> None:
        ...


class BaseProducer(ProducerInt):
    batch_size = 30
    storage = Storage()
    input_topic = "last_checkup"

    def get_query(self) -> str:
        query = f"""
        --sql
        SELECT id FROM {self.table}
        WHERE modified > (%s)
        ORDER BY modified
        ;
        """
        return query

    def produce(self, connection: pg_connection) -> None:
        logger.debug("Getting modified ids from the last checkup")
        last_checkup = self.storage.get(self.input_topic)[0]

        query = self.get_query()
        with connection.cursor() as cursor:
            cursor.execute(query, vars=(last_checkup,))

            response = cursor.fetchall()
            logger.debug(
                f"Retrieved {len(response)} ids from `{self.table}` table"
            )
            producer_ids = [res["id"] for res in response]

        if producer_ids:
            self.storage.set(self.output_topic, producer_ids)


class PersonProducer(BaseProducer):
    table = "content.person"
    output_topic = "person_ids"


class GenreProducer(BaseProducer):
    table = "content.genre"
    output_topic = "genre_ids"


class FilmWorkProducer(BaseProducer):
    table = "content.film_work"
    output_topic = "film_ids"


@lru_cache
def get_producers() -> list[ProducerInt]:
    producers = [producer() for producer in BaseProducer.__subclasses__()]
    return cast(list[ProducerInt], producers)


def run_producers(connection: pg_connection) -> None:
    for producer in get_producers():
        producer.produce(connection)
