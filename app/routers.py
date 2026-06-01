from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from . import crud, schemas
from .database import get_db

router = APIRouter()


# ── Projects ──────────────────────────────────────────────────

@router.get("/projects", response_model=List[schemas.ProjectListResponse], tags=["Projects"])
def list_projects(db: Session = Depends(get_db)):
    """List all travel projects."""
    projects = crud.list_projects(db)
    return [
        schemas.ProjectListResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            start_date=p.start_date,
            is_completed=p.is_completed,
            place_count=len(p.places),
        )
        for p in projects
    ]


@router.post("/projects", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED, tags=["Projects"])
async def create_project(data: schemas.ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new travel project, optionally seeding it with artworks from the
    Art Institute of Chicago API.
    """
    return await crud.create_project(db, data)


@router.get("/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a single travel project with all its places."""
    return crud.get_project(db, project_id)


@router.patch("/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def update_project(project_id: int, data: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    """Update project metadata (name, description, start_date)."""
    return crud.update_project(db, project_id, data)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project. Fails with 409 if any place has been marked as visited.
    """
    crud.delete_project(db, project_id)


# ── Project Places ─────────────────────────────────────────────

@router.get("/projects/{project_id}/places", response_model=List[schemas.ProjectPlaceResponse], tags=["Places"])
def list_places(project_id: int, db: Session = Depends(get_db)):
    """List all places within a project."""
    return crud.list_places(db, project_id)


@router.post(
    "/projects/{project_id}/places",
    response_model=schemas.ProjectPlaceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Places"],
)
async def add_place(project_id: int, data: schemas.ProjectPlaceCreate, db: Session = Depends(get_db)):
    """
    Add an artwork from the Art Institute of Chicago API to a project.
    Validates existence, uniqueness, and the 10-place limit.
    """
    return await crud.add_place(db, project_id, data)


@router.get("/projects/{project_id}/places/{place_id}", response_model=schemas.ProjectPlaceResponse, tags=["Places"])
def get_place(project_id: int, place_id: int, db: Session = Depends(get_db)):
    """Get a single place within a project."""
    return crud.get_place(db, project_id, place_id)


@router.patch("/projects/{project_id}/places/{place_id}", response_model=schemas.ProjectPlaceResponse, tags=["Places"])
def update_place(
    project_id: int,
    place_id: int,
    data: schemas.ProjectPlaceUpdate,
    db: Session = Depends(get_db),
):
    """Update notes or mark a place as visited. Completing all places completes the project."""
    return crud.update_place(db, project_id, place_id, data)
