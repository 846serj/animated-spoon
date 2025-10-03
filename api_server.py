#!/usr/bin/env python3
"""
Simple Flask API server to serve recipe generation requests.
"""

from flask import Flask, request, jsonify
import sys
import os

# Add current directory to path to import tools
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import airtable_sync, embeddings, vector_store, retrieval, generator

app = Flask(__name__)

# Global variables for loaded data
recipes = None
index = None
id_to_recipe = None

def load_data():
    """Load recipes and FAISS index, or create them if they don't exist."""
    global recipes, index, id_to_recipe
    
    import os
    
    # Check if data files exist
    if not os.path.exists("data/recipes_with_embeddings.json") or not os.path.exists("data/recipes.index"):
        print("Data files not found. Setting up recipe data...")
        setup_data()
    
    print("Loading recipes with embeddings...")
    recipes = embeddings.load_embeddings()
    
    print("Loading FAISS index...")
    index = vector_store.load_faiss_index()
    id_to_recipe = vector_store.get_id_to_recipe(recipes)
    
    print(f"Loaded {len(recipes)} recipes")

def setup_data():
    """Set up recipe data from Airtable."""
    import os
    
    print("1. Creating data directory...")
    os.makedirs("data", exist_ok=True)
    
    print("2. Fetching recipes from Airtable...")
    recipes = airtable_sync.fetch_airtable_records()
    
    print("3. Generating embeddings...")
    recipes_with_embeddings = embeddings.generate_embeddings(recipes)
    
    print("4. Saving embeddings...")
    embeddings.save_embeddings(recipes_with_embeddings)
    
    print("5. Building FAISS index...")
    vector_store.build_faiss_index(recipes_with_embeddings)
    
    print("Data setup complete!")

@app.route('/api/recipe-query', methods=['POST'])
def generate_recipe_article():
    """Generate recipe article from query."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Extract number from query (default to 5 if no number found)
        import re
        numbers = re.findall(r'\d+', query)
        k = int(numbers[0]) if numbers else 5
        
        # Retrieve recipes
        top_recipes = retrieval.search_recipes(query, index, id_to_recipe, k=k)
        
        if not top_recipes:
            return jsonify({'error': 'No recipes found'}), 404
        
        # Generate complete article
        article = generator.generate_article(query, top_recipes)
        
        # Extract sources from recipes
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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'recipes_loaded': len(recipes) if recipes else 0})

if __name__ == '__main__':
    print("Starting recipe generation server...")
    load_data()
    print("Server ready!")
    app.run(host='0.0.0.0', port=3004, debug=True)
