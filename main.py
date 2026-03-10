import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.logging_config import setup_logging
from app.routes import (
    auth_routes,
    document_routes,
    email_routes,
    query_routes,
    request_history_routes,
)
from app.services.rag_service import rag_service
from app.services.document_service import document_service
from app.services.docker_manager import DockerManager
import app.models  # noqa: F401 — register models on Base.metadata

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Initialize Docker if in docker mode
    docker_manager = (
        DockerManager(
            docker_compose_path=settings.DOCKER_COMPOSE_PATH,
            project_name=settings.DOCKER_COMPOSE_PROJECT,
            mode=settings.LLM_MODE,
        )
        if settings.LLM_MODE == "docker"
        else None
    )

    try:
        if docker_manager:
            await docker_manager.start()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created.")

        await rag_service.initialize()
        await document_service.initialize()
        yield
    finally:
        if docker_manager:
            await docker_manager.stop()


app = FastAPI(
    title="RAG Model API",
    description="An API to query documents using a Retrieval-Augmented Generation model.",
    lifespan=lifespan,
)

@app.middleware("http")
async def log_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin:
        logger.info(f"Incoming request from origin: {origin} | Method: {request.method} | Path: {request.url.path}")
    return await call_next(request)

allowed_origins = [
    settings.FRONTEND_ORIGIN,
    settings.FRONTEND_ORIGIN.replace("localhost", "127.0.0.1"),
    settings.FRONTEND_ORIGIN.replace("127.0.0.1", "localhost"),
]
logger.info(f"CORS Allowed Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(query_routes.router)
app.include_router(document_routes.router)
app.include_router(request_history_routes.router)
app.include_router(email_routes.router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "Welcome to the RAG API. Use the /docs endpoint to see the API documentation."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
