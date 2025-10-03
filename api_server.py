#!/usr/bin/env python3
"""
Redirect api_server.py to production_server.py
This satisfies Render's auto-detection while using our optimized server.
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the production server
if __name__ == '__main__':
    print("Redirecting to production_server.py...")
    
    # Import the production server module
    from production_server import app, load_data
    
    print("Starting production recipe server...")
    
    # Load data
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
    
    print("Server ready!")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
