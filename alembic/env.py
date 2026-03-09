import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so Alembic can detect them
from app.db.database import Base
from app.models.user import User  # noqa
from app.models.store import Store, StoreSupervisorAssignment  # noqa
from app.models.token import RevokedToken  # noqa
from app.models.upload_job import UploadJob  # noqa
from app.models.sales import SalesKpi, MenuSales  # noqa
from app.models.customer import Customer, RfmSnapshot  # noqa
from app.models.alert import Alert  # noqa
from app.models.action import Action  # noqa
from app.models.campaign import Campaign  # noqa
from app.models.notice import Notice  # noqa
from app.models.visit_log import VisitLog  # noqa
from app.models.report import Report  # noqa
from app.models.agent_status import AgentStatus  # noqa
from app.models.escalation import Escalation  # noqa

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
