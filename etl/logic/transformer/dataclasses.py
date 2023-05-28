from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel, Field, validator

ESBulkType = TypeVar("ESBulkType")


class SQLContainerInt(ABC, Generic[ESBulkType]):
    @abstractmethod
    def __init__(self, batch: list) -> None:
        ...

    @abstractmethod
    def transform(self) -> ESBulkType:
        ...


class ESBulkInt(ABC):
    @abstractmethod
    def to_actions(self, index: str) -> list[dict]:
        ...


class Roles(Enum):
    ACTOR = "actor"
    DIRECTOR = "director"
    WRITTER = "writer"


class ESPerson(BaseModel):
    person_id: str = Field(alias="id")
    name: str


class ESMoviesDoc(BaseModel):
    movies_id: str = Field(alias="id")
    imdb_rating: float | None
    genre: list[str]
    title: str
    description: str | None
    director: list[str]
    actors_names: list[str]
    writers_names: list[str]
    actors: list[ESPerson]
    writers: list[ESPerson]


class ESIndexTemplate(BaseModel):
    _index: str
    _id: str


class ESBulk(BaseModel, ESBulkInt):
    bulk: list[ESMoviesDoc]

    def to_actions(self, index: str) -> list[dict]:
        actions: list[dict] = []
        for doc in self.bulk:
            actions.append(
                {
                    "_id": doc.movies_id,
                    "_index": index,
                    **doc.dict(by_alias=True),
                }
            )

        return actions


class Person(BaseModel):
    person_id: UUID
    person_name: str
    person_role: Roles


class Movie(BaseModel):
    film_id: UUID = Field(alias="id")
    title: str
    description: str | None
    rating: float | None
    film_type: str = Field(alias="type")
    created: datetime
    modified: datetime
    genres: list
    persons: list[Person]

    @validator("genres")
    @classmethod
    def convert_genres(cls, value: list) -> list[str]:
        if not all(value):
            return [""]

        return cast(list[str], value)

    def transform_to_es_doc(self) -> ESMoviesDoc:
        def get_persons_by(role: Roles) -> list[ESPerson]:
            return [
                ESPerson(id=str(i.person_id), name=i.person_name)
                for i in self.persons
                if i.person_role == role
            ]

        actors = get_persons_by(Roles.ACTOR)
        writers = get_persons_by(Roles.WRITTER)
        directors = get_persons_by(Roles.DIRECTOR)

        actors_names = [i.name for i in actors]
        writers_names = [i.name for i in writers]
        directors_names = [i.name for i in directors]

        es_index = ESMoviesDoc(
            id=str(self.film_id),
            imdb_rating=self.rating,
            genre=self.genres,
            title=self.title,
            description=self.description,
            director=directors_names,
            actors_names=actors_names,
            writers_names=writers_names,
            actors=actors,
            writers=writers,
        )

        return es_index


class MoviesContainer(BaseModel, SQLContainerInt[ESBulk]):
    batch: list[Movie]

    def transform(self) -> ESBulk:
        es_indexes = [i.transform_to_es_doc() for i in self.batch]
        return ESBulk(bulk=es_indexes)
