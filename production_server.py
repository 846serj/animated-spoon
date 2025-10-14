#!/usr/bin/env python3
"""
Production recipe server - completely self-contained.
No external imports that could cause embedding generation.
"""

from flask import Flask, request, jsonify, redirect
import os
import json
import sys
import faiss
import numpy as np
import openai
import re
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse

from tools.image_utils import extract_remote_image_url
from urllib3.util import Retry

app = Flask(__name__)

WORDPRESS_PROXY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

WORDPRESS_PROXY_TIMEOUT = (5, 30)
WORDPRESS_PROXY_RETRY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("HEAD", "GET"),
)

WORDPRESS_PROXY_SESSION = requests.Session()
WORDPRESS_PROXY_SESSION.headers.update(WORDPRESS_PROXY_HEADERS)
_wordpress_adapter = HTTPAdapter(max_retries=WORDPRESS_PROXY_RETRY)
WORDPRESS_PROXY_SESSION.mount("http://", _wordpress_adapter)
WORDPRESS_PROXY_SESSION.mount("https://", _wordpress_adapter)

BLOCKED_IMAGE_DOMAINS = {"smushcdn.com"}

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


def _get_image_url_from_recipe(recipe):
    """Extract the first available remote image URL from a recipe record."""
    image_url, _ = extract_remote_image_url(recipe)
    return image_url


def _is_blocked_image_domain(image_url):
    """Return True if the image URL belongs to a blocked domain."""
    try:
        hostname = urlparse(image_url).hostname or ""
    except ValueError:
        return False

    hostname = hostname.lower()
    return any(hostname.endswith(domain) for domain in BLOCKED_IMAGE_DOMAINS)


def filter_inaccessible_image_recipes(recipes):
    """Remove recipes whose remote images cannot be reached reliably."""
    accessible_recipes = []
    removed_recipes = []

    for recipe in recipes:
        image_url = _get_image_url_from_recipe(recipe)

        if not image_url:
            accessible_recipes.append(recipe)
            continue

        if _is_blocked_image_domain(image_url):
            removed_recipes.append({
                "title": recipe.get("title", "Untitled Recipe"),
                "image_url": image_url,
                "reason": "blocked_domain",
            })
            continue

        try:
            response = WORDPRESS_PROXY_SESSION.head(
                image_url,
                allow_redirects=True,
                timeout=WORDPRESS_PROXY_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            try:
                with WORDPRESS_PROXY_SESSION.get(
                    image_url,
                    stream=True,
                    timeout=WORDPRESS_PROXY_TIMEOUT,
                ) as upstream_response:
                    upstream_response.raise_for_status()
            except requests.RequestException as exc:
                removed_recipes.append({
                    "title": recipe.get("title", "Untitled Recipe"),
                    "image_url": image_url,
                    "reason": "fetch_error",
                    "error": str(exc),
                })
                continue

        accessible_recipes.append(recipe)

    return accessible_recipes, removed_recipes

def generate_article(query, recipes):
    """Generate article from recipes."""
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Prepare recipe context
        recipe_context = ""
        for i, recipe in enumerate(recipes[:5], 1):
            recipe_context += f"\n{i}. {recipe.get('title', 'Untitled Recipe')}\n"
            recipe_context += f"   Ingredients: {recipe.get('ingredients', 'N/A')}\n"
            recipe_context += f"   Instructions: {recipe.get('instructions', 'N/A')}\n"
            if recipe.get('url'):
                recipe_context += f"   Source: {recipe['url']}\n"
        
        # Generate article
        prompt = f"""You are a professional food writer. Create a comprehensive article about: {query}

Use these recipes as inspiration and reference:

{recipe_context}

Write a complete article that includes:
1. An engaging introduction
2. The requested number of recipes with full ingredients and instructions
3. Tips and variations
4. A conclusion

Make it professional, engaging, and practical for home cooks."""

        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating article: {e}")
        return f"Error generating article: {str(e)}"

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

        filtered_recipes, removed_recipes = filter_inaccessible_image_recipes(top_recipes)

        if removed_recipes:
            print(
                "Removed recipes with inaccessible images:",
                [(r.get('title'), r.get('image_url')) for r in removed_recipes]
            )

        if not filtered_recipes:
            return jsonify({
                'error': 'No recipes with accessible images found',
                'removed_recipes': removed_recipes,
            }), 502

        top_recipes = filtered_recipes

        # Generate article
        article = generate_article(query, top_recipes)

        # Extract sources
        sources = [recipe.get('url') for recipe in top_recipes if recipe.get('url')]

        return jsonify({
            'article': article,
            'sources': sources,
            'recipe_count': len(top_recipes),
            'query': query,
            'removed_recipes': removed_recipes,
        })
        
    except Exception as e:
        print(f"Error generating recipe article: {e}")
        return jsonify({'error': str(e)}), 500


def _validate_remote_image_url(image_url):
    """Validate that the provided image URL can be used directly."""
    if not image_url:
        return False

    try:
        parsed = urlparse(image_url)
    except ValueError:
        return False

    if parsed.scheme not in ('http', 'https'):
        return False

    if _is_blocked_image_domain(image_url):
        return False

    return True


@app.route('/api/wordpress/proxy', methods=['GET'])
def proxy_wordpress_asset():
    """Redirect to the original image to keep it hosted remotely."""
    image_url = request.args.get('url', '').strip()

    if not image_url:
        return jsonify({'error': 'Missing url parameter'}), 400

    if not _validate_remote_image_url(image_url):
        return jsonify({'error': 'Invalid or blocked image URL'}), 400

    return redirect(image_url, code=302)


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

