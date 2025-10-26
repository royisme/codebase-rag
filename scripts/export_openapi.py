import json
from fastapi.openapi.utils import get_openapi
from core.app import create_app


app = create_app()
schema = get_openapi(
    title=app.title,
    version=app.version,
    routes=app.routes,
)
output_path = "docs/openapi.json"
with output_path.open("w", encoding="utf-8") as f:
    json.dump(schema, f, ensure_ascii=False, indent=2)
