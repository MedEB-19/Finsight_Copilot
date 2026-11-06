from functools import lru_cache

from sqlalchemy import create_engine

from finsight.config import db_url


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(db_url(), pool_pre_ping=True)
