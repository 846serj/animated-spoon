#!/usr/bin/env python3
"""
Build FAISS index from recipes with embeddings.
"""

import sys
import os

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import embeddings, vector_store

def main():
    print("Loading recipes with embeddings...")
    recipes = embeddings.load_embeddings()
    
    print("Building FAISS index...")
    vector_store.build_faiss_index(recipes)
    
    print("Done!")

if __name__ == "__main__":
    main()
