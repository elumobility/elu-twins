from fastapi.testclient import TestClient
from elu.twin.backend.app_private import app
from elu.twin.data.schemas.user import InputUser
import json


client = TestClient(app)


def test_create_user():
    username = "niklas@emobility.com"
    password = "Test1234"
    data = InputUser(username=username, password=password)
    # j = json.dumps(data)
    j = data.model_dump()

    response = client.post("/user/", json=j)
    assert response.status_code == 200
    # assert response.json() == {
    #     "Status": "Success",
    #     "User": {
    #         "first_name": "PLACEHOLDER",
    #         "last_name": "PLACEHOLDER",
    #         "activated": False,
    #         "createdAt": "2023-03-17T00:04:32",
    #         "id": user_id,
    #         "address": "PLACEHOLDER",
    #         "updatedAt": None,
    #     },
    # }
