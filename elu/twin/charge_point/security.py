from base64 import b64encode


def basic_auth_header(username: str, password: str):
    """

    :param username:
    :param password:
    :return:
    """
    assert ":" not in username
    user_pass = f"{username}:{password}"
    basic_credentials = b64encode(user_pass.encode()).decode()
    return "Authorization", f"Basic {basic_credentials}"
