from sqlmodel import SQLModel, create_engine, Session

from elu.twin.backend.env import (
    POSTGRES_USERNAME,
    POSTGRES_PASSWORD,
    POSTGRES_HOSTNAME,
    POSTGRES_PORT,
    POSTGRES_DB_NAME,
)

if POSTGRES_HOSTNAME:
    db_kwargs = {
        "url": f"postgresql://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOSTNAME}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}"
    }
else:
    sqlite_file_name = "database.db"
    connect_args = {"check_same_thread": False}
    db_kwargs = {
        "url": f"sqlite:///{sqlite_file_name}",
        "echo": True,
        "connect_args": connect_args,
    }


engine = create_engine(**db_kwargs)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
