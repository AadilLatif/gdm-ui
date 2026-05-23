"""Routers for fgc_flow_api."""
from fgc_core.routers.auth import router as auth_router
from fgc_flow_api.routers.jobs import router as jobs_router
from fgc_flow_api.routers.models import router as models_router
from fgc_flow_api.routers.simulations import router as simulations_router

__all__ = ["auth_router", "jobs_router", "models_router", "simulations_router"]
