#!/bin/bash
echo "Starting animated-spoon server..."
echo "Current directory: $(pwd)"
echo "Files in directory:"
ls -la
echo "Checking if api_server.py exists:"
if [ -f "api_server.py" ]; then
    echo "✅ api_server.py found"
    echo "Starting server..."
    python api_server.py
else
    echo "❌ api_server.py not found!"
    echo "Available Python files:"
    ls -la *.py
    exit 1
fi
