"""
OpenAI embedding generation for recipes.
"""

import openai
import json
import numpy as np
from config import *

# Set up OpenAI client
openai.api_key = OPENAI_API_KEY

def generate_embeddings(recipes):
    """Generate embeddings for a list of recipes."""
    print(f"Generating embeddings for {len(recipes)} recipes...")
    
    # Use smaller batch size for memory efficiency
    batch_size = min(BATCH_SIZE, 25)  # Cap at 25 for memory efficiency
    
    # Prepare text for embedding
    texts = []
    for recipe in recipes:
        text = f"{recipe['title']} {recipe['description']} {recipe['category']} {' '.join(recipe.get('tags', []))}"
        texts.append(text)
    
    # Generate embeddings in batches
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
        
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )
        
        batch_embeddings = [data.embedding for data in response.data]
        embeddings.extend(batch_embeddings)
    
    # Add embeddings to recipes
    for i, recipe in enumerate(recipes):
        recipe["embedding"] = embeddings[i]
    
    return recipes

def save_embeddings(recipes, path=EMBEDDINGS_JSON):
    """Save recipes with embeddings to JSON file."""
    with open(path, "w") as f:
        json.dump(recipes, f, indent=2)
    print(f"Saved {len(recipes)} recipes with embeddings to {path}")

def load_embeddings(path=EMBEDDINGS_JSON):
    """Load recipes with embeddings from JSON file."""
    with open(path, "r") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes with embeddings from {path}")
    return recipes
