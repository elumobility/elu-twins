from contextlib import asynccontextmanager
from fastapi import FastAPI

from elu.twin.backend.db.database import create_db_and_tables
from elu.twin.backend.routes.v1.public.user import router as user_router
from elu.twin.backend.routes.v1.public.token import router as token_router
from elu.twin.backend.routes.v1.public.charge_point import router as charge_point_router
from elu.twin.backend.routes.v1.public.vehicle import router as vehicle_router
from elu.twin.backend.routes.v1.public.charge_point_actions import (
    router as charge_point_actions_router,
)
from elu.twin.backend.routes.v1.public.ocpp_transaction import (
    router as transaction_router,
)
from elu.twin.backend import __version__
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import FileResponse, HTMLResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="elu twin - Public API",
    version=__version__,
    lifespan=lifespan,
    #    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="./elu/twin/backend/static"), name="static")


@app.get("/favicon.ico", response_class=FileResponse, include_in_schema=False)
async def read_favicon():
    favicon_path = Path("elu/twin/backend/static/favicon.ico")
    return FileResponse(favicon_path)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root():
    html_content = """
        <html>
            <head>
                <title>ELU twin - Public API</title>
                <link rel="icon" href="/static/favicon.ico" type="image/x-icon">
            </head>
            <body>
                <h1>Welcome to ELU twin - Public API</h1>
                <p>You can request early access <a href="https://www.elumobility.com/twins">here</a>.</p>
            </body>
        </html>
        """
    return HTMLResponse(content=html_content)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


routers = [
    user_router,
    token_router,
    charge_point_router,
    vehicle_router,
    charge_point_actions_router,
    transaction_router,
]

for router in routers:
    app.include_router(
        router,
    )
