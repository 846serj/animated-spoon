#!/usr/bin/env python3
"""
Production recipe server - completely self-contained.
No external imports that could cause embedding generation.
"""

from flask import Flask, request, jsonify
import os
import json
import sys
import faiss
import numpy as np
import openai
import re

from tools.image_utils import build_remote_image_figure, extract_remote_image_url
from tools.generator import generate_article as structured_generate_article
from tools.drafting import (
    DEFAULT_BLOCKED_IMAGE_DOMAINS,
    prepare_article_payload,
)

app = Flask(__name__)

BLOCKED_IMAGE_DOMAINS = set(DEFAULT_BLOCKED_IMAGE_DOMAINS)

# Global variables for pre-computed data
recipes = None
index = None
id_to_recipe = None

def load_data():
    """Load pre-computed data files."""
    global recipes, index, id_to_recipe
    
    print("Loading pre-computed recipe data...")
    
    try:
        # Load recipes with embeddings
        with open("data/recipes_with_embeddings.json", "r") as f:
            recipes = json.load(f)
        
        # Load FAISS index
        index = faiss.read_index("data/recipes.index")
        
        # Create ID mapping
        id_to_recipe = {recipe["id"]: recipe for recipe in recipes}
        
        print(f"Loaded {len(recipes)} recipes with embeddings")
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

def search_recipes(query, k=5):
    """Search recipes using pre-computed embeddings."""
    try:
        # Generate embedding for query
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = np.array([response.data[0].embedding], dtype=np.float32)
        
        # Search FAISS index
        scores, indices = index.search(query_embedding, k)
        
        # Get top recipes
        top_recipes = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(recipes):
                recipe = recipes[idx].copy()
                recipe['similarity_score'] = float(score)
                top_recipes.append(recipe)

        return top_recipes
    except Exception as e:
        print(f"Error searching recipes: {e}")
        return []


def generate_article(query, recipes):
    """Generate article from recipes while preserving Airtable image links."""
    try:
        return structured_generate_article(query, recipes)
    except Exception as e:
        print(f"Error generating structured article: {e}")
        return _fallback_article(query, recipes)


def _fallback_article(query, recipes):
    """Fallback article that still hotlinks original imagery."""
    if not recipes:
        return f"<h1>{query}</h1><p>No recipes found.</p>"

    sections = [f"<h1>{query}</h1>"]

    for recipe in recipes:
        title = recipe.get('title', 'Untitled Recipe')
        section = [f"<h2>{title}</h2>"]

        image_url, airtable_field = extract_remote_image_url(recipe)
        if image_url:
            section.append(build_remote_image_figure(title, image_url, airtable_field))

        ingredients = recipe.get('ingredients')
        if ingredients:
            section.append(f"<h3>Ingredients</h3>\n<p>{ingredients}</p>")

        instructions = recipe.get('instructions')
        if instructions:
            section.append(f"<h3>Instructions</h3>\n<p>{instructions}</p>")

        source_url = recipe.get('url')
        if source_url:
            section.append(f'<p><a href="{source_url}">View Full Recipe</a></p>')

        sections.append('\n'.join(section))

    return '\n\n'.join(sections)

@app.route('/api/recipe-query', methods=['POST'])
def generate_recipe_article():
    """Generate recipe article from query."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Extract number from query
        numbers = re.findall(r'\d+', query)
        k = int(numbers[0]) if numbers else 5
        
        # Search recipes
        top_recipes = search_recipes(query, k=k)
        
        if not top_recipes:
            return jsonify({'error': 'No recipes found'}), 404

        payload, removed_recipes = prepare_article_payload(
            query,
            top_recipes,
            blocked_domains=BLOCKED_IMAGE_DOMAINS,
            article_generator=generate_article,
        )

        if removed_recipes:
            print(
                "Removed recipes with inaccessible images:",
                [(r.get('title'), r.get('image_url')) for r in removed_recipes]
            )

        if not payload:
            return jsonify({
                'error': 'No recipes with accessible images found',
                'removed_recipes': removed_recipes,
            }), 502

        return jsonify(payload)
        
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

