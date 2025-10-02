"""
FAISS vector store management.
"""

import faiss
import numpy as np
import json
from config import *

def build_faiss_index(recipes):
    """Build FAISS index from recipes with embeddings."""
    print(f"Building FAISS index for {len(recipes)} recipes...")
    
    # Extract embeddings
    embeddings = np.array([recipe["embedding"] for recipe in recipes]).astype('float32')
    
    # Create FAISS index
    dimension = len(embeddings[0])
    index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
    
    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Add embeddings to index
    index.add(embeddings)
    
    # Save index
    faiss.write_index(index, FAISS_INDEX_FILE)
    print(f"FAISS index saved to {FAISS_INDEX_FILE}")
    
    return index

def load_faiss_index():
    """Load existing FAISS index."""
    try:
        index = faiss.read_index(FAISS_INDEX_FILE)
        print(f"Loaded FAISS index from {FAISS_INDEX_FILE}")
        return index
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        return None

def get_id_to_recipe(recipes):
    """Create mapping from recipe ID to recipe object."""
    return {recipe["id"]: recipe for recipe in recipes}
