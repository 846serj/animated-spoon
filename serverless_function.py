#!/usr/bin/env python3
"""
Serverless function approach - industry standard for AI/ML services.
Deploy to Vercel, Netlify Functions, or AWS Lambda.
"""

import json
import os
from tools import retrieval
from tools.drafting import prepare_article_payload, DEFAULT_BLOCKED_IMAGE_DOMAINS

# Pre-computed data (loaded once per function instance)
recipes = None
index = None
id_to_recipe = None

def load_data():
    """Load pre-computed data (cached per function instance)."""
    global recipes, index, id_to_recipe
    
    if recipes is not None:
        return  # Already loaded
    
    import faiss
    
    # Load recipes
    with open("data/recipes_with_embeddings.json", "r") as f:
        recipes = json.load(f)
    
    # Load FAISS index
    index = faiss.read_index("data/recipes.index")
    
    # Create ID mapping
    id_to_recipe = {recipe["id"]: recipe for recipe in recipes}

def handler(event, context=None):
    """Main handler function."""
    try:
        # Load data if not already loaded
        load_data()
        
        # Parse request
        if isinstance(event, dict) and 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        query = body.get('query', '')
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Query is required'})
            }
        
        # Extract number from query
        import re
        numbers = re.findall(r'\d+', query)
        k = int(numbers[0]) if numbers else 5
        
        # Retrieve recipes
        top_recipes = retrieval.search_recipes(query, index, id_to_recipe, k=k)
        
        if not top_recipes:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No recipes found'})
            }
        
        payload, removed = prepare_article_payload(
            query,
            top_recipes,
            blocked_domains=DEFAULT_BLOCKED_IMAGE_DOMAINS,
        )

        if not payload:
            return {
                'statusCode': 502,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'No recipes with accessible images found',
                    'removed_recipes': removed,
                })
            }

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(payload)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

# For local testing
if __name__ == "__main__":
    test_event = {
        'body': json.dumps({'query': '5 italian pasta dishes'})
    }
    result = handler(test_event)
    print(json.dumps(result, indent=2))
