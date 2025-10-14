"""
Enhanced LLM-based content generation for recipes with multi-section article structure.
"""

from typing import Optional

import openai
from config import *
from .image_utils import build_image_credit, extract_remote_image_url
from .prompt_templates import (
    extract_context,
    INTRO_TEMPLATE,
    RECIPE_SECTION_TEMPLATE,
    COOKING_TIPS_TEMPLATE,
    CONCLUSION_TEMPLATE
)


def _build_image_figure(
    title: str,
    image_url: Optional[str],
    airtable_field: Optional[str],
) -> str:
    """Return a ready-to-use HTML figure that hotlinks the remote recipe image."""
    if not image_url:
        return ""

    caption = build_image_credit(image_url)
    source_field = airtable_field or "unknown"
    return (
        '\n<figure style="margin: 10px 0; text-align: center;" '
        'data-image-hosting="remote" '
        'data-image-hotlink="true" '
        f'data-image-source-field="{source_field}">'
        f'\n<img src="{image_url}" alt="{title}" '
        'width="1280" height="720" '
        'style="width: 100%; max-width: 1280px; height: auto; border-radius: 8px; object-fit: cover;" '
        'loading="lazy" '
        f'data-original-image-url="{image_url}">'
        f'\n<figcaption style="font-size: 0.9em; color: #666; margin-top: 5px; font-style: italic;">{caption}</figcaption>'
        '\n</figure>'
    )

def _deduplicate_recipes(recipes_list):
    """Remove duplicate recipe entries while preserving order."""
    unique_recipes = []
    seen_identifiers = set()

    for recipe in recipes_list:
        identifier = recipe.get("id") or recipe.get("record_id")

        if not identifier:
            title = (recipe.get("title") or "").strip().lower()
            url = (recipe.get("url") or "").strip().lower()
            if title or url:
                identifier = (title, url)
            else:
                identifier = id(recipe)

        if identifier in seen_identifiers:
            continue

        seen_identifiers.add(identifier)
        unique_recipes.append(recipe)

    return unique_recipes



def generate_article(query, recipes_list):
    """Generate a complete multi-section article."""
    if not recipes_list:
        return "No recipes found."

    # Prevent duplicate recipes from appearing in the same article
    unique_recipes = _deduplicate_recipes(recipes_list)
    if len(unique_recipes) < len(recipes_list):
        print(
            f"Removed {len(recipes_list) - len(unique_recipes)} duplicate "
            "recipe(s) before article generation."
        )
    recipes_list = unique_recipes

    # Extract context
    context = extract_context(query)
    
    # Generate each section
    intro = generate_intro(query, context)
    recipe_sections = generate_recipe_sections(recipes_list, context)

    # Combine into complete article without a conclusion section
    article_parts = [intro.strip(), recipe_sections.strip()]
    return "\n\n".join(part for part in article_parts if part)

def generate_intro(query, context):
    """Generate article introduction."""
    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional food writer who creates engaging, appetizing content."},
                {"role": "user", "content": INTRO_TEMPLATE.format(
                    query=query,
                    cuisine=context['cuisine'],
                    number=context['number']
                )}
            ],
            max_tokens=500,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        
        # Ensure content is properly formatted as HTML paragraphs
        if not content.startswith('<p>') and not content.startswith('<h2>'):
            # Split into paragraphs and wrap each in <p> tags
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            if paragraphs:
                content = '\n\n'.join([f'<p>{p}</p>' for p in paragraphs])
            else:
                content = f'<p>{content}</p>'
        
        return content
    except Exception as e:
        print(f"Error generating intro: {e}")
        return f"<p>Welcome to our collection of {context['cuisine']} recipes!</p>"

def generate_recipe_sections(recipes_list, context):
    """Generate individual recipe sections."""
    sections = []
    
    for recipe in recipes_list:
        try:
            response = openai.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional food writer who creates engaging, appetizing content."},
                    {"role": "user", "content": RECIPE_SECTION_TEMPLATE.format(
                        cuisine=context['cuisine'],
                        title=recipe['title'],
                        description=recipe.get('description', '') or f"{recipe.get('ingredients', '')} {recipe.get('instructions', '')}"
                    )}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            section = f"<h2>{recipe['title']}</h2>"
            image_url, airtable_field = extract_remote_image_url(recipe)

            section += _build_image_figure(recipe['title'], image_url, airtable_field)
            
            # Ensure content is properly formatted as HTML paragraph
            content = response.choices[0].message.content.strip()
            
            # If content doesn't have <p> tags, wrap it as a single paragraph
            if not content.startswith('<p>'):
                content = f'<p>{content}</p>'
            
            section += f"\n{content}"
            
            if recipe.get('url'):
                section += f'\n<p><a href="{recipe["url"]}">View Full Recipe</a></p>'
            sections.append(section)
            
        except Exception as e:
            print(f"Error generating section for {recipe['title']}: {e}")
            image_url, airtable_field = extract_remote_image_url(recipe)

            fallback_section = f"<h2>{recipe['title']}</h2>"

            fallback_section += _build_image_figure(
                recipe['title'],
                image_url,
                airtable_field,
            )
            
            # Create a concise fallback description (50-100 words)
            ingredients = recipe.get('ingredients', '')
            instructions = recipe.get('instructions', '')
            fallback_text = f"{ingredients} {instructions}".strip()
            
            # Truncate to approximately 50-100 words if too long
            words = fallback_text.split()
            if len(words) > 100:
                fallback_text = ' '.join(words[:100]) + '...'
            
            fallback_section += f"<p>{fallback_text}</p>"
            
            sections.append(fallback_section)
    
    return "\n\n".join(sections)

def generate_cooking_tips(context):
    """Generate cooking tips section."""
    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional food writer who creates engaging, appetizing content."},
                {"role": "user", "content": COOKING_TIPS_TEMPLATE.format(cuisine=context['cuisine'])}
            ],
            max_tokens=400,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating cooking tips: {e}")
        return f"<p>Master the art of {context['cuisine']} cooking with these essential tips.</p>"

def generate_conclusion(query, context):
    """Generate article conclusion."""
    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional food writer who creates engaging, appetizing content."},
                {"role": "user", "content": CONCLUSION_TEMPLATE.format(
                    query=query,
                    cuisine=context['cuisine']
                )}
            ],
            max_tokens=300,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        
        # Ensure content is properly formatted as HTML paragraphs
        if not content.startswith('<p>') and not content.startswith('<h2>'):
            # Split into paragraphs and wrap each in <p> tags
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            if paragraphs:
                content = '\n\n'.join([f'<p>{p}</p>' for p in paragraphs])
            else:
                content = f'<p>{content}</p>'
        
        return content
    except Exception as e:
        print(f"Error generating conclusion: {e}")
        return f"<h2>Conclusion</h2><p>We hope you enjoy exploring these {context['cuisine']} recipes!</p>"

# Legacy function for backward compatibility
def generate_summary(recipes_list):
    """Legacy function - now generates a simple summary."""
    if not recipes_list:
        return "No recipes found."
    
    recipe_titles = [recipe['title'] for recipe in recipes_list]
    return f"<h2>Found Recipes</h2><ul>" + "".join([f"<li>{title}</li>" for title in recipe_titles]) + "</ul>"
