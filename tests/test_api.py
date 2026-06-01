"""
Test suite for the Travel Planner API.

All external Art Institute calls are mocked so tests run offline.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# ── in-memory test database ───────────────────────────────────

TEST_DB_URL = "sqlite:///./test_travel.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# ── fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


MOCK_ARTWORK_27992 = {
    "external_id": 27992,
    "title": "A Sunday on La Grande Jatte",
    "artist": "Georges Seurat",
    "image_url": "https://www.artic.edu/iiif/2/abc123/full/843,/0/default.jpg",
}

MOCK_ARTWORK_14598 = {
    "external_id": 14598,
    "title": "American Gothic",
    "artist": "Grant Wood",
    "image_url": "https://www.artic.edu/iiif/2/def456/full/843,/0/default.jpg",
}


def make_artic_mock(artwork_data):
    return AsyncMock(return_value=artwork_data)


# ── project tests ─────────────────────────────────────────────

class TestProjects:
    def test_list_projects_empty(self, client):
        r = client.get("/api/v1/projects")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_project_minimal(self, client):
        r = client.post("/api/v1/projects", json={"name": "Paris Trip"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Paris Trip"
        assert data["is_completed"] is False
        assert data["places"] == []

    def test_create_project_full(self, client):
        r = client.post(
            "/api/v1/projects",
            json={"name": "Chicago Art Tour", "description": "Visiting museums", "start_date": "2025-06-01"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["description"] == "Visiting museums"
        assert data["start_date"] == "2025-06-01"

    def test_create_project_with_places(self, client):
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            r = client.post(
                "/api/v1/projects",
                json={"name": "Art Tour", "places": [{"external_id": 27992}]},
            )
        assert r.status_code == 201
        data = r.json()
        assert len(data["places"]) == 1
        assert data["places"][0]["title"] == "A Sunday on La Grande Jatte"

    def test_create_project_name_required(self, client):
        r = client.post("/api/v1/projects", json={"description": "No name"})
        assert r.status_code == 422

    def test_create_project_with_invalid_artwork(self, client):
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(None)):
            r = client.post(
                "/api/v1/projects",
                json={"name": "Bad Places", "places": [{"external_id": 99999999}]},
            )
        assert r.status_code == 422

    def test_create_project_too_many_places(self, client):
        places = [{"external_id": i} for i in range(1, 12)]
        r = client.post("/api/v1/projects", json={"name": "Overloaded", "places": places})
        assert r.status_code == 422

    def test_create_project_duplicate_places_in_request(self, client):
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            r = client.post(
                "/api/v1/projects",
                json={"name": "Dupes", "places": [{"external_id": 27992}, {"external_id": 27992}]},
            )
        assert r.status_code == 422

    def test_get_project(self, client):
        create = client.post("/api/v1/projects", json={"name": "Rome"}).json()
        r = client.get(f"/api/v1/projects/{create['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "Rome"

    def test_get_project_not_found(self, client):
        r = client.get("/api/v1/projects/9999")
        assert r.status_code == 404

    def test_update_project(self, client):
        create = client.post("/api/v1/projects", json={"name": "Old Name"}).json()
        r = client.patch(f"/api/v1/projects/{create['id']}", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_update_project_not_found(self, client):
        r = client.patch("/api/v1/projects/9999", json={"name": "X"})
        assert r.status_code == 404

    def test_delete_project(self, client):
        create = client.post("/api/v1/projects", json={"name": "Temp"}).json()
        r = client.delete(f"/api/v1/projects/{create['id']}")
        assert r.status_code == 204
        assert client.get(f"/api/v1/projects/{create['id']}").status_code == 404

    def test_delete_project_with_visited_place_forbidden(self, client):
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            project = client.post(
                "/api/v1/projects",
                json={"name": "Art Tour", "places": [{"external_id": 27992}]},
            ).json()

        place_id = project["places"][0]["id"]
        client.patch(
            f"/api/v1/projects/{project['id']}/places/{place_id}",
            json={"visited": True},
        )

        r = client.delete(f"/api/v1/projects/{project['id']}")
        assert r.status_code == 409

    def test_list_projects_shows_place_count(self, client):
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            client.post(
                "/api/v1/projects",
                json={"name": "Art Tour", "places": [{"external_id": 27992}]},
            )
        r = client.get("/api/v1/projects")
        assert r.status_code == 200
        assert r.json()[0]["place_count"] == 1


# ── places tests ──────────────────────────────────────────────

class TestPlaces:
    def _make_project(self, client):
        return client.post("/api/v1/projects", json={"name": "Test Project"}).json()

    def test_add_place(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            r = client.post(
                f"/api/v1/projects/{project['id']}/places",
                json={"external_id": 27992},
            )
        assert r.status_code == 201
        assert r.json()["title"] == "A Sunday on La Grande Jatte"

    def test_add_place_not_in_api(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(None)):
            r = client.post(
                f"/api/v1/projects/{project['id']}/places",
                json={"external_id": 99999999},
            )
        assert r.status_code == 422

    def test_add_duplicate_place_rejected(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992})
            r = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992})
        assert r.status_code == 409

    def test_add_place_exceeds_limit(self, client):
        project = self._make_project(client)

        async def side_effect(eid):
            return {"external_id": eid, "title": f"Art {eid}", "artist": None, "image_url": None}

        with patch("app.crud.validate_and_fetch_artwork", side_effect=side_effect):
            for i in range(1, 11):
                r = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": i})
                assert r.status_code == 201

            r = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 11})
        assert r.status_code == 422

    def test_list_places(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992})
        r = client.get(f"/api/v1/projects/{project['id']}/places")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_get_place(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            place = client.post(
                f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992}
            ).json()
        r = client.get(f"/api/v1/projects/{project['id']}/places/{place['id']}")
        assert r.status_code == 200

    def test_get_place_not_found(self, client):
        project = self._make_project(client)
        r = client.get(f"/api/v1/projects/{project['id']}/places/9999")
        assert r.status_code == 404

    def test_update_place_notes(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            place = client.post(
                f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992}
            ).json()
        r = client.patch(
            f"/api/v1/projects/{project['id']}/places/{place['id']}",
            json={"notes": "Must visit on Sunday morning"},
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "Must visit on Sunday morning"

    def test_mark_place_visited(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            place = client.post(
                f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992}
            ).json()
        r = client.patch(
            f"/api/v1/projects/{project['id']}/places/{place['id']}",
            json={"visited": True},
        )
        assert r.status_code == 200
        assert r.json()["visited"] is True

    def test_all_visited_completes_project(self, client):
        project = self._make_project(client)
        with patch("app.crud.validate_and_fetch_artwork", make_artic_mock(MOCK_ARTWORK_27992)):
            place = client.post(
                f"/api/v1/projects/{project['id']}/places", json={"external_id": 27992}
            ).json()
        client.patch(
            f"/api/v1/projects/{project['id']}/places/{place['id']}",
            json={"visited": True},
        )
        r = client.get(f"/api/v1/projects/{project['id']}")
        assert r.json()["is_completed"] is True

    def test_partial_visited_does_not_complete_project(self, client):
        project = self._make_project(client)

        async def side_effect(eid):
            return {"external_id": eid, "title": f"Art {eid}", "artist": None, "image_url": None}

        with patch("app.crud.validate_and_fetch_artwork", side_effect=side_effect):
            p1 = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 1}).json()
            client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 2})

        client.patch(f"/api/v1/projects/{project['id']}/places/{p1['id']}", json={"visited": True})
        r = client.get(f"/api/v1/projects/{project['id']}")
        assert r.json()["is_completed"] is False
