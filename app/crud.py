from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from . import models, schemas
from .artic_client import validate_and_fetch_artwork


# ── helpers ───────────────────────────────────────────────────

def _sync_project_completion(project: models.Project) -> None:
    """Mark project completed when all places are visited."""
    if project.places and all(p.visited for p in project.places):
        project.is_completed = True
    else:
        project.is_completed = False


# ── projects ──────────────────────────────────────────────────

def get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def list_projects(db: Session) -> List[models.Project]:
    return db.query(models.Project).all()


def get_project(db: Session, project_id: int) -> models.Project:
    return get_project_or_404(db, project_id)


async def create_project(db: Session, data: schemas.ProjectCreate) -> models.Project:
    project = models.Project(
        name=data.name,
        description=data.description,
        start_date=data.start_date,
    )
    db.add(project)
    db.flush()  # get project.id without committing

    if data.places:
        if len(data.places) > 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A project cannot have more than 10 places",
            )
        seen_external_ids = set()
        for place_ref in data.places:
            if place_ref.external_id in seen_external_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Duplicate external_id {place_ref.external_id} in request",
                )
            seen_external_ids.add(place_ref.external_id)

            artwork = await validate_and_fetch_artwork(place_ref.external_id)
            if not artwork:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Artwork with id {place_ref.external_id} not found in Art Institute API",
                )
            db.add(models.ProjectPlace(project_id=project.id, **artwork))

    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, data: schemas.ProjectUpdate) -> models.Project:
    project = get_project_or_404(db, project_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> None:
    project = get_project_or_404(db, project_id)
    if any(p.visited for p in project.places):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a project that has visited places",
        )
    db.delete(project)
    db.commit()


# ── project places ────────────────────────────────────────────

def get_place_or_404(db: Session, project_id: int, place_id: int) -> models.ProjectPlace:
    place = (
        db.query(models.ProjectPlace)
        .filter(
            models.ProjectPlace.id == place_id,
            models.ProjectPlace.project_id == project_id,
        )
        .first()
    )
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return place


def list_places(db: Session, project_id: int) -> List[models.ProjectPlace]:
    get_project_or_404(db, project_id)
    return (
        db.query(models.ProjectPlace)
        .filter(models.ProjectPlace.project_id == project_id)
        .all()
    )


def get_place(db: Session, project_id: int, place_id: int) -> models.ProjectPlace:
    return get_place_or_404(db, project_id, place_id)


async def add_place(db: Session, project_id: int, data: schemas.ProjectPlaceCreate) -> models.ProjectPlace:
    project = get_project_or_404(db, project_id)

    current_count = len(project.places)
    if current_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Project already has the maximum of 10 places",
        )

    existing = (
        db.query(models.ProjectPlace)
        .filter(
            models.ProjectPlace.project_id == project_id,
            models.ProjectPlace.external_id == data.external_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This place is already in the project",
        )

    artwork = await validate_and_fetch_artwork(data.external_id)
    if not artwork:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Artwork with id {data.external_id} not found in Art Institute API",
        )

    place = models.ProjectPlace(project_id=project_id, **artwork)
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


def update_place(
    db: Session, project_id: int, place_id: int, data: schemas.ProjectPlaceUpdate
) -> models.ProjectPlace:
    place = get_place_or_404(db, project_id, place_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(place, key, value)

    project = place.project
    _sync_project_completion(project)

    db.commit()
    db.refresh(place)
    return place
