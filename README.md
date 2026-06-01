# Travel Planner API

A RESTful CRUD API for managing travel projects and places sourced from the
[Art Institute of Chicago](https://api.artic.edu/docs/) public API.

Built with **FastAPI**, **SQLAlchemy**, and **SQLite**.

---

## Setup

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload
```

The API is now available at **http://localhost:8000**.  
Interactive docs: **http://localhost:8000/docs**

---

## Running tests

```bash
pytest tests/ -v
```

---

## Project structure

```
travel_planner/
├── app/
│   ├── main.py          # FastAPI app + startup
│   ├── database.py      # SQLAlchemy engine & session
│   ├── models.py        # ORM models (Project, ProjectPlace)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── crud.py          # Business logic / DB operations
│   ├── routers.py       # API route handlers
│   └── artic_client.py  # Art Institute of Chicago HTTP client
├── tests/
│   └── test_api.py      # 26 integration tests (all external calls mocked)
├── requirements.txt
└── README.md
```

---

## API endpoints

### Projects

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/projects` | List all projects |
| `POST` | `/api/v1/projects` | Create a project (optionally with places) |
| `GET` | `/api/v1/projects/{id}` | Get a single project |
| `PATCH` | `/api/v1/projects/{id}` | Update project metadata |
| `DELETE` | `/api/v1/projects/{id}` | Delete project (blocked if any place is visited) |

### Places

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/projects/{id}/places` | List places in a project |
| `POST` | `/api/v1/projects/{id}/places` | Add a place (validated against Art Institute API) |
| `GET` | `/api/v1/projects/{id}/places/{pid}` | Get a single place |
| `PATCH` | `/api/v1/projects/{id}/places/{pid}` | Update notes / mark as visited |

---

## Key business rules

- A project holds **1–10 places**.
- The same external artwork cannot appear twice in the same project.
- Every place is validated against the Art Institute of Chicago API before being stored.
- **Deleting a project** is blocked if any of its places have been marked as `visited`.
- When **all places** in a project are marked as `visited`, the project is automatically
  set to `is_completed = true`.

---

## Example: create a project with artworks

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chicago Art Tour",
    "description": "Iconic works at the Art Institute",
    "start_date": "2025-09-01",
    "places": [
      {"external_id": 27992},
      {"external_id": 14598}
    ]
  }'
```

*Artwork IDs can be discovered via the Art Institute search endpoint:*
`GET https://api.artic.edu/api/v1/artworks/search?q=monet&limit=5`
