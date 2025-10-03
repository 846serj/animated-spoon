#!/usr/bin/env python3
"""
AWS Lambda function for recipe generation.
Industry standard for enterprise server-to-server AI services.
"""

import json
import os
from tools import retrieval, generator

# Pre-computed data (loaded once per Lambda instance)
recipes = None
index = None
id_to_recipe = None

def load_data():
    """Load pre-computed data (cached per Lambda instance)."""
    global recipes, index, id_to_recipe
    
    if recipes is not None:
        return  # Already loaded
    
    import faiss
    
    # Load recipes from S3 or Lambda layer
    with open("/tmp/data/recipes_with_embeddings.json", "r") as f:
        recipes = json.load(f)
    
    # Load FAISS index
    index = faiss.read_index("/tmp/data/recipes.index")
    
    # Create ID mapping
    id_to_recipe = {recipe["id"]: recipe for recipe in recipes}

def lambda_handler(event, context):
    """AWS Lambda handler."""
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
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
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
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No recipes found'})
            }
        
        # Generate article
        article = generator.generate_article(query, top_recipes)
        
        # Extract sources
        sources = [recipe.get('url') for recipe in top_recipes if recipe.get('url')]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'article': article,
                'sources': sources,
                'recipe_count': len(top_recipes),
                'query': query
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
