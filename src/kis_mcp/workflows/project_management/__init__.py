from .admission import register_project_management_admission_tool
from .descriptors import project_management_workflow_descriptors
from .enhanced_tools import register_project_management_enhancement_tools
from .parsing import (
    desired_projection_from_json,
    implementation_trace_from_json,
    observed_projection_from_json,
    traceability_stage,
    work_record_from_json,
)
from .tools import (
    register_project_management_tools as _register_project_management_tools,
)
from .triage_tools import register_project_management_triage_tool


def register_project_management_tools(server, service, *, activation_materializer=None) -> None:
    _register_project_management_tools(
        server,
        service,
        activation_materializer=activation_materializer,
    )
    register_project_management_enhancement_tools(server, service)


__all__ = [
    "desired_projection_from_json",
    "implementation_trace_from_json",
    "observed_projection_from_json",
    "project_management_workflow_descriptors",
    "register_project_management_admission_tool",
    "register_project_management_enhancement_tools",
    "register_project_management_tools",
    "register_project_management_triage_tool",
    "traceability_stage",
    "work_record_from_json",
]
