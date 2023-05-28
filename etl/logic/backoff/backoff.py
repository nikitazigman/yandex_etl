from functools import partial

import backoff
from elasticsearch.exceptions import ConnectionError
from psycopg2.errors import OperationalError

from etl.settings.settings import SystemSettings

system_settings = SystemSettings()

backoff_expo = partial(
    backoff.expo,
    base=2,
    factor=system_settings.factor,
    max_value=system_settings.max_value,
)

etl_backoff = partial(
    backoff.on_exception,
    backoff_expo,
    (ConnectionError, OperationalError),
)
