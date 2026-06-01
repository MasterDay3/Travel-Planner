from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date


# ── Place schemas ──────────────────────────────────────────────

class PlaceImport(BaseModel):
    """Reference to an artwork from the Art Institute of Chicago API."""
    external_id: int = Field(..., description="Artwork ID from the Art Institute of Chicago API")


class ProjectPlaceCreate(BaseModel):
    external_id: int


class ProjectPlaceUpdate(BaseModel):
    notes: Optional[str] = None
    visited: Optional[bool] = None


class ProjectPlaceResponse(BaseModel):
    id: int
    project_id: int
    external_id: int
    title: str
    artist: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None
    visited: bool

    model_config = {"from_attributes": True}


# ── Project schemas ────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    places: Optional[List[PlaceImport]] = Field(default=None, max_length=10)

    @field_validator("places")
    @classmethod
    def places_not_empty_if_provided(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("places list must have at least 1 item if provided")
        if v is not None and len(v) > 10:
            raise ValueError("A project cannot have more than 10 places")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    is_completed: bool
    places: List[ProjectPlaceResponse] = []

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    is_completed: bool
    place_count: int

    model_config = {"from_attributes": True}
