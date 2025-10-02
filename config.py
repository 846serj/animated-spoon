import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appa4SaUbDRFYM42O")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Molly's View")

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4-turbo"
TOP_K = 10
BATCH_SIZE = 100
RECIPES_JSON = "data/recipes.json"
EMBEDDINGS_JSON = "data/recipes_with_embeddings.json"
FAISS_INDEX_FILE = "data/recipes.index"
