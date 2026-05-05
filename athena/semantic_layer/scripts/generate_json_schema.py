#!/usr/bin/env python3
"""Generate JSON Schema files from Pydantic models for SGLang XGrammar constraints.

Usage:
    python generate_json_schema.py [--output-dir OUTPUT_DIR]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_json_schema(model_class: Any) -> dict[str, Any]:
    schema = model_class.model_json_schema()
    _clean_schema(schema)
    return schema


def _clean_schema(schema: dict[str, Any]) -> None:
    for field in list(schema.get("$defs", {}).values()):
        field.pop("title", None)
    schema.pop("title", None)


def _write_schema(schema: dict[str, Any], filename: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    print(f"  Wrote {path}")


def main():
    import argparse

    from athena.semantic_layer.schemas.intent import IntentPacket
    from athena.semantic_layer.schemas.state import SemanticStateSnapshot

    parser = argparse.ArgumentParser(description="Generate JSON Schema from Pydantic models")
    parser.add_argument(
        "--output-dir",
        default="athena/semantic_layer/schemas/",
        help="Output directory for JSON Schema files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    models: list[tuple[str, Any]] = [
        ("intent.json", IntentPacket),
        ("state.json", SemanticStateSnapshot),
    ]

    print("Generating JSON Schema files:")
    for filename, model in models:
        schema = generate_json_schema(model)
        _write_schema(schema, filename, output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
