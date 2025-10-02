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
INTRO_TEMPLATE = """Write a compelling 2-3 paragraph introduction for an article titled "{query}".

Create anticipation and set the scene for {cuisine} cuisine. Mention what makes {cuisine} food special and what readers will discover in this collection of {number} recipes.

Write in an engaging, warm tone that makes readers excited to cook these dishes.

Format the response as HTML paragraphs using <p> tags."""

RECIPE_SECTION_TEMPLATE = """Write an engaging 2 paragraph section about this {cuisine} recipe:

Title: {title}
Description: {description}

Include:
- Why this recipe is special
- Cooking tips or techniques
- Cultural context or flavor notes
- What makes it authentic {cuisine}

Write in engaging food-blog style, keep it professional and new york times style, no buzzwords.

Format the response as HTML paragraphs using <p> tags."""

COOKING_TIPS_TEMPLATE = """Write 1-2 paragraphs of general cooking tips for {cuisine} cuisine.

Focus on:
- Essential techniques
- Key ingredients
- Common mistakes to avoid
- Pro tips for authentic flavor

Write in a helpful, encouraging tone that builds confidence in home cooks.

Format the response as HTML paragraphs using <p> tags."""

CONCLUSION_TEMPLATE = """Write a compelling conclusion paragraph for an article about {query}.

Tie everything together and encourage readers to try these {cuisine} recipes. End on an inspiring note that makes them excited to start cooking.

Keep it warm and encouraging.

Format the response as HTML paragraphs using <p> tags."""
