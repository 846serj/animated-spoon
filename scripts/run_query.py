#!/usr/bin/env python3
"""
Example script to run a query against the recipe database.
Usage: python scripts/run_query.py [--fresh]
  --fresh: Fetch latest data from Airtable before searching
"""

import json
import sys
import os
import argparse

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import airtable_sync, embeddings, vector_store, retrieval, generator, html_formatter
from config import *

def main():
    parser = argparse.ArgumentParser(description='Run recipe queries')
    parser.add_argument('--fresh', action='store_true', 
                       help='Fetch latest data from Airtable before searching')
    args = parser.parse_args()

    if args.fresh:
        print("Fetching latest recipes from Airtable...")
        airtable_sync.fetch_airtable_records()
        print("Note: You'll need to rebuild embeddings and FAISS index for fresh data")
        print("Run: python scripts/build_embeddings.py && python scripts/build_faiss_index.py")
        return

    # Load recipes with embeddings
    print("Loading recipes with embeddings...")
    recipes = embeddings.load_embeddings()

    # Load FAISS index
    print("Loading FAISS index...")
    index = vector_store.load_faiss_index()
    id_to_recipe = vector_store.get_id_to_recipe(recipes)

    # User query
    query = "12 italian dinners you don't wanna miss"
    print(f"Searching for: {query}")

    # Extract number from query (default to 5 if no number found)
    import re
    numbers = re.findall(r'\d+', query)
    k = int(numbers[0]) if numbers else 5

    # Retrieve recipes
    top_recipes = retrieval.search_recipes(query, index, id_to_recipe, k=k)
    
    print(f"Found {len(top_recipes)} matching recipes")

    # Generate grounded summary
    print("Generating summary...")
    summary = generator.generate_summary(top_recipes)

    # Generate HTML
    print("Generating HTML...")
    html_output = html_formatter.generate_html(top_recipes)

    print("=== Summary ===\n", summary)
    print("\n=== HTML Output ===\n", html_output)

if __name__ == "__main__":
    main()
