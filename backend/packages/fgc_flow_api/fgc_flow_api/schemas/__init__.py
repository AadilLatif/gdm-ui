"""Pydantic request/response schemas for fgc_flow_api."""

from fgc_core.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from fgc_flow_api.schemas.error import ErrorResponse
from fgc_flow_api.schemas.jobs import (
    JobResultResponse,
    JobStatusResponse,
    JobSubmissionRequest,
    JobSubmissionResponse,
)
from fgc_flow_api.schemas.models import (
    ModelListItem,
    ModelListResponse,
    ModelResponse,
    ModelUploadRequest,
    ModelUploadResponse,
)
from fgc_flow_api.schemas.simulations import (
    ACSolverConfig,
    DCSolverConfig,
    LinDistFlowConfig,
    SimulationBatchRequest,
    SimulationBatchResponse,
    SimulationCompareRequest,
    SimulationCompareResponse,
    SimulationDispatchResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationSolverName,
    SolverConfig,
)

__all__ = [
    "ACSolverConfig",
    "DCSolverConfig",
    "ErrorResponse",
    "JobResultResponse",
    "JobStatusResponse",
    "JobSubmissionRequest",
    "JobSubmissionResponse",
    "LinDistFlowConfig",
    "LoginRequest",
    "ModelListItem",
    "ModelListResponse",
    "ModelResponse",
    "ModelUploadRequest",
    "ModelUploadResponse",
    "RefreshRequest",
    "RegisterRequest",
    "SimulationBatchRequest",
    "SimulationBatchResponse",
    "SimulationCompareRequest",
    "SimulationCompareResponse",
    "SimulationDispatchResponse",
    "SimulationRequest",
    "SimulationResponse",
    "SimulationSolverName",
    "SolverConfig",
    "TokenResponse",
]
