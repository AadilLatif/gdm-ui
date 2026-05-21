# GDM Studio Backend

FastAPI backend for the GDM Studio application — a web UI for working with grid-data-models `DistributionSystem` objects.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# If grid-data-models is a local package:
pip install -e /path/to/grid-data-models
```

## Run

```bash
python run.py
```

Server starts at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

## API Overview

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Current user info |

### Users (admin)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/` | List all users |
| GET | `/api/users/{id}` | Get user |
| PATCH | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Delete user |

### Projects (model management)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/upload` | Upload model zip |
| GET | `/api/projects/` | List user's models |
| GET | `/api/projects/{id}` | Get project details |
| POST | `/api/projects/{id}/select` | Set as active model |
| PATCH | `/api/projects/{id}` | Update project metadata |
| DELETE | `/api/projects/{id}` | Delete project |

### System (active model)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system/summary` | System summary |
| GET | `/api/system/components` | List components (optionally filtered by `?component_type=`) |
| GET | `/api/system/components/{uuid}` | Get single component |
| GET | `/api/system/export` | Export full system JSON |

### Equipment
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/equipment/categories` | List equipment categories |
| GET | `/api/equipment/` | List equipment (optionally filtered by `?category=`) |
| GET | `/api/equipment/{uuid}` | Get equipment item |

### Network
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/network/topology` | Graph nodes & edges |
| GET | `/api/network/buses` | List buses |

### Scenarios
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scenarios/` | List tracked changes |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
