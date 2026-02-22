from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models so their metadata is registered on Base
from app.models.database import Base  # noqa: E402
from app.core.config import settings  # noqa: E402
import app.models.transaction  # noqa: F401,E402
import app.models.entity  # noqa: F401,E402

target_metadata = Base.metadata

# NOTE: We build the engine directly from settings rather than using
# config.set_main_option / engine_from_config, because configparser
# treats '%' as an interpolation character which breaks URL-encoded
# passwords (e.g. %40 for '@').


def run_migrations_offline() -> None:
    """Run migrations without an active database connection (generates SQL)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    kwargs = {"poolclass": pool.NullPool}
    if settings.DATABASE_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    connectable = create_engine(settings.DATABASE_URL, **kwargs)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
