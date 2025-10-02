#!/bin/bash
# Start the recipe generation server

echo "Starting Recipe Generation Server..."
echo "Make sure you have run: python scripts/sync_from_airtable.py"
echo ""

# Check if data files exist
if [ ! -f "data/recipes_with_embeddings.json" ]; then
    echo "Error: Recipe embeddings not found!"
    echo "Please run: python scripts/sync_from_airtable.py"
    exit 1
fi

if [ ! -f "data/recipes.index" ]; then
    echo "Error: FAISS index not found!"
    echo "Please run: python scripts/sync_from_airtable.py"
    exit 1
fi

# Start the server
python api_server.py
