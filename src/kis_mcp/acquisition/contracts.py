from __future__ import annotations

REGISTERED_ACQUISITION_OPERATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "project": {
            "type": "string",
            "pattern": r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
        },
        "profile": {
            "type": "string",
            "pattern": r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
        },
        "recipe": {
            "type": "string",
            "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
        },
        "recipe_hash": {
            "type": "string",
            "pattern": r"^sha256:[0-9a-f]{64}$",
        },
        "parameters": {
            "type": "object",
            "maxProperties": 16,
            "propertyNames": {
                "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
            },
            "additionalProperties": {
                "oneOf": [
                    {"type": ["string", "number", "boolean"]},
                    {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 64,
                        "items": {"type": ["string", "number", "boolean"]},
                    },
                ],
            },
        },
        "approved": {"type": "boolean"},
    },
    "required": [
        "project",
        "profile",
        "recipe",
        "recipe_hash",
        "parameters",
        "approved",
    ],
}

__all__ = ["REGISTERED_ACQUISITION_OPERATION_SCHEMA"]
