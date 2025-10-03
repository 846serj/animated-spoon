#!/usr/bin/env python3
"""
Recipe server with automatic data generation on first run.
This handles the case where data files don't exist on Render.
"""

import sys
import os
import json
import faiss
import numpy as np
import openai
import re
import requests
from flask import Flask, request, jsonify

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# Global variables for pre-computed data
recipes = None
index = None
id_to_recipe = None

def fetch_airtable_records():
    """Fetch recipes from Airtable."""
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID", "appa4SaUbDRFYM42O")
    table_name = os.getenv("AIRTABLE_TABLE_NAME", "Molly's View")
    
    if not api_key:
        raise Exception("AIRTABLE_API_KEY environment variable not set")
    
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    all_records = []
    offset = None
    
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
            
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        all_records.extend(data["records"])
        
        if "offset" in data:
            offset = data["offset"]
        else:
            break
    
    # Convert Airtable records to recipe format
    recipes = []
    for record in all_records:
        fields = record.get("fields", {})
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
        }
        recipes.append(recipe)
    
    return recipes

def generate_embeddings_batch(recipes_batch):
    """Generate embeddings for a batch of recipes."""
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    # Create text for embedding
    texts = []
    for recipe in recipes_batch:
        text = f"{recipe['title']} {recipe['ingredients']} {recipe['instructions']}"
        texts.append(text)
    
    # Generate embeddings
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    
    # Add embeddings to recipes
    for i, recipe in enumerate(recipes_batch):
        recipe["embedding"] = response.data[i].embedding
    
    return recipes_batch

def setup_data():
    """Set up recipe data from Airtable with memory optimization."""
    print("Setting up recipe data on Render...")
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    # Fetch recipes
    print("Fetching recipes from Airtable...")
    recipes = fetch_airtable_records()
    print(f"Fetched {len(recipes)} recipes")
    
    # Save raw recipes
    print("Saving raw recipes...")
    with open("data/recipes.json", "w") as f:
        json.dump(recipes, f, indent=2)
    
    # Generate embeddings in small batches
    print("Generating embeddings in small batches...")
    batch_size = 10
    recipes_with_embeddings = []
    
    for i in range(0, len(recipes), batch_size):
        batch = recipes[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(recipes) + batch_size - 1)//batch_size}")
        
        batch_embeddings = generate_embeddings_batch(batch)
        recipes_with_embeddings.extend(batch_embeddings)
        
        # Save progress every 100 recipes
        if len(recipes_with_embeddings) % 100 == 0:
            print(f"Saving progress: {len(recipes_with_embeddings)} recipes processed")
            with open("data/recipes_with_embeddings.json", "w") as f:
                json.dump(recipes_with_embeddings, f)
    
    # Save final embeddings
    print("Saving final embeddings...")
    with open("data/recipes_with_embeddings.json", "w") as f:
        json.dump(recipes_with_embeddings, f)
    
    # Build FAISS index
    print("Building FAISS index...")
    embeddings_matrix = np.array([recipe["embedding"] for recipe in recipes_with_embeddings], dtype=np.float32)
    index = faiss.IndexFlatIP(embeddings_matrix.shape[1])
    index.add(embeddings_matrix)
    faiss.write_index(index, "data/recipes.index")
    
    print("Data setup complete!")
    return len(recipes_with_embeddings)

def load_data():
    """Load pre-computed data files, or create them if they don't exist."""
    global recipes, index, id_to_recipe
    
    print("Loading pre-computed recipe data...")
    
    try:
        # Check if data files exist
        if not os.path.exists("data/recipes_with_embeddings.json") or not os.path.exists("data/recipes.index"):
            print("Data files not found. Setting up data...")
            setup_data()
        
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
        
        # Generate article
        article = generate_article(query, top_recipes)
        
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
    print("Starting recipe server...")
    
    # Load data
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
    
    print("Server ready!")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)