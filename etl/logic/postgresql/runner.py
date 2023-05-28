from typing import Iterator

from etl.logic.backoff.backoff import etl_backoff

from .client import PostgreClient
from .enrichers import run_enrichers
from .mergers import run_mergers
from .producers import run_producers


@etl_backoff()
def run_postgre_layers(pg_client: PostgreClient) -> Iterator[None]:
    with pg_client as client:
        run_producers(client.connection)
        run_enrichers(client.connection)
        yield from run_mergers(client.connection)
