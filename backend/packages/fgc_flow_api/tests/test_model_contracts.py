from __future__ import annotations

import sys
from pathlib import Path

CORE_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "fgc_core"
if str(CORE_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_PACKAGE_DIR))

from fgc_flow_api.database import FlowBase
from fgc_flow_api.models import Model
from fgc_flow_api.schemas import ModelListItem, ModelUploadRequest, ModelUploadResponse


def test_flow_model_table_definition():
    assert Model.__tablename__ == "model"
    assert "model" in FlowBase.metadata.tables


def test_model_columns():
    columns = set(Model.__table__.columns.keys())
    assert {"id", "user_id", "name", "file_path", "file_size", "created_at"} <= columns


def test_model_schema_fields():
    assert "name" in ModelUploadRequest.model_fields
    assert {"model_id", "name", "file_size", "created_at"} <= set(ModelUploadResponse.model_fields)
    assert {"model_id", "name", "file_size", "created_at"} <= set(ModelListItem.model_fields)
