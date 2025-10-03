#!/usr/bin/env python3
"""
Server deployment script - generates data on server, deploys lightweight API.
Industry standard approach for production AI services.
"""

import os
import json
import sys
from tools import airtable_sync, embeddings, vector_store

def generate_server_data():
    """Generate all data on the server."""
    print("=== Generating Recipe Data on Server ===")
    
    # 1. Fetch recipes from Airtable
    print("1. Fetching recipes from Airtable...")
    recipes = airtable_sync.fetch_airtable_records()
    print(f"   Fetched {len(recipes)} recipes")
    
    # 2. Generate embeddings in small batches
    print("2. Generating embeddings...")
    recipes_with_embeddings = []
    batch_size = 25  # Small batches for server memory
    
    for i in range(0, len(recipes), batch_size):
        batch = recipes[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}/{(len(recipes) + batch_size - 1)//batch_size}")
        
        batch_embeddings = embeddings.generate_embeddings(batch)
        recipes_with_embeddings.extend(batch_embeddings)
    
    # 3. Save embeddings
    print("3. Saving embeddings...")
    embeddings.save_embeddings(recipes_with_embeddings)
    
    # 4. Build FAISS index
    print("4. Building FAISS index...")
    vector_store.build_faiss_index(recipes_with_embeddings)
    
    print("=== Data Generation Complete! ===")
    return len(recipes_with_embeddings)

def create_lightweight_server():
    """Create a lightweight server that only serves pre-computed data."""
    
    server_code = '''#!/usr/bin/env python3
"""
Lightweight recipe server - only serves pre-computed data.
No data generation, just fast serving.
"""

from flask import Flask, request, jsonify
import os
import json
import sys
import faiss
import numpy as np

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import retrieval, generator

app = Flask(__name__)

# Global variables for pre-computed data
recipes = None
index = None
id_to_recipe = None

def load_data():
    """Load pre-computed data files."""
    global recipes, index, id_to_recipe
    
    print("Loading pre-computed recipe data...")
    
    # Load recipes with embeddings
    with open("data/recipes_with_embeddings.json", "r") as f:
        recipes = json.load(f)
    
    # Load FAISS index
    index = faiss.read_index("data/recipes.index")
    
    # Create ID mapping
    id_to_recipe = {recipe["id"]: recipe for recipe in recipes}
    
    print(f"Loaded {len(recipes)} recipes with embeddings")

@app.route('/api/recipe-query', methods=['POST'])
def generate_recipe_article():
    """Generate recipe article from query."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Extract number from query
        import re
        numbers = re.findall(r'\\d+', query)
        k = int(numbers[0]) if numbers else 5
        
        # Retrieve recipes using pre-computed index
        top_recipes = retrieval.search_recipes(query, index, id_to_recipe, k=k)
        
        if not top_recipes:
            return jsonify({'error': 'No recipes found'}), 404
        
        # Generate article
        article = generator.generate_article(query, top_recipes)
        
        # Extract sources
        sources = [recipe.get('url') for recipe in top_recipes if recipe.get('url')]
        
        return jsonify({
            'article': article,
            'sources': sources,
            'recipe_count': len(top_recipes),
            'query': query
        })
        
    except Exception as e:
        print(f"Error generating recipe article: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'message': 'Recipe Generation Server',
        'status': 'running',
        'recipes_loaded': len(recipes) if recipes else 0,
        'endpoints': ['/api/recipe-query', '/health']
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'recipes_loaded': len(recipes) if recipes else 0
    })

if __name__ == '__main__':
    print("Starting lightweight recipe server...")
    load_data()
    print("Server ready!")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
'''
    
    with open("lightweight_server.py", "w") as f:
        f.write(server_code)
    
    print("Created lightweight_server.py")

def main():
    """Main deployment function."""
    print("=== Server Deployment Process ===")
    
    # Step 1: Generate all data
    recipe_count = generate_server_data()
    
    # Step 2: Create lightweight server
    create_lightweight_server()
    
    # Step 3: Update Procfile
    with open("Procfile", "w") as f:
        f.write("web: python lightweight_server.py")
    
    print("=== Deployment Ready! ===")
    print(f"Generated {recipe_count} recipes with embeddings")
    print("Files ready for deployment:")
    print("- lightweight_server.py (lightweight API server)")
    print("- data/recipes_with_embeddings.json (pre-computed data)")
    print("- data/recipes.index (FAISS index)")
    print("- Procfile (updated for lightweight server)")

if __name__ == "__main__":
    main()
