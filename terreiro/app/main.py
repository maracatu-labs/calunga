import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache import close_redis
from app.config import settings
from app.database import close_pool, create_pool
from app.middleware import RateLimitMiddleware
from app.routers import auth, chats, deputados, exportacao, feed, feedback, health, metrics, senadores, suspeitas

# uvicorn only configures its own loggers; app-namespaced loggers default to
# WARNING, which silences operational signal (magic_link_sent, cache.hit,
# tool.calls, etc). Bring them up to INFO so prod log inspection actually
# shows what happened.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(logging.INFO)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_redis()
    await close_pool()

app = FastAPI(
    title="Terreiro — Maracatu API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(deputados.router)
app.include_router(senadores.router)
app.include_router(chats.router)
app.include_router(exportacao.router)
app.include_router(suspeitas.router)
app.include_router(feed.router)
app.include_router(feedback.router)
app.include_router(metrics.router)
