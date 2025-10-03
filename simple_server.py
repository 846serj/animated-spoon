#!/usr/bin/env python3
"""
Simplified Flask server for Render deployment with minimal memory usage.
"""

from flask import Flask, request, jsonify
import sys
import os
import json

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
    """Set up recipe data from Airtable with minimal memory usage."""
    import os
    import gc
    
    print("1. Creating data directory...")
    os.makedirs("data", exist_ok=True)
    
    print("2. Fetching recipes from Airtable...")
    recipes = airtable_sync.fetch_airtable_records()
    
    # For Render's memory limits, let's use only the first 1000 recipes
    if len(recipes) > 1000:
        print(f"Limiting to first 1000 recipes for memory efficiency (total: {len(recipes)})")
        recipes = recipes[:1000]
    
    # Save raw recipes first
    print("3. Saving raw recipes...")
    with open("data/recipes.json", "w") as f:
        json.dump(recipes, f, indent=2)
    
    print("4. Generating embeddings in tiny batches...")
    # Process in very small batches to reduce memory usage
    batch_size = 5  # Very small batch size
    recipes_with_embeddings = []
    
    for i in range(0, len(recipes), batch_size):
        batch = recipes[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(recipes) + batch_size - 1)//batch_size}")
        
        batch_embeddings = embeddings.generate_embeddings(batch)
        recipes_with_embeddings.extend(batch_embeddings)
        
        # Force garbage collection to free memory
        del batch_embeddings
        gc.collect()
        
        # Save progress every 50 recipes
        if len(recipes_with_embeddings) % 50 == 0:
            print(f"Saving progress: {len(recipes_with_embeddings)} recipes processed")
            embeddings.save_embeddings(recipes_with_embeddings)
    
    print("5. Saving final embeddings...")
    embeddings.save_embeddings(recipes_with_embeddings)
    
    # Clear memory before building index
    del recipes_with_embeddings
    gc.collect()
    
    print("6. Building FAISS index...")
    # Reload embeddings for index building
    recipes_with_embeddings = embeddings.load_embeddings()
    vector_store.build_faiss_index(recipes_with_embeddings)
    
    # Final cleanup
    del recipes_with_embeddings
    gc.collect()
    
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

@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'message': 'Recipe Generation Server (Simplified)',
        'status': 'running',
        'recipes_loaded': len(recipes) if recipes else 0,
        'endpoints': ['/api/recipe-query', '/health']
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'recipes_loaded': len(recipes) if recipes else 0})

if __name__ == '__main__':
    print("Starting simplified recipe generation server...")
    load_data()
    print("Server ready!")
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
