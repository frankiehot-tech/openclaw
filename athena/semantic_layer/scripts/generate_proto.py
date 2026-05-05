#!/usr/bin/env python3
"""Generate Protobuf (.proto) file from Pydantic models for Men0 gRPC communication.

Usage:
    python generate_proto.py [--output-dir OUTPUT_DIR]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

TYPE_MAP = {
    "string": "string",
    "integer": "int64",
    "number": "double",
    "boolean": "bool",
    "array": "repeated",
}

FIELD_COUNTER = 1


def _proto_type(json_type: str, items: Any = None, ref: str | None = None) -> str:
    if ref:
        return ref.split("/")[-1]
    if json_type == "array" and items:
        item_type = items.get("type", "string")
        ref = items.get("$ref", "")
        if ref:
            return f"repeated {ref.split('/')[-1]}"
        return f"repeated {TYPE_MAP.get(item_type, 'string')}"
    return TYPE_MAP.get(json_type, "string")


def _generate_message(name: str, schema: dict[str, Any], definitions: dict[str, Any]) -> list[str]:
    global FIELD_COUNTER
    lines = [f"message {name} {{"]
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field_name, field_schema in properties.items():
        field_num = FIELD_COUNTER
        FIELD_COUNTER += 1
        proto_type = _proto_type(
            field_schema.get("type", "string"),
            field_schema.get("items"),
            field_schema.get("$ref", ""),
        )
        if field_name not in required:
            lines.append(f"  optional {proto_type} {field_name} = {field_num};")
        else:
            lines.append(f"  {proto_type} {field_name} = {field_num};")

    lines.append("}")
    lines.append("")
    return lines


def main():
    import argparse

    from athena.semantic_layer.schemas.intent import IntentPacket
    from athena.semantic_layer.schemas.state import SemanticStateSnapshot

    parser = argparse.ArgumentParser(description="Generate .proto from Pydantic models")
    parser.add_argument(
        "--output-dir",
        default="athena/semantic_layer/schemas/",
        help="Output directory for .proto file",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    models: list[tuple[str, Any]] = [
        ("intent", IntentPacket),
        ("state", SemanticStateSnapshot),
    ]

    print("Generating protobuf file:")
    all_lines = [
        'syntax = "proto3";',
        "",
        'package men0.semantic.v1;',
        "",
        'option go_package = "github.com/openclaw/men0/semantic/v1";',
        "",
    ]

    for _, model in models:
        schema = model.model_json_schema()
        definitions = schema.get("$defs", {})
        for def_name, def_schema in definitions.items():
            all_lines.extend(_generate_message(def_name, def_schema, definitions))
        all_lines.extend(_generate_message(model.__name__, schema, definitions))

    proto_path = output_dir / "athena_semantic.proto"
    proto_path.write_text("\n".join(all_lines))
    print(f"  Wrote {proto_path}")
    print("Done.")


if __name__ == "__main__":
    main()
