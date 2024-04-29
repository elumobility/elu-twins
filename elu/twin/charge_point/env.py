"""Read configuration parameters"""

from os import environ


BACKEND_PRIVATE_URL = environ.get("BACKEND_PRIVATE_URL", "http://localhost:8001")
REDIS_HOSTNAME = environ.get("REDIS_HOSTNAME", "localhost")
REDIS_PORT = environ.get("REDIS_PORT", "6379")
REDIS_DB_ACTIONS = environ.get("REDIS_DB", "1")
REDIS_DB_CELERY = environ.get("REDIS_DB", "1")

CELERY_FACTORY_NAME = environ.get("CELERY_FACTORY_NAME", "celery_chargers_factory")

TOPIC_CONNECT_CP = "connect-charge-point"
TOPIC_DISCONNECT_CP = "disconnect-charge-point"

VID_PREFFIX = "VID:"
