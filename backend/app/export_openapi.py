"""Print the OpenAPI schema as JSON: `uv run python -m app.export_openapi > openapi.json`.

Used by `make types` to regenerate the frontend's TypeScript types without starting a server.
"""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))
