import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from database import users_collection
from routes import auth

logger = logging.getLogger("auth-service")

app = FastAPI(title="Sports Store — Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")


@app.on_event("startup")
async def create_indexes():
    try:
        await users_collection.create_index("email", unique=True)
    except PyMongoError as exc:  # Mongo may be unavailable (e.g. unit tests)
        logger.warning("Index creation skipped: %s", exc)

    # Verify Redis connectivity
    try:
        from cache import redis_client
        redis_client.ping()
        logger.info("Redis connection verified.")
    except RedisError as exc:
        logger.warning("Redis is offline: %s", exc)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}
