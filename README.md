# Recipe Writer - RAG Pipeline

A modular RAG (Retrieval-Augmented Generation) pipeline for recipe content creation using OpenAI embeddings and FAISS vector search, with **Airtable integration** as the source of truth.

## Features

- **Airtable Integration**: Automatic sync from Airtable as source of truth
- **Modular Architecture**: Clean separation of concerns with dedicated tool modules
- **Scalable**: Handles 10k+ recipes with batch embedding generation
- **Flexible**: Easy to swap LLMs or vector stores
- **WordPress Ready**: Built-in HTML output generation
- **Remote Image Hotlinking**: Shared helpers guarantee the original Airtable
  image URLs are embedded directly so nothing ever touches the destination
  site's media library
- **Filtered Search**: Search by category and tags
- **Real-time Updates**: Fetch latest data from Airtable on demand

## Project Structure

```
recipe-writer/
│
├── data/
│   ├── recipes.json                    # Input recipe data
│   ├── recipes_with_embeddings.json    # Recipes with generated embeddings
│   └── recipes.index                   # FAISS vector index
│
├── tools/
│   ├── __init__.py
│   ├── airtable_sync.py                # Airtable API integration
│   ├── embeddings.py                   # OpenAI embedding generation
│   ├── vector_store.py                 # FAISS index management
│   ├── retrieval.py                    # Recipe search functionality
│   ├── generator.py                    # LLM-based content generation
│   └── html_formatter.py               # HTML output generation
│
├── scripts/
│   ├── sync_from_airtable.py           # Complete Airtable sync workflow
│   ├── build_embeddings.py             # Generate embeddings for recipes
│   ├── build_faiss_index.py            # Build FAISS vector index
│   ├── draft_recipe_article.py         # One-command article drafting CLI
│   └── run_query.py                    # Example query script
│
├── config.py                           # Configuration settings
├── requirements.txt                    # Python dependencies
├── query                               # Simple CLI for queries
└── README.md
```

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys**:
   Edit `config.py` and set your API keys:
   ```python
   OPENAI_API_KEY = "your-openai-api-key-here"
   AIRTABLE_API_KEY = "your-airtable-api-key-here"
   AIRTABLE_BASE_ID = "your-airtable-base-id"
   AIRTABLE_TABLE_NAME = "Recipes"  # or your table name
   ```

3. **Set up Airtable**:
   Create an Airtable base with a "Recipes" table containing these fields:
   - **Title** (Single line text)
   - **Description** (Long text)
   - **Category** (Single select: Summer, Fall, Winter, Spring)
   - **Tags** (Multiple select: grill, seafood, healthy, etc.)
   - **URL** (URL field)

## Usage

### One-command Article Drafting (Recommended)
```bash
python scripts/draft_recipe_article.py "7 cozy fall soups"
```

The CLI prints the generated HTML plus a list of remote image URLs so you can
verify hotlinking at a glance. Pass `--json` to copy the full payload (article,
sources, hotlinked image metadata) into other tools.

### Simple Query Interface
```bash
./query "your search query here"
```

### Browser-based editor

A lightweight TinyMCE editor is available in `frontend/index.html`. It connects to
`/api/recipe-query` so you can generate a draft, polish the copy directly in the
browser, and then paste it into your CMS. Start any of the Flask servers and
open the file locally:

```bash
python production_server.py  # or your preferred server
# then open frontend/index.html in a browser
```

> **Note:** When opening the file directly from disk the editor will default to
> `http://localhost:3004` for API calls. To use a different domain, set the
> `data-api-base` attribute on the `<body>` tag in `frontend/index.html`.

### Complete Airtable Sync
```bash
python scripts/sync_from_airtable.py
```

### Step-by-Step Process
```bash
# 1. Sync from Airtable and generate embeddings
python scripts/build_embeddings.py

# 2. Build FAISS index
python scripts/build_faiss_index.py

# 3. Run queries
python scripts/run_query.py
```

### Fresh Data Query
```bash
# Fetch latest from Airtable before querying
python scripts/run_query.py --fresh
```

## Configuration

Key settings in `config.py`:

- `OPENAI_API_KEY`: Your OpenAI API key
- `AIRTABLE_API_KEY`: Your Airtable API key
- `AIRTABLE_BASE_ID`: Your Airtable base ID
- `AIRTABLE_TABLE_NAME`: Your Airtable table name (default: "Recipes")
- `EMBEDDING_MODEL`: OpenAI embedding model (default: "text-embedding-3-small")
- `LLM_MODEL`: OpenAI chat model (default: "gpt-4-turbo")
- `TOP_K`: Number of top results to retrieve (default: 10)
- `BATCH_SIZE`: Batch size for embedding generation (default: 100)

## License

MIT License
