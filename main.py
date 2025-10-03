#!/usr/bin/env python3
"""
Main entry point for the recipe server.
This file ensures Render uses the correct server.
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the production server
from production_server import app

if __name__ == '__main__':
    print("Starting recipe server via main.py...")
    
    # Load data
    from production_server import load_data
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
    
    print("Server ready!")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
