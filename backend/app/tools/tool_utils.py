import inspect
import re
import types
import typing

_PYTHON_TO_JSON_TYPE: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _resolve_json_type(annotation: object) -> str:
    """Resolve a Python annotation to a JSON Schema type."""
    origin = typing.get_origin(annotation)
    if origin is not None:
        if origin in (typing.Union, types.UnionType):
            for argument in typing.get_args(annotation):
                if argument is not type(None):
                    return _resolve_json_type(argument)
        return _PYTHON_TO_JSON_TYPE.get(origin, "string")
    return _PYTHON_TO_JSON_TYPE.get(annotation, "string")


def _schema_for_annotation(annotation: object) -> dict[str, object]:
    """Build a minimal JSON Schema for an annotation."""
    schema: dict[str, object] = {"type": _resolve_json_type(annotation)}
    if schema["type"] == "array":
        arguments = typing.get_args(annotation)
        if arguments:
            schema["items"] = _schema_for_annotation(arguments[0])
    return schema


def _parse_google_docstring(docstring: str) -> tuple[str, dict[str, str]]:
    """Parse a Google-style docstring."""
    if not docstring:
        return "", {}

    parts = re.split(r"^\s*Args\s*:\s*$", docstring, maxsplit=1, flags=re.M)
    description = inspect.cleandoc(parts[0]).strip()
    description = re.split(
        r"^\s*(?:Returns?|Raises?|Yields?)\s*:\s*$",
        description,
        maxsplit=1,
        flags=re.M,
    )[0].strip()
    if len(parts) < 2:
        return description, {}

    args_text = re.split(
        r"^\s*(?:Returns?|Raises?|Yields?)\s*:\s*$",
        parts[1],
        maxsplit=1,
        flags=re.M,
    )[0]
    parameter_descriptions: dict[str, str] = {}
    for match in re.finditer(
        r"^\s+(\w+)\s*(\([^)]*\))?\s*:\s*(.+)$", args_text, re.M
    ):
        parameter_descriptions[match.group(1)] = match.group(3).strip()
    return description, parameter_descriptions


def tools_from_functions(
    functions: list[typing.Callable[..., str]],
) -> tuple[list[dict[str, object]], dict[str, typing.Callable[..., str]]]:
    """Convert functions into Anthropic tool schemas and an execution map."""
    schemas: list[dict[str, object]] = []
    function_map: dict[str, typing.Callable[..., str]] = {}

    for function in functions:
        hints = typing.get_type_hints(function)
        signature = inspect.signature(function)
        description, parameter_descriptions = _parse_google_docstring(
            function.__doc__ or ""
        )
        properties: dict[str, object] = {}
        required: list[str] = []

        for name, parameter in signature.parameters.items():
            annotation = hints.get(name, str)
            properties[name] = {
                **_schema_for_annotation(annotation),
                "description": parameter_descriptions.get(name, name),
            }
            if parameter.default is inspect.Parameter.empty:
                required.append(name)

        schemas.append(
            {
                "name": function.__name__,
                "description": description or function.__name__,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    **({"required": required} if required else {}),
                },
            }
        )
        function_map[function.__name__] = function

    return schemas, function_map
