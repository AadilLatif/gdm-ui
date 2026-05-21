"""Service for loading and querying GDM DistributionSystem models."""

from __future__ import annotations

import importlib
import json
import tempfile
import typing
from pathlib import Path
from typing import Any, get_args, get_origin
from uuid import UUID

from gdm.distribution import DistributionSystem
from gdm.quantities import ureg
from infrasys.base_quantity import BaseQuantity


# Build a registry of type name -> class for equipment and components
def _build_type_registry() -> dict[str, type]:
    registry: dict[str, type] = {}
    for module_path in (
        "gdm.distribution.equipment",
        "gdm.distribution.components",
    ):
        mod = importlib.import_module(module_path)
        for name in dir(mod):
            obj = getattr(mod, name)
            if isinstance(obj, type) and name[0].isupper():
                registry[name] = obj
    return registry


TYPE_REGISTRY = _build_type_registry()


def _coerce_quantities(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Convert quantity fields from frontend format to pint Quantity objects.

    Handles:
      - strings like "12.47 kilovolt" -> Quantity(12.47, 'kilovolt')
      - dicts like {"value": 12.47, "unit": "kV"} -> Quantity(12.47, 'kV')
      - already-Quantity objects -> pass through
    """
    if not hasattr(cls, "model_fields"):
        return data

    result = dict(data)
    for field_name, field_info in cls.model_fields.items():
        if field_name not in result:
            continue
        val = result[field_name]
        if val is None:
            continue
        annotation = field_info.annotation
        if annotation is None:
            continue
        # Check if the field type is a BaseQuantity subclass
        # Handle Annotated[Quantity, ...] pattern
        actual_type = annotation
        if get_origin(annotation) is typing.Annotated:
            actual_type = get_args(annotation)[0]
        is_qty = isinstance(actual_type, type) and issubclass(actual_type, BaseQuantity)
        if not is_qty:
            continue
        if isinstance(val, BaseQuantity):
            continue  # Already a quantity
        if isinstance(val, dict) and "value" in val:
            unit = val.get("unit") or val.get("units") or ""
            result[field_name] = actual_type(float(val["value"]), unit) if unit else actual_type(float(val["value"]), actual_type.__base_unit__)
        elif isinstance(val, str) and " " in val:
            # String like "12.47 kilovolt"
            result[field_name] = ureg.Quantity(val)
        elif isinstance(val, (int, float)):
            # Bare number -> use base unit
            result[field_name] = actual_type(float(val), actual_type.__base_unit__)
    return result


class GDMService:
    """Manages loaded GDM systems in memory, keyed by project ID."""

    def __init__(self):
        self._systems: dict[str, DistributionSystem] = {}
        self._scenario_catalogs: dict[str, dict[str, DistributionSystem]] = {}  # project_id -> {filename: system}

    def load_system(self, project_id: str, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"System file not found: {file_path}")
        system = DistributionSystem.from_json(path)
        self._systems[project_id] = system
        return self.get_summary(project_id)

    def unload_system(self, project_id: str):
        self._systems.pop(project_id, None)

    def get_system(self, project_id: str) -> DistributionSystem:
        system = self._systems.get(project_id)
        if system is None:
            raise KeyError(f"System not loaded for project {project_id}")
        return system

    def get_summary(self, project_id: str) -> dict[str, Any]:
        system = self.get_system(project_id)
        component_types: dict[str, int] = {}
        total = 0
        for comp in system.iter_all_components():
            type_name = type(comp).__name__
            component_types[type_name] = component_types.get(type_name, 0) + 1
            total += 1

        return {
            "name": system.name,
            "uuid": str(system.uuid),
            "description": system.description,
            "total_components": total,
            "component_types": component_types,
        }

    def get_components_by_type(self, project_id: str, component_type: str) -> list[dict[str, Any]]:
        system = self.get_system(project_id)
        results = []
        for comp in system.iter_all_components():
            if type(comp).__name__ == component_type:
                results.append(self._serialize_component(comp))
        return results

    def get_component_by_uuid(self, project_id: str, uuid: str) -> dict[str, Any] | None:
        system = self.get_system(project_id)
        try:
            comp = system.get_component_by_uuid(UUID(uuid))
            return self._serialize_component(comp)
        except Exception:
            return None

    def get_all_components(self, project_id: str) -> list[dict[str, Any]]:
        system = self.get_system(project_id)
        return [self._serialize_component(comp) for comp in system.iter_all_components()]

    def get_topology(self, project_id: str) -> dict[str, Any]:
        system = self.get_system(project_id)
        graph = system.get_undirected_graph()
        nodes = []
        edges = []

        # Build name→uuid lookup for edge components
        name_to_uuid: dict[str, str] = {}
        for comp in system.iter_all_components():
            if hasattr(comp, "name") and hasattr(comp, "uuid"):
                name_to_uuid[comp.name] = str(comp.uuid)

        for node in graph.nodes(data=True):
            node_data = {"id": str(node[0]), **{k: str(v) for k, v in node[1].items()}}
            nodes.append(node_data)

        for u, v, data in graph.edges(data=True):
            edge_data = {"source": str(u), "target": str(v), **{k: str(v_) for k, v_ in data.items()}}
            edge_name = data.get("name", "")
            if edge_name and edge_name in name_to_uuid:
                edge_data["uuid"] = name_to_uuid[edge_name]
            edges.append(edge_data)

        return {"nodes": nodes, "edges": edges}

    def get_buses(self, project_id: str) -> list[dict[str, Any]]:
        from gdm.distribution.components import DistributionBus

        system = self.get_system(project_id)
        return [self._serialize_component(b) for b in system.get_components(DistributionBus)]

    def get_scenarios(self, project_id: str) -> list[dict[str, Any]]:
        from gdm.tracked_changes import TrackedChange

        return self.get_components_by_type(project_id, TrackedChange.__name__)

    # ===== Scenario catalog management =====

    def load_scenario_catalog(self, project_id: str, file_path: str, filename: str) -> dict[str, Any]:
        """Load a scenario zip as a catalog system."""
        from gdm.tracked_changes import TrackedChange

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
        catalog = DistributionSystem.from_json(path)
        if project_id not in self._scenario_catalogs:
            self._scenario_catalogs[project_id] = {}
        self._scenario_catalogs[project_id][filename] = catalog

        # Get scenario names
        tcs = list(catalog.get_components(TrackedChange))
        scenario_names = sorted(set(tc.scenario_name for tc in tcs if tc.scenario_name))
        return {
            "filename": filename,
            "scenario_names": scenario_names,
            "total_changes": len(tcs),
        }

    def list_scenario_files(self, project_id: str) -> list[dict[str, Any]]:
        """List all loaded scenario catalog files for a project."""
        from gdm.tracked_changes import TrackedChange

        catalogs = self._scenario_catalogs.get(project_id, {})
        result = []
        for filename, catalog in catalogs.items():
            tcs = list(catalog.get_components(TrackedChange))
            scenario_names = sorted(set(tc.scenario_name for tc in tcs if tc.scenario_name))
            result.append({
                "filename": filename,
                "scenario_names": scenario_names,
                "total_changes": len(tcs),
            })
        return result

    def get_scenario_timeline(self, project_id: str, filename: str, scenario_name: str) -> dict[str, Any]:
        """Get resolved timeline for a scenario — additions resolved to component summaries."""
        from gdm.tracked_changes import TrackedChange

        catalogs = self._scenario_catalogs.get(project_id, {})
        catalog = catalogs.get(filename)
        if catalog is None:
            raise ValueError(f"Scenario file not loaded: {filename}")

        tcs = [
            tc for tc in catalog.get_components(TrackedChange)
            if tc.scenario_name == scenario_name
        ]
        tcs.sort(key=lambda tc: tc.timestamp or "")

        # Also look up the base system for deletion/edit component info
        base_system = self._systems.get(project_id)

        steps = []
        for tc in tcs:
            # Resolve additions: look up component in catalog
            additions = []
            for uuid in tc.additions:
                try:
                    comp = catalog.get_component_by_uuid(uuid)
                    info: dict[str, Any] = {
                        "uuid": str(uuid),
                        "name": comp.name,
                        "type": type(comp).__name__,
                    }
                    # Include bus reference for node components
                    if hasattr(comp, "bus") and comp.bus is not None:
                        info["bus"] = comp.bus.name
                    elif hasattr(comp, "buses") and comp.buses:
                        info["bus1"] = comp.buses[0].name if comp.buses[0] else None
                        info["bus2"] = comp.buses[1].name if len(comp.buses) > 1 and comp.buses[1] else None
                    # Include coordinate for buses
                    if hasattr(comp, "coordinate") and comp.coordinate is not None:
                        info["coordinate"] = {"x": comp.coordinate.x, "y": comp.coordinate.y}
                    additions.append(info)
                except Exception:
                    additions.append({"uuid": str(uuid), "name": "Unknown", "type": "Unknown"})

            # Resolve deletions: look up component in base system
            deletions = []
            for uuid in tc.deletions:
                info = {"uuid": str(uuid), "name": "Unknown", "type": "Unknown"}
                if base_system:
                    try:
                        comp = base_system.get_component_by_uuid(uuid)
                        info["name"] = comp.name
                        info["type"] = type(comp).__name__
                    except Exception:
                        pass
                deletions.append(info)

            # Resolve edits
            edits = []
            for edit in tc.edits:
                edit_info: dict[str, Any] = {
                    "component_uuid": str(edit.component_uuid),
                    "field": edit.name,
                    "value": edit.value,
                    "component_name": "Unknown",
                    "component_type": "Unknown",
                }
                if base_system:
                    try:
                        comp = base_system.get_component_by_uuid(edit.component_uuid)
                        edit_info["component_name"] = comp.name
                        edit_info["component_type"] = type(comp).__name__
                    except Exception:
                        pass
                edits.append(edit_info)

            steps.append({
                "name": tc.name,
                "timestamp": tc.timestamp.isoformat() if tc.timestamp else None,
                "additions": additions,
                "deletions": deletions,
                "edits": edits,
            })

        return {
            "scenario_name": scenario_name,
            "filename": filename,
            "steps": steps,
        }

    def remove_scenario_catalog(self, project_id: str, filename: str) -> None:
        """Remove a loaded scenario catalog."""
        catalogs = self._scenario_catalogs.get(project_id, {})
        catalogs.pop(filename, None)

    def create_scenario_from_ops(
        self,
        project_id: str,
        scenario_name: str,
        ops: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a scenario catalog from tracked operations recorded in the Network UI."""
        from gdm.tracked_changes import TrackedChange, PropertyEdit
        from datetime import datetime as dt

        system = self.get_system(project_id)
        catalog = system.deepcopy()

        # Group ops by timestamp into TrackedChange steps
        steps: dict[str, dict[str, list]] = {}
        for op in ops:
            ts = op.get("timestamp", dt.now().isoformat())
            if ts not in steps:
                steps[ts] = {"additions": [], "deletions": [], "edits": []}
            if op["action"] == "addition":
                steps[ts]["additions"].append(UUID(op["uuid"]))
            elif op["action"] == "deletion":
                steps[ts]["deletions"].append(UUID(op["uuid"]))
            elif op["action"] == "edit":
                for field_name, value in (op.get("editedFields") or {}).items():
                    pe = PropertyEdit(
                        name=field_name,
                        value=value,
                        component_uuid=UUID(op["uuid"]),
                    )
                    catalog.add_component(pe)
                    steps[ts]["edits"].append(pe)

        for i, (ts, step_data) in enumerate(sorted(steps.items())):
            tc = TrackedChange(
                name=f"{scenario_name}_step_{i}",
                scenario_name=scenario_name,
                timestamp=dt.fromisoformat(ts),
                additions=step_data["additions"],
                deletions=step_data["deletions"],
                edits=step_data["edits"],
            )
            catalog.add_component(tc)

        filename = f"{scenario_name.replace(' ', '_')}.json"
        if project_id not in self._scenario_catalogs:
            self._scenario_catalogs[project_id] = {}
        self._scenario_catalogs[project_id][filename] = catalog

        return {
            "filename": filename,
            "scenario_names": [scenario_name],
            "total_changes": len(steps),
        }

    def apply_scenario(
        self, project_id: str, filename: str, scenario_name: str, timestamp: str | None = None
    ) -> DistributionSystem:
        """Apply tracked changes from a scenario to the base system and return the updated copy."""
        from gdm.tracked_changes import TrackedChange, apply_updates_to_system
        from datetime import datetime as dt

        system = self.get_system(project_id)
        catalogs = self._scenario_catalogs.get(project_id, {})
        catalog = catalogs.get(filename)
        if catalog is None:
            raise ValueError(f"Scenario file not loaded: {filename}")

        tcs = [
            tc for tc in catalog.get_components(TrackedChange)
            if tc.scenario_name == scenario_name
        ]
        if not tcs:
            raise ValueError(f"No tracked changes for scenario: {scenario_name}")

        system_date = dt.fromisoformat(timestamp) if timestamp else None
        updated = apply_updates_to_system(tcs, system, catalog, system_date=system_date)
        return updated

    def export_scenario_zip(
        self, project_id: str, filename: str, scenario_name: str,
        timestamp: str | None = None, name: str = "scenario_model",
    ) -> str:
        """Apply scenario then export as zip. Returns zip path."""
        import shutil
        import zipfile

        updated = self.apply_scenario(project_id, filename, scenario_name, timestamp)
        tmpdir = tempfile.mkdtemp()
        export_dir = Path(tmpdir) / name
        export_dir.mkdir()

        json_path = export_dir / f"{name}.json"
        updated.to_json(json_path)

        zip_path = Path(tmpdir) / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in export_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(export_dir))
        return str(zip_path)

    def save_scenario_as_project(
        self, project_id: str, filename: str, scenario_name: str,
        timestamp: str | None = None, dest_dir: str = "",
    ) -> str:
        """Apply scenario and save the resulting system to dest_dir. Returns json path."""
        updated = self.apply_scenario(project_id, filename, scenario_name, timestamp)
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        json_path = dest / "system.json"
        updated.to_json(json_path)
        return str(json_path)

    def export_system_json(self, project_id: str) -> dict[str, Any]:
        system = self.get_system(project_id)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "export.json"
            system.to_json(out_path)
            return json.loads(out_path.read_text())

    def export_system_zip(self, project_id: str, name: str = "system") -> str:
        """Export the system to a zip file and return the path."""
        import shutil
        import zipfile

        system = self.get_system(project_id)
        tmpdir = tempfile.mkdtemp()
        export_dir = Path(tmpdir) / name
        export_dir.mkdir()

        json_path = export_dir / f"{name}.json"
        system.to_json(json_path)

        zip_path = Path(tmpdir) / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in export_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(export_dir))
        return str(zip_path)

    def _serialize_component(self, comp: Any) -> dict[str, Any]:
        """Convert a pydantic component to a JSON-safe dict."""
        data = comp.model_dump(mode="json")
        data["_type"] = type(comp).__name__
        data["uuid"] = str(comp.uuid)
        return data

    # ===== CRUD operations =====

    def _resolve_references(self, system: DistributionSystem, cls: type, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve string references (bus names, equipment names/UUIDs) to actual component objects."""
        import types as _types
        from gdm.distribution.components import DistributionBus
        from infrasys import Component

        resolved = dict(data)
        if not hasattr(cls, "model_fields"):
            return resolved

        for field_name, field_info in cls.model_fields.items():
            if field_name not in resolved:
                continue
            val = resolved[field_name]
            if val is None or not isinstance(val, (str, list)):
                continue

            annotation = field_info.annotation
            if annotation is None:
                continue
            actual_type = annotation
            if get_origin(annotation) is typing.Annotated:
                actual_type = get_args(annotation)[0]

            # Unwrap Optional / X | None union types to the concrete type
            origin = get_origin(actual_type)
            if origin is typing.Union or isinstance(actual_type, _types.UnionType):
                args = get_args(actual_type)
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    actual_type = non_none[0]

            # Handle single component ref: str -> lookup by name or UUID
            if isinstance(actual_type, type) and issubclass(actual_type, Component) and isinstance(val, str):
                if actual_type is DistributionBus:
                    resolved[field_name] = system.get_component(DistributionBus, val)
                else:
                    try:
                        resolved[field_name] = system.get_component_by_uuid(UUID(val))
                    except Exception:
                        try:
                            resolved[field_name] = system.get_component(actual_type, val)
                        except Exception:
                            pass  # Leave as-is; model_validate will produce a clear error

            # Handle list of component refs: list[str] -> list[Component]
            elif get_origin(actual_type) is list and isinstance(val, list):
                inner = get_args(actual_type)
                if inner and isinstance(inner[0], type) and issubclass(inner[0], Component):
                    ref_type = inner[0]
                    resolved[field_name] = [
                        (system.get_component(ref_type, v) if isinstance(v, str) else v)
                        for v in val
                    ]

        return resolved

    def add_component(self, project_id: str, type_name: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new component from type name + field data and add to system."""
        from infrasys.location import Location

        cls = TYPE_REGISTRY.get(type_name)
        if cls is None:
            raise ValueError(f"Unknown component type: {type_name}")
        system = self.get_system(project_id)
        coerced = _coerce_quantities(cls, data)
        resolved = self._resolve_references(system, cls, coerced)
        component = cls.model_validate(resolved)
        # Add composed sub-components (e.g. Location) to system first
        if hasattr(component, "coordinate") and component.coordinate is not None:
            system.add_component(component.coordinate)
        system.add_component(component)
        return self._serialize_component(component)

    def update_component(self, project_id: str, uuid: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update fields on an existing component in-place."""
        system = self.get_system(project_id)
        component = system.get_component_by_uuid(UUID(uuid))
        cls = type(component)
        coerced = _coerce_quantities(cls, data)
        for key, value in coerced.items():
            if key in ("_type", "uuid"):
                continue
            if hasattr(component, key):
                setattr(component, key, value)
        return self._serialize_component(component)

    def delete_component(self, project_id: str, uuid: str) -> None:
        """Remove a component from the system."""
        system = self.get_system(project_id)
        component = system.get_component_by_uuid(UUID(uuid))
        system.remove_component(component)


# Singleton instance
gdm_service = GDMService()
