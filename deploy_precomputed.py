#!/usr/bin/env python3
"""
Pre-compute all data locally, then deploy lightweight server.
This is the industry-standard approach for ML/AI services.
"""

import os
import json
import shutil
from tools import airtable_sync, embeddings, vector_store

def main():
    print("=== Pre-computing Recipe Data ===")
    
    # 1. Fetch recipes
    print("1. Fetching recipes from Airtable...")
    recipes = airtable_sync.fetch_airtable_records()
    
    # 2. Generate embeddings
    print("2. Generating embeddings...")
    recipes_with_embeddings = embeddings.generate_embeddings(recipes)
    
    # 3. Save embeddings
    print("3. Saving embeddings...")
    embeddings.save_embeddings(recipes_with_embeddings)
    
    # 4. Build FAISS index
    print("4. Building FAISS index...")
    vector_store.build_faiss_index(recipes_with_embeddings)
    
    # 5. Create deployment package
    print("5. Creating deployment package...")
    create_deployment_package()
    
    print("=== Pre-computation Complete! ===")
    print("Data files ready for deployment:")
    print("- data/recipes_with_embeddings.json")
    print("- data/recipes.index")
    print("- data/recipes.json")

def create_deployment_package():
    """Create a clean deployment package."""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Create a simple deployment script
    deploy_script = '''#!/usr/bin/env python3
"""
Lightweight recipe server with pre-computed data.
"""

from flask import Flask, request, jsonify
import os
import json
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import retrieval, generator

app = Flask(__name__)

# Global variables
recipes = None
index = None
id_to_recipe = None

def load_precomputed_data():
    """Load pre-computed data."""
    global recipes, index, id_to_recipe
    
    import faiss
    import numpy as np
    
    print("Loading pre-computed data...")
    
    # Load recipes
    with open("data/recipes_with_embeddings.json", "r") as f:
        recipes = json.load(f)
    
    # Load FAISS index
    index = faiss.read_index("data/recipes.index")
    
    # Create ID mapping
    id_to_recipe = {recipe["id"]: recipe for recipe in recipes}
    
    print(f"Loaded {len(recipes)} recipes")

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
        
        # Retrieve recipes
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
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'message': 'Recipe Generation Server',
        'status': 'running',
        'recipes_loaded': len(recipes) if recipes else 0
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    load_precomputed_data()
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
'''
    
    with open("deploy_server.py", "w") as f:
        f.write(deploy_script)
    
    print("Created deploy_server.py")

if __name__ == "__main__":
    main()
