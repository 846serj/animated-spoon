"""
Structured prompt templates for multi-section article generation.
"""

# Cuisine detection keywords
CUISINE_KEYWORDS = {
    'italian': ['italian', 'italy', 'pasta', 'pizza', 'risotto', 'parmesan', 'basil', 'tomato'],
    'mexican': ['mexican', 'mexico', 'taco', 'burrito', 'enchilada', 'salsa', 'cilantro', 'lime'],
    'chinese': ['chinese', 'china', 'stir-fry', 'wok', 'soy', 'ginger', 'sesame', 'dumpling'],
    'indian': ['indian', 'india', 'curry', 'masala', 'garam', 'tikka', 'naan', 'dal'],
    'french': ['french', 'france', 'bouquet', 'herbes', 'wine', 'butter', 'cream', 'sauce'],
    'thai': ['thai', 'thailand', 'coconut', 'lemongrass', 'fish sauce', 'pad thai', 'curry'],
    'japanese': ['japanese', 'japan', 'sushi', 'miso', 'wasabi', 'teriyaki', 'ramen', 'tempura'],
    'mediterranean': ['mediterranean', 'olive oil', 'feta', 'hummus', 'tzatziki', 'greek', 'lemon'],
    'american': ['american', 'usa', 'bbq', 'burger', 'fries', 'comfort', 'southern', 'tex-mex'],
    'spanish': ['spanish', 'spain', 'paella', 'tapas', 'saffron', 'chorizo', 'gazpacho']
}

def detect_cuisine(query):
    """Extract cuisine type from query."""
    query_lower = query.lower()
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            return cuisine
    return 'general'

def extract_context(query):
    """Extract context from query."""
    import re
    
    # Extract number
    numbers = re.findall(r'\d+', query)
    number = int(numbers[0]) if numbers else len(query.split())
    
    # Detect cuisine
    cuisine = detect_cuisine(query)
    
    return {
        'cuisine': cuisine,
        'number': number,
        'query': query
    }

# Prompt Templates
INTRO_TEMPLATE = """Write a warm, human introduction for an article titled "{query}".

Keep it to 45-65 words in two or three sentences. Start by naturally mentioning the article topic so readers immediately know what they’re getting. Highlight what makes {cuisine} cooking inviting and what the collection of {number} recipes will help them do. Use conversational language, avoid buzzwords or marketing speak, and sound like a real food writer sharing genuine enthusiasm.

IMPORTANT: Format the response as a single <p> tag. The paragraph must be wrapped in <p> and </p> tags. Do NOT include any h2 heading."""

RECIPE_SECTION_TEMPLATE = """Write 45-80 words about this {cuisine} recipe:

Title: {title}
Description: {description}

Lead with the recipe title or its main keyword for SEO clarity, then explain in natural, human voice what makes it special. Highlight cultural context, sensory details, and any smart tips or techniques that capture authentic {cuisine} flavor. Avoid buzzwords and keep the tone warm and conversational, like a trusted food writer.

Format the response as a single HTML paragraph using <p> tags."""

COOKING_TIPS_TEMPLATE = """Write 1-2 paragraphs of general cooking tips for {cuisine} cuisine.

Focus on:
- Essential techniques
- Key ingredients
- Common mistakes to avoid
- Pro tips for authentic flavor

Write in a helpful, encouraging tone that builds confidence in home cooks.

Format the response as HTML paragraphs using <p> tags."""

CONCLUSION_TEMPLATE = """Write a compelling conclusion for an article about {query}.

Tie everything together and encourage readers to try these {cuisine} recipes. End on an inspiring note that makes them excited to start cooking.

Keep it warm and encouraging.

IMPORTANT: Format the response as HTML with <h2>Conclusion</h2> followed by <p> tags for each paragraph. Each paragraph must be wrapped in <p> and </p> tags."""
