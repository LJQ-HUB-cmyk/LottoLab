from logging.config import fileConfig

from alembic import context
from lottolab.config import get_settings
from lottolab.db import Base, make_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
url = get_settings().database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:

    def migrate(connection):
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

    supplied = config.attributes.get("connection")
    if supplied is not None:
        migrate(supplied)
    else:
        engine = make_engine(url)
        try:
            with engine.connect() as connection:
                migrate(connection)
        finally:
            engine.dispose()
