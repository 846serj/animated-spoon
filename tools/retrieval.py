"""
Recipe search and retrieval functionality.
"""

import numpy as np
import openai
import faiss
from config import *

def search_recipes(query, index, id_to_recipe, category=None, tags=None, k=5):
    """Search for recipes using vector similarity."""
    # Generate query embedding
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query]
    )
    query_embedding = np.array([response.data[0].embedding]).astype('float32')
    
    # Normalize for cosine similarity
    faiss.normalize_L2(query_embedding)
    
    # Search
    scores, indices = index.search(query_embedding, k * 2)  # Get more results for filtering
    
    # Get recipes
    results = []
    seen_recipe_ids = set()
    recipe_ids = list(id_to_recipe.keys())
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:  # Invalid index
            continue

        if idx >= len(recipe_ids):
            continue

        recipe_id = recipe_ids[idx]

        if recipe_id in seen_recipe_ids:
            continue

        recipe = id_to_recipe[recipe_id]

        # Apply filters
        if category and recipe.get("category", "").lower() != category.lower():
            continue
        if tags:
            recipe_tags = [tag.lower() for tag in recipe.get("tags", [])]
            if not any(tag.lower() in recipe_tags for tag in tags):
                continue
        
        results.append(recipe)
        seen_recipe_ids.add(recipe_id)
        if len(results) >= k:
            break
    
    return results
