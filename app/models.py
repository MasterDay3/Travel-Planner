from sqlalchemy import Column, Integer, String, Boolean, Date, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)

    places = relationship("ProjectPlace", back_populates="project", cascade="all, delete-orphan")


class ProjectPlace(Base):
    __tablename__ = "project_places"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    artist = Column(String(500), nullable=True)
    image_url = Column(String(1000), nullable=True)
    notes = Column(Text, nullable=True)
    visited = Column(Boolean, default=False)

    project = relationship("Project", back_populates="places")

    __table_args__ = (
        UniqueConstraint("project_id", "external_id", name="uq_project_external"),
    )
