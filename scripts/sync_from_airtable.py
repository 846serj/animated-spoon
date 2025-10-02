#!/usr/bin/env python3
"""
Complete workflow: sync from Airtable, build embeddings, and create FAISS index.
"""

import sys
import os

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import airtable_sync, embeddings, vector_store

def main():
    print("=== Complete Airtable Sync Workflow ===")
    
    # Step 1: Fetch from Airtable
    print("\n1. Fetching recipes from Airtable...")
    recipes = airtable_sync.fetch_airtable_records()
    
    # Step 2: Generate embeddings
    print("\n2. Generating embeddings...")
    recipes_with_embeddings = embeddings.generate_embeddings(recipes)
    
    # Step 3: Save embeddings
    print("\n3. Saving embeddings...")
    embeddings.save_embeddings(recipes_with_embeddings)
    
    # Step 4: Build FAISS index
    print("\n4. Building FAISS index...")
    vector_store.build_faiss_index(recipes_with_embeddings)
    
    print("\n=== Workflow Complete! ===")
    print("You can now run queries using: ./query \"your search query\"")

if __name__ == "__main__":
    main()
