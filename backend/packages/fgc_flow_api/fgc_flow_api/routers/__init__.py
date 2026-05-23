"""Routers for fgc_flow_api."""
from fgc_flow_api.routers.auth import router as auth_router
from fgc_flow_api.routers.jobs import router as jobs_router

__all__ = ["auth_router", "jobs_router"]
