import string
from random import choices


def generate_cid():
    # Generate random characters for X
    random_chars = "".join(choices(string.ascii_uppercase + string.digits, k=20))

    # Construct the final string
    random_string = f"ELU-{random_chars[:4]}-{random_chars[4:9]}-{random_chars[9:]}"

    return random_string


def generate_id_tag():
    # Generate random characters for X
    random_chars = "".join(choices(string.ascii_uppercase + string.digits, k=20))

    # Construct the final string
    random_string = f"{random_chars[:10]}"

    return random_string
