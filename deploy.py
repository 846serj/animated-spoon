#!/usr/bin/env python3
"""
Deployment script to sync data and start server.
Run this on deployment to set up the recipe data.
"""

import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import airtable_sync, embeddings, vector_store

def main():
    print("=== Recipe Server Deployment Setup ===")
    
    # Check if data already exists
    if os.path.exists("data/recipes_with_embeddings.json") and os.path.exists("data/recipes.index"):
        print("Data files already exist, skipping setup...")
        return
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    print("1. Fetching recipes from Airtable...")
    recipes = airtable_sync.fetch_airtable_records()
    
    print("2. Generating embeddings...")
    recipes_with_embeddings = embeddings.generate_embeddings(recipes)
    
    print("3. Saving embeddings...")
    embeddings.save_embeddings(recipes_with_embeddings)
    
    print("4. Building FAISS index...")
    vector_store.build_faiss_index(recipes_with_embeddings)
    
    print("=== Deployment Setup Complete! ===")

if __name__ == "__main__":
    main()
