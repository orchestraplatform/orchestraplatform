#!/usr/bin/env python3
"""Generate OpenAPI schema from FastAPI app."""

import json
import sys
from pathlib import Path

# Add current directory to path to import main
sys.path.insert(0, str(Path(__file__).parent))

from main import app

def generate_schema(output_file: str = "openapi.json"):
    """Generate OpenAPI schema and save to file."""
    schema = app.openapi()
    
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"✅ OpenAPI schema generated: {output_file}")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    generate_schema(output)
