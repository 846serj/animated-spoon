#!/usr/bin/env python3
"""
Direct Airtable recipe server - queries Airtable directly, no pre-computed data needed.
Much faster and more efficient approach.
"""

import sys
import os
import json
import numpy as np
import openai
import re
import requests
from flask import Flask, request, jsonify

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

def fetch_recipes_from_airtable(query_text="", limit=50):
    """Fetch recipes from Airtable with optional text filtering."""
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID", "appa4SaUbDRFYM42O")
    table_name = os.getenv("AIRTABLE_TABLE_NAME", "Molly's View")
    
    if not api_key:
        raise Exception("AIRTABLE_API_KEY environment variable not set")
    
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Build query parameters
    params = {
        "pageSize": min(limit, 100),  # Airtable max is 100
        "sort[0][field]": "Title",
        "sort[0][direction]": "asc"
    }
    
    # Skip Airtable filtering for now - we'll do it in our code
    # This avoids complex formula syntax issues
    
    all_records = []
    offset = None
    
    while len(all_records) < limit:
        if offset:
            params["offset"] = offset
            
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        all_records.extend(data["records"])
        
        if "offset" in data and len(all_records) < limit:
            offset = data["offset"]
        else:
            break
    
    # Convert Airtable records to recipe format
    recipes = []
    for record in all_records[:limit]:
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

def generate_embedding(text):
    """Generate embedding for a single text."""
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    
    return response.data[0].embedding

def search_recipes_semantic(query, recipes, k=5):
    """Search recipes using semantic similarity."""
    try:
        # Generate embedding for query
        query_embedding = generate_embedding(query)
        
        # Generate embeddings for recipes and calculate similarities
        recipe_scores = []
        for recipe in recipes:
            # Create text for embedding
            recipe_text = f"{recipe['title']} {recipe['ingredients']} {recipe['instructions']}"
            recipe_embedding = generate_embedding(recipe_text)
            
            # Calculate cosine similarity
            similarity = np.dot(query_embedding, recipe_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(recipe_embedding)
            )
            
            recipe_scores.append((recipe, similarity))
        
        # Sort by similarity and return top k
        recipe_scores.sort(key=lambda x: x[1], reverse=True)
        top_recipes = [recipe for recipe, score in recipe_scores[:k]]
        
        return top_recipes
    except Exception as e:
        print(f"Error in semantic search: {e}")
        # Fallback to simple text search
        return search_recipes_text(query, recipes, k)

def search_recipes_text(query, recipes, k=5):
    """Fallback text search."""
    query_lower = query.lower()
    scored_recipes = []
    
    for recipe in recipes:
        score = 0
        text = f"{recipe['title']} {recipe['ingredients']} {recipe['instructions']}".lower()
        
        # Simple scoring based on keyword matches
        for word in query_lower.split():
            if word in text:
                score += text.count(word)
        
        if score > 0:
            scored_recipes.append((recipe, score))
    
    # Sort by score and return top k
    scored_recipes.sort(key=lambda x: x[1], reverse=True)
    return [recipe for recipe, score in scored_recipes[:k]]

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
        print("=== Recipe Query Started ===")
        
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
        api_key = os.getenv("AIRTABLE_API_KEY")
        if not api_key:
            print("Error: AIRTABLE_API_KEY not set")
            return jsonify({'error': 'AIRTABLE_API_KEY environment variable not set'}), 500
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("Error: OPENAI_API_KEY not set")
            return jsonify({'error': 'OPENAI_API_KEY environment variable not set'}), 500
        
        print("Environment variables OK")
        
        # Fetch recipes from Airtable (with text filtering)
        print("Fetching recipes from Airtable...")
        try:
            recipes = fetch_recipes_from_airtable(query_text=query, limit=100)
            print(f"Fetched {len(recipes)} recipes")
        except Exception as e:
            print(f"Error fetching from Airtable: {e}")
            return jsonify({'error': f'Airtable error: {str(e)}'}), 500
        
        if not recipes:
            print("No recipes found")
            return jsonify({'error': 'No recipes found'}), 404
        
        # Search for most relevant recipes
        print("Searching for most relevant recipes...")
        try:
            top_recipes = search_recipes_semantic(query, recipes, k=k)
            print(f"Found {len(top_recipes)} relevant recipes")
        except Exception as e:
            print(f"Error in semantic search: {e}")
            # Fallback to simple text search
            top_recipes = search_recipes_text(query, recipes, k=k)
            print(f"Fallback found {len(top_recipes)} recipes")
        
        if not top_recipes:
            print("No relevant recipes found")
            return jsonify({'error': 'No relevant recipes found'}), 404
        
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
        
        print("=== Recipe Query Completed Successfully ===")
        
        return jsonify({
            'article': article,
            'sources': sources,
            'recipe_count': len(top_recipes),
            'query': query
        })
        
    except Exception as e:
        print(f"=== Unexpected Error ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'message': 'Direct Airtable Recipe Server',
        'status': 'running',
        'description': 'Queries Airtable directly - no pre-computed data needed',
        'endpoints': ['/api/recipe-query', '/health']
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'description': 'Direct Airtable access - always ready'
    })

if __name__ == '__main__':
    print("Starting direct Airtable recipe server...")
    print("No data generation needed - queries Airtable directly!")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 3004))
    print(f"Starting server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)