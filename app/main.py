from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import router

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Travel Planner API",
    description=(
        "A CRUD API for managing travel projects and places sourced from the "
        "Art Institute of Chicago collection."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "docs": "/docs"}
