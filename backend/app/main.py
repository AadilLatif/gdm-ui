from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, equipment, network, projects, scenarios, system, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _seed_admin()
    yield


async def _seed_admin():
    """Create the default admin user if it doesn't exist yet."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.user import User
    from app.services.auth_service import hash_password

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == settings.admin_username)
        )
        if result.scalar_one_or_none() is None:
            admin = User(
                email=f"{settings.admin_username}@gdmstudio.dev",
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                is_admin=True,
            )
            session.add(admin)
            await session.commit()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(system.router)
app.include_router(equipment.router)
app.include_router(network.router)
app.include_router(scenarios.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
