from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.engine.system1 import get_decision_model
from app.storage import get_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_decision_model()  # load System 1 once at startup, falling back to keywords if it fails (§12)
    get_engine()  # create the assessments table if it does not exist
    yield


app = FastAPI(title="PRISM Engine API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
