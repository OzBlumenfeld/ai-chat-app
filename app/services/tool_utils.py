import json
from typing import Annotated, Any

import pydantic
from pydantic import BeforeValidator
from pydantic_core import PydanticUndefined
from langchain_core.tools import BaseTool


def _coerce_str(v: Any) -> Any:
    """Coerce Ollama's malformed dict outputs back to plain strings.

    Ollama occasionally emits ``{'type': 'string', 'value': '...'}`` or ``{}``
    for parameters that the tool schema declares as ``str``.  This validator
    runs *before* Pydantic's type check so we can normalise those cases.
    """
    if not isinstance(v, dict):
        return v
    if "value" in v:
        return str(v["value"])
    return json.dumps(v) if v else ""


def patch_tools_for_ollama(tools: list[BaseTool]) -> list[BaseTool]:
    """Patch each tool's args_schema so string fields tolerate Ollama's dict outputs.

    Iterates over every tool's Pydantic model fields.  For any field whose
    annotation is ``str``, it replaces it with ``Annotated[str,
    BeforeValidator(_coerce_str)]`` so Pydantic coerces the value before
    running the normal type check.  Tools whose schemas have no string fields
    are left untouched.
    """
    for tool in tools:
        schema = tool.args_schema
        if schema is None or isinstance(schema, dict):
            continue

        field_defs: dict[str, Any] = {}
        needs_patch = False

        for fname, finfo in schema.model_fields.items():
            if finfo.annotation is str:
                needs_patch = True
                field_kwargs: dict[str, Any] = {}
                if finfo.default is not PydanticUndefined:
                    field_kwargs["default"] = finfo.default
                elif finfo.default_factory is not None:
                    field_kwargs["default_factory"] = finfo.default_factory
                if finfo.description:
                    field_kwargs["description"] = finfo.description
                field_defs[fname] = (
                    Annotated[str, BeforeValidator(_coerce_str)],
                    pydantic.Field(**field_kwargs),
                )
            else:
                field_defs[fname] = (finfo.annotation, finfo)

        if needs_patch:
            new_schema = pydantic.create_model(schema.__name__, **field_defs)
            object.__setattr__(tool, "args_schema", new_schema)

    return tools
