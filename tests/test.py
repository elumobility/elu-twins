from fastapi.testclient import TestClient
from elu.twin.backend.app_private import app
from elu.twin.backend.db.database import get_session
from elu.twin.data.schemas.user import InputUser
import json
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
import pytest
from elu.twin.backend.env import (
    POSTGRES_USERNAME,
    POSTGRES_PASSWORD,
    POSTGRES_HOSTNAME,
    POSTGRES_PORT,
    POSTGRES_DB_NAME,
)


client = TestClient(app)


@pytest.fixture(name="session")
def session_fixture():
    db_kwargs = {
        "url": f"postgresql://{POSTGRES_USERNAME}:"
        f"{POSTGRES_PASSWORD}@{POSTGRES_HOSTNAME}:"
        f"{POSTGRES_PORT}/{POSTGRES_DB_NAME}"
    }

    engine = create_engine(**db_kwargs)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):

    def get_session_override():

        return session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create_user(client: TestClient):
    username = "niklas1@emobility.com"
    password = "Test1234"
    data = InputUser(username=username, password=password)
    j = data.model_dump()

    response = client.post("/user/", json=j)
    assert response.status_code == 200
