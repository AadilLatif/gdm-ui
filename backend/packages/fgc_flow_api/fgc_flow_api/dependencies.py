"""Auth dependencies for fgc_flow_api.

Wraps fgc_core's auth dependencies — no code duplication.
Protected endpoints in this package use these wrappers.
"""
from fgc_core.dependencies import get_admin_user, get_current_user

__all__ = ["get_current_user", "get_admin_user"]
