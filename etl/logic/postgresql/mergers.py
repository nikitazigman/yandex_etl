from abc import ABC, abstractmethod
from functools import lru_cache
from itertools import chain, zip_longest
from typing import Iterator, cast

from loguru import logger
from psycopg2._psycopg import connection as pg_connection

from etl.logic.storage.storage import Storage


class MergerInt(ABC):
    storage: Storage
    input_topic: str
    output_topic: str
    table: str

    @abstractmethod
    def merge(self, connection: pg_connection) -> Iterator[None]:
        ...


class BaseMerger(MergerInt):
    storage = Storage()
    batch_size = 50

    def get_query(self) -> str:
        query = f"""
        --sql
        SELECT
            fw.id,
            fw.title,
            fw.description,
            fw.rating,
            fw.type,
            fw.created,
            fw.modified,
            ARRAY_AGG (DISTINCT g.name) as genres,
            COALESCE (
                JSON_AGG(
                    DISTINCT jsonb_build_object(
                        'person_role', pfw.role,
                        'person_id', p.id,
                        'person_name', p.full_name
                    )
                ) FILTER (WHERE p.id is not null),
                '[]'
            ) as persons
        FROM {self.table} as fw
        LEFT JOIN content.person_film_work pfw ON pfw.film_work_id = fw.id
        LEFT JOIN content.person p ON p.id = pfw.person_id
        LEFT JOIN content.genre_film_work gfw ON gfw.film_work_id = fw.id
        LEFT JOIN content.genre g ON g.id = gfw.genre_id
        WHERE fw.id IN %s
        GROUP BY fw.id
        ORDER BY fw.modified
        ;
        """
        return query

    def merge(self, connection: pg_connection) -> Iterator[None]:
        query = self.get_query()
        films_ids = self.storage.get(self.input_topic)

        if not films_ids:
            return []

        unique_film_ids = tuple(set(chain(*films_ids)))
        with connection.cursor() as cursor:
            cursor.execute(query, vars=(unique_film_ids,))
            while film_data := cursor.fetchmany(size=self.batch_size):
                logger.debug(
                    f"Retrieved {len(film_data)} rows"
                    f" from `{self.table}` table"
                )
                self.storage.set(self.output_topic, film_data)
                yield None


class MoviesMerger(BaseMerger):
    input_topic = "film_ids"
    output_topic = "movies_sql_data"

    table = "content.film_work"


@lru_cache
def get_mergers() -> list[MergerInt]:
    mergers = [merger() for merger in BaseMerger.__subclasses__()]
    return cast(list[MergerInt], mergers)


def run_mergers(connection: pg_connection) -> Iterator[None]:
    mergers = get_mergers()
    yield from zip_longest(*[merger.merge(connection) for merger in mergers])