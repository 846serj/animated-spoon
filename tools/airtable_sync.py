"""
Airtable integration for fetching recipe data.
"""

import requests
import json
from config import *

def fetch_airtable_records():
    """Fetch all records from Airtable and save to local JSON file."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}"
    }
    
    all_records = []
    offset = None
    
    while True:
        params = {}
        if offset:
            params["offset"] = offset
            
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        all_records.extend(data["records"])
        
        if "offset" in data:
            offset = data["offset"]
        else:
            break
    
    # Convert to our format
    recipes = []
    for record in all_records:
        fields = record.get("fields", {})

        # Preserve every image-related Airtable field so downstream article
        # generators can keep the original hotlinked photography instead of
        # forcing a re-upload to the publishing CMS.
        recipe = {
            "id": record["id"],
            "title": fields.get("Title", ""),
            "description": fields.get("Description", ""),
            "category": fields.get("Category", ""),
            "tags": fields.get("Tags", []),
            "url": fields.get("URL", ""),
            "image_link": fields.get("Image Link", ""),
            "image_url": fields.get("Image URL", ""),
            "image": fields.get("Image", ""),
            "photo": fields.get("Photo", ""),
            "picture": fields.get("Picture", ""),
            "attachments": fields.get("Attachments", []),
        }
        recipes.append(recipe)
    
    # Save to file
    with open(RECIPES_JSON, "w") as f:
        json.dump(recipes, f, indent=2)
    
    print(f"Fetched {len(recipes)} recipes from Airtable")
    return recipes

def sync_and_get_recipes():
    """Convenience function to get latest recipes from Airtable."""
    return fetch_airtable_records()
