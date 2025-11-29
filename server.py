#!/usr/bin/env python3
"""
Marimo Server - Serves all dashboards from notebooks directory
This allows navigation between notebooks via relative links.
"""

import marimo
from pathlib import Path

# Get the notebooks directory
notebooks_dir = Path(__file__).parent / "notebooks"

# Create ASGI app and add each notebook explicitly
server = marimo.create_asgi_app()

# Add each notebook in the directory
app_names = []
for filename in sorted(notebooks_dir.iterdir()):
    if filename.suffix == ".py" and filename.name != "__init__.py":
        app_name = filename.stem  # e.g., "index", "ad_performance_dashboard"
        # Mount at root with .py extension to match the link format
        server = server.with_app(path=f"/{app_name}.py", root=str(filename))
        app_names.append(app_name)
        print(f"✅ Registered: /{app_name}.py")

# Build the app
app = server.build()

if __name__ == "__main__":
    import uvicorn
    
    print("\n🚀 Starting Marimo Dashboard Server...")
    print(f"📁 Serving {len(app_names)} notebooks from: {notebooks_dir}")
    print("\n🌐 Available dashboards:")
    for name in app_names:
        print(f"   - http://localhost:2718/{name}.py")
    
    print("\n📊 Recommended starting point:")
    print("   - Index: http://localhost:2718/index.py")
    print("\n✨ Navigation between notebooks now works!")
    
    uvicorn.run(app, host="0.0.0.0", port=2718)
