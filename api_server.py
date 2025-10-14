#!/usr/bin/env python3
"""
Recipe server with local data storage - downloads all Airtable data once,
then searches through it efficiently without re-generating embeddings.
"""

import sys
import os
import json
import numpy as np
import openai
import re
import requests
from requests.adapters import HTTPAdapter
import threading
import time
import faiss
from urllib.parse import urlparse

from tools.generator import (
    generate_article as build_structured_article,
    generate_article_fallback,
)
from tools.image_utils import extract_remote_image_url
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from urllib3.util import Retry

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app, origins=["https://test-for-write.onrender.com", "http://localhost:3000", "http://localhost:3003"])

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

# Global variables for cached data
recipes_cache = None
faiss_index = None
cache_ready = False
cache_progress = "Starting..."
cache_error = None

def fetch_all_recipes_from_airtable():
    """Fetch ALL recipes from Airtable and cache them locally."""
    global recipes_cache, cache_ready, cache_progress, cache_error

    try:
        cache_progress = "Fetching recipes from Airtable..."
        cache_error = None
        
        api_key = os.getenv("AIRTABLE_API_KEY")
        base_id = os.getenv("AIRTABLE_BASE_ID", "appa4SaUbDRFYM42O")
        table_name = os.getenv("AIRTABLE_TABLE_NAME", "Molly's View")
        
        if not api_key:
            raise Exception("AIRTABLE_API_KEY environment variable not set")
        
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Fetch ALL recipes (no limit)
        params = {
            "pageSize": 100,  # Airtable max per request
            "sort[0][field]": "Title",
            "sort[0][direction]": "asc"
        }
        
        all_records = []
        offset = None
        batch_count = 0
        
        while True:
            if offset:
                params["offset"] = offset
            
            batch_count += 1
            cache_progress = f"Fetching batch {batch_count} from Airtable..."
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            all_records.extend(data["records"])
            
            cache_progress = f"Fetched {len(all_records)} recipes so far..."
            
            if "offset" in data:
                offset = data["offset"]
            else:
                break
        
        # Convert Airtable records to recipe format
        recipes = []
        for record in all_records:
            fields = record.get("fields", {})
            
            # Debug: Print available fields for first record
            if len(recipes) == 0:
                print(f"Available Airtable fields: {list(fields.keys())}")
            
            recipe = {
                "id": record["id"],
                "title": fields.get("Title", "Untitled Recipe"),
                "ingredients": fields.get("Ingredients", ""),
                "instructions": fields.get("Instructions", ""),
                "url": fields.get("URL", ""),
                "cuisine": fields.get("Cuisine", ""),
                "meal_type": fields.get("Meal Type", ""),
                "difficulty": fields.get("Difficulty", ""),
                "prep_time": fields.get("Prep Time", ""),
                "cook_time": fields.get("Cook Time", ""),
                "servings": fields.get("Servings", ""),
                "tags": fields.get("Tags", ""),
                "image": fields.get("Image", ""),
                "image_url": fields.get("Image URL", ""),
                "image_link": fields.get("Image Link", ""),
                "photo": fields.get("Photo", ""),
                "picture": fields.get("Picture", ""),
                "attachments": fields.get("Attachments", ""),
                "description": fields.get("Description", ""),
            }
            recipes.append(recipe)
        
        # Save to local file for persistence
        cache_progress = "Saving recipes to local cache..."
        os.makedirs("data", exist_ok=True)
        with open("data/recipes_cache.json", "w") as f:
            json.dump(recipes, f, indent=2)
        
        recipes_cache = recipes
        
        # Build FAISS index for semantic search
        cache_progress = "Building FAISS index for semantic search..."
        build_faiss_index(recipes)
        
        cache_ready = True
        cache_progress = f"Cache ready! Loaded {len(recipes)} recipes with FAISS index"
        
        print(f"Successfully cached {len(recipes)} recipes from Airtable with FAISS index")
        
    except Exception as e:
        cache_progress = f"Error: {str(e)}"
        cache_error = str(e)
        print(f"Error fetching recipes: {e}")

def build_faiss_index(recipes):
    """Build FAISS index for semantic search."""
    global faiss_index, cache_error

    try:
        cache_progress = "Generating embeddings for FAISS index..."
        cache_error = None
        
        # Generate embeddings in batches
        batch_size = 50
        all_embeddings = []
        
        for i in range(0, len(recipes), batch_size):
            batch = recipes[i:i + batch_size]
            batch_texts = []
            
            for recipe in batch:
                text = f"{recipe['title']} {recipe['ingredients']} {recipe['instructions']}"
                batch_texts.append(text)
            
            # Generate embeddings for batch
            openai.api_key = os.getenv("OPENAI_API_KEY")
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=batch_texts
            )
            
            # Add embeddings to list
            for embedding_data in response.data:
                all_embeddings.append(embedding_data.embedding)
            
            cache_progress = f"Generated embeddings for {len(all_embeddings)}/{len(recipes)} recipes"
        
        # Create FAISS index
        cache_progress = "Creating FAISS index..."
        embeddings_matrix = np.array(all_embeddings, dtype=np.float32)
        
        # Create FAISS index (Inner Product for cosine similarity)
        dimension = embeddings_matrix.shape[1]
        faiss_index = faiss.IndexFlatIP(dimension)
        faiss_index.add(embeddings_matrix)
        
        # Save FAISS index
        faiss.write_index(faiss_index, "data/recipes_faiss.index")
        
        cache_progress = f"FAISS index built! {len(recipes)} recipes indexed"
        print(f"Built FAISS index with {len(recipes)} recipes")
        
    except Exception as e:
        cache_progress = f"FAISS index error: {str(e)}"
        cache_error = str(e)
        print(f"Error building FAISS index: {e}")

def load_cached_recipes():
    """Load recipes from local cache if available."""
    global recipes_cache, faiss_index, cache_ready, cache_progress, cache_error

    try:
        if os.path.exists("data/recipes_cache.json") and os.path.exists("data/recipes_faiss.index"):
            cache_progress = "Loading recipes from local cache..."
            with open("data/recipes_cache.json", "r") as f:
                recipes_cache = json.load(f)

            cache_progress = "Loading FAISS index..."
            faiss_index = faiss.read_index("data/recipes_faiss.index")

            cache_ready = True
            cache_progress = f"Cache loaded! {len(recipes_cache)} recipes with FAISS index ready"
            cache_error = None
            print(f"Loaded {len(recipes_cache)} recipes with FAISS index from cache")
            return True
    except Exception as e:
        cache_progress = f"Cache load error: {str(e)}"
        cache_error = str(e)
        print(f"Error loading cache: {e}")

    return False

def search_recipes_text(query, recipes, k=5):
    """Fast text-based search through all recipes."""
    query_lower = query.lower()
    query_words = query_lower.split()
    
    scored_recipes = []
    
    for recipe in recipes:
        score = 0
        text = f"{recipe['title']} {recipe['ingredients']} {recipe['instructions']}".lower()
        
        # Score based on word matches
        for word in query_words:
            if word in text:
                # Higher score for title matches
                if word in recipe['title'].lower():
                    score += 10
                # Medium score for ingredient matches
                elif word in recipe['ingredients'].lower():
                    score += 5
                # Lower score for instruction matches
                else:
                    score += 1
        
        # Bonus for exact phrase matches
        if query_lower in text:
            score += 20
        
        if score > 0:
            scored_recipes.append((recipe, score))
    
    # Sort by score and return top k
    scored_recipes.sort(key=lambda x: x[1], reverse=True)
    return [recipe for recipe, score in scored_recipes[:k]]


def _get_image_url_from_recipe(recipe):
    """Extract the first available remote image URL and Airtable field."""
    return extract_remote_image_url(recipe)


def _is_blocked_image_domain(image_url):
    """Return True if the image URL belongs to a blocked domain."""
    try:
        hostname = urlparse(image_url).hostname or ""
    except ValueError:
        return False

    hostname = hostname.lower()
    return any(hostname.endswith(domain) for domain in BLOCKED_IMAGE_DOMAINS)


def _is_transient_image_fetch_error(error: requests.RequestException) -> bool:
    """Return True when an image fetch failure looks temporary."""
    if isinstance(error, (requests.Timeout, requests.ConnectionError)):
        return True

    response = getattr(error, "response", None)
    if response is None:
        return False

    status_code = getattr(response, "status_code", None)
    if status_code is None:
        return False

    return status_code >= 500 or status_code == 429


def filter_inaccessible_image_recipes(recipes):
    """Remove recipes whose remote images cannot be reached reliably.

    The validation is limited to ``HEAD`` requests so we never download image
    binaries that could be stored accidentally by WordPress or other
    downstream systems. Hosts that block ``HEAD`` are treated as accessible to
    keep their hotlinked URLs intact.
    """
    accessible_recipes = []
    removed_recipes = []

    for recipe in recipes:
        image_url, airtable_field = _get_image_url_from_recipe(recipe)

        if not image_url:
            accessible_recipes.append(recipe)
            continue

        if _is_blocked_image_domain(image_url):
            removed_recipes.append({
                "title": recipe.get("title", "Untitled Recipe"),
                "image_url": image_url,
                "airtable_field": airtable_field,
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
        except requests.RequestException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)

            if _is_transient_image_fetch_error(exc) or status_code in {400, 401, 403, 405, 406}:
                print(
                    "Non-fatal image availability issue (HEAD)",
                    recipe.get("title", "Untitled Recipe"),
                    image_url,
                    status_code,
                )
                accessible_recipes.append(recipe)
                continue

            removed_recipes.append({
                "title": recipe.get("title", "Untitled Recipe"),
                "image_url": image_url,
                "airtable_field": airtable_field,
                "reason": "head_error",
                "status_code": status_code,
                "error": str(exc),
            })
            continue

        accessible_recipes.append(recipe)

    return accessible_recipes, removed_recipes

def search_recipes_semantic(query, recipes, k=5):
    """Semantic search using FAISS index."""
    global faiss_index
    
    try:
        if faiss_index is None:
            print("FAISS index not available, falling back to text search")
            return search_recipes_text(query, recipes, k)
        
        # Generate embedding for query
        openai.api_key = os.getenv("OPENAI_API_KEY")
        query_embedding = generate_embedding(query)
        
        # Search FAISS index
        query_vector = np.array([query_embedding], dtype=np.float32)
        scores, indices = faiss_index.search(query_vector, k)
        
        # Get top recipes
        top_recipes = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(recipes):
                recipe = recipes[idx].copy()
                recipe['similarity_score'] = float(score)
                top_recipes.append(recipe)
        
        return top_recipes
        
    except Exception as e:
        print(f"FAISS semantic search error: {e}")
        # Fallback to text search
        return search_recipes_text(query, recipes, k)

def generate_embedding(text):
    """Generate embedding for a single text."""
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    
    return response.data[0].embedding

def generate_article(query, recipes):
    """Generate article using the structured generator with a deterministic fallback."""
    openai.api_key = os.getenv("OPENAI_API_KEY")

    try:
        return build_structured_article(query, recipes)
    except Exception as exc:
        print(f"Error with systematic generation: {exc}")
        return generate_article_simple(query, recipes)


def generate_article_simple(query, recipes):
    """Fallback simple article generation that preserves remote imagery."""
    return generate_article_fallback(query, recipes)

@app.route('/api/recipe-query', methods=['POST'])
def generate_recipe_article():
    """Generate recipe article from query."""
    try:
        print("=== Recipe Query Started ===")
        
        if not cache_ready:
            print("Cache not ready yet")
            status_code = 503
            status = 'loading'
            error_message = 'Recipe cache not ready yet'

            if cache_error:
                status_code = 500
                status = 'error'
                error_message = 'Recipe cache failed to initialize'

            return jsonify({
                'error': error_message,
                'progress': cache_progress,
                'status': status,
                'details': cache_error
            }), status_code
        
        data = request.get_json()
        query = data.get('query', '')
        
        print(f"Received query: {query}")
        
        if not query:
            print("Error: No query provided")
            return jsonify({'error': 'Query is required'}), 400
        
        # Extract number from query
        numbers = re.findall(r'\d+', query)
        k = int(numbers[0]) if numbers else 5
        print(f"Extracted k={k} from query")
        
        # Check environment variables
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("Error: OPENAI_API_KEY not set")
            return jsonify({'error': 'OPENAI_API_KEY environment variable not set'}), 500
        
        print("Environment variables OK")
        
        # Search through all cached recipes
        print(f"Searching through {len(recipes_cache)} cached recipes...")
        try:
            top_recipes = search_recipes_semantic(query, recipes_cache, k=k)
            print(f"Found {len(top_recipes)} relevant recipes")
        except Exception as e:
            print(f"Error in semantic search: {e}")
            # Fallback to text search
            top_recipes = search_recipes_text(query, recipes_cache, k=k)
            print(f"Fallback found {len(top_recipes)} recipes")
        
        if not top_recipes:
            print("No relevant recipes found")
            return jsonify({'error': 'No relevant recipes found'}), 404

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
        print("Generating article...")
        try:
            article = generate_article(query, top_recipes)
            print("Article generated successfully!")
        except Exception as e:
            print(f"Error generating article: {e}")
            return jsonify({'error': f'Article generation error: {str(e)}'}), 500
        
        # Extract sources
        sources = [recipe.get('url') for recipe in top_recipes if recipe.get('url')]

        # Surface image hotlink information so downstream systems avoid re-hosting.
        image_hotlinks = []
        for recipe in top_recipes:
            image_url, airtable_field = extract_remote_image_url(recipe)
            if not image_url:
                continue
            image_hotlinks.append({
                'title': recipe.get('title', 'Untitled Recipe'),
                'image_url': image_url,
                'airtable_field': airtable_field,
                'hotlink': True,
            })

        print("=== Recipe Query Completed Successfully ===")

        return jsonify({
            'article': article,
            'sources': sources,
            'recipe_count': len(top_recipes),
            'query': query,
            'total_recipes_searched': len(recipes_cache),
            'removed_recipes': removed_recipes,
            'image_hotlinks': image_hotlinks,
        })
        
    except Exception as e:
        print(f"=== Unexpected Error ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


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
        'message': 'Local Cache Recipe Server',
        'status': 'running',
        'cache_ready': cache_ready,
        'progress': cache_progress,
        'recipes_loaded': len(recipes_cache) if recipes_cache else 0,
        'description': 'Downloads all Airtable data once, then searches locally',
        'endpoints': ['/api/recipe-query', '/health', '/status']
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'cache_ready': cache_ready,
        'progress': cache_progress,
        'recipes_loaded': len(recipes_cache) if recipes_cache else 0
    })

@app.route('/status', methods=['GET'])
def status():
    """Status endpoint for cache progress."""
    return jsonify({
        'cache_ready': cache_ready,
        'progress': cache_progress,
        'recipes_loaded': len(recipes_cache) if recipes_cache else 0
    })

if __name__ == '__main__':
    print("Starting local cache recipe server...")
    
    # Try to load from cache first
    if not load_cached_recipes():
        print("No cache found. Starting background download...")
        # Start background thread to fetch all recipes
        thread = threading.Thread(target=fetch_all_recipes_from_airtable)
        thread.daemon = True
        thread.start()
    
    print("Server ready! (Cache may be loading in background)")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
