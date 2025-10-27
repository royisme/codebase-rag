"""导出最新的 OpenAPI schema 到 docs/openapi.json。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from core.app import create_app


def main() -> None:
    app = create_app()
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
