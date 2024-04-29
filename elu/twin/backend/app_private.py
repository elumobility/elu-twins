from contextlib import asynccontextmanager
from fastapi import FastAPI

from elu.twin.backend.db.database import create_db_and_tables
from elu.twin.backend.routes.v1.private.vehicle import router as vehicle_router
from elu.twin.backend.routes.v1.private.charge_point_ocpp import router as ocpp_router
from elu.twin.backend.routes.v1.private.quota import router as quota_router
from elu.twin.backend import __version__
from elu.twin.backend.routes.v1.private.user import router as user_router
from elu.twin.backend.routes.v1.private.ocpp_transaction import (
    router as transaction_router,
)
from elu.twin.backend.routes.v1.private.charge_point_actions import (
    router as charge_point_actions_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="elu-twin. Private API. This API is only for internal usage of OCPP protocol.",
    version=__version__,
    lifespan=lifespan,
)

routers = [
    user_router,
    vehicle_router,
    ocpp_router,
    quota_router,
    transaction_router,
    charge_point_actions_router,
]

for router in routers:
    app.include_router(
        router,
    )
