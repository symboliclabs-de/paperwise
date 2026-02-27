from fastapi import FastAPI

from app.api.routes.v1.endpoints import router

app = FastAPI(title="paperwise")

app.include_router(router, prefix="/api/v1")
