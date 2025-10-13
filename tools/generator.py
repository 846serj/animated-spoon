"""
Enhanced LLM-based content generation for recipes with multi-section article structure.
"""

import re
from html import escape
from urllib.parse import urlparse

import openai
from config import *
from .prompt_templates import (
    extract_context,
    INTRO_TEMPLATE,
    RECIPE_SECTION_TEMPLATE,
    COOKING_TIPS_TEMPLATE,
    CONCLUSION_TEMPLATE
)


def _slugify_heading(text):
    """Create a stable slug for heading IDs."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    if not slug:
        slug = "recipe"
    return f"h-{slug}"


def _extract_paragraphs(html_content):
    """Return paragraph content with <p> tags removed."""
    content = (html_content or "").strip()
    if not content:
        return []

    matches = re.findall(r"<p[^>]*>(.*?)</p>", content, flags=re.I | re.S)
    if matches:
        return [match.strip() for match in matches if match.strip()]

    parts = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    if parts:
        return parts

    return [content]


def _format_heading_block(title):
    """Return a Gutenberg heading block for the given title."""
    raw_title = title or "Untitled Recipe"
    safe_title = escape(raw_title)
    heading_id = _slugify_heading(raw_title)
    return (
        f"<!-- wp:heading {{\"id\":\"{heading_id}\"}} -->\n"
        f"<h2 class=\"wp-block-heading\" id=\"{heading_id}\">{safe_title}</h2>\n"
        f"<!-- /wp:heading -->"
    )


def _image_caption_from_url(image_url):
    """Generate a human-readable caption from the image URL domain."""
    try:
        domain = urlparse(image_url).netloc
        if domain:
            return f"Image credit: {domain}"
    except Exception:
        pass
    return "Image credit: Source"


def _format_image_block(image_url, title):
    """Return a Gutenberg image block for the given image."""
    safe_url = escape(image_url.strip())
    safe_title = escape(title or "Recipe image")
    caption = escape(_image_caption_from_url(image_url))
    return (
        "<!-- wp:image -->\n"
        f"<figure class=\"wp-block-image\"><img width=\"1280\" height=\"720\" "
        "style=\"width: 100%; max-width: 1280px; height: auto; border-radius: 8px; object-fit: cover;\" "
        f"src=\"{safe_url}\" alt=\"{safe_title}\"><figcaption style=\"font-size: 0.9em; color: #666; margin-top: 5px; font-style: italic;\">"
        f"{caption}</figcaption></figure>\n"
        "<!-- /wp:image -->"
    )


def _format_paragraph_block(content):
    """Wrap content in a Gutenberg paragraph block without nested <p> tags."""
    cleaned = re.sub(r"</?p[^>]*>", "", content or "", flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = ""
    return (
        "<!-- wp:paragraph -->\n"
        f"<p>{cleaned}</p>\n"
        "<!-- /wp:paragraph -->"
    )


def _find_image_url(recipe):
    """Retrieve the best available image URL for a recipe."""
    if not recipe:
        return None

    for field in [
        "image_link",
        "image_url",
        "image",
        "photo",
        "picture",
        "Image",
        "Photo",
        "Picture",
        "Image URL",
        "Image Link",
    ]:
        value = recipe.get(field)
        if value:
            return value

    attachments = recipe.get("attachments")
    if isinstance(attachments, list) and attachments:
        first = attachments[0]
        if isinstance(first, dict) and first.get("url"):
            return first["url"]
        if isinstance(first, str):
            return first

    return None


def _fallback_description(recipe):
    """Create a concise fallback description using ingredients and instructions."""
    ingredients = recipe.get("ingredients", "") if recipe else ""
    instructions = recipe.get("instructions", "") if recipe else ""
    fallback_text = f"{ingredients} {instructions}".strip()
    words = fallback_text.split()
    if len(words) > 100:
        fallback_text = " ".join(words[:100]) + "..."
    if not fallback_text:
        title = recipe.get("title") if recipe else "Recipe"
        fallback_text = f"Enjoy this {title} recipe."
    return fallback_text


def _prepare_description_text(raw_content, recipe):
    """Normalize model content into a single paragraph with optional link."""
    paragraphs = _extract_paragraphs(raw_content)
    if not paragraphs:
        paragraphs = [_fallback_description(recipe)]

    description = " ".join(part.strip() for part in paragraphs if part.strip())
    description = re.sub(r"\s+", " ", description).strip()
    if not description:
        description = _fallback_description(recipe)

    recipe_url = recipe.get("url") if recipe else None
    if recipe_url:
        description = (
            f"{description} <a href=\"{escape(recipe_url, quote=True)}\">View Full Recipe</a>"
        )

    return description

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
        paragraphs = _extract_paragraphs(content)
        if not paragraphs:
            paragraphs = [content]
        return "\n\n".join(_format_paragraph_block(p) for p in paragraphs if p.strip())
    except Exception as e:
        print(f"Error generating intro: {e}")
        fallback = f"Welcome to our collection of {context['cuisine']} recipes!"
        return _format_paragraph_block(fallback)

def generate_recipe_sections(recipes_list, context):
    """Generate individual recipe sections."""
    sections = []

    for recipe in recipes_list:
        title = recipe.get('title', 'Recipe')
        image_url = _find_image_url(recipe)

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
            content = response.choices[0].message.content.strip()
            description = _prepare_description_text(content, recipe)
        except Exception as e:
            print(f"Error generating section for {recipe['title']}: {e}")
            description = _fallback_description(recipe)

        section_parts = [_format_heading_block(title)]
        if image_url and image_url.strip():
            section_parts.append(_format_image_block(image_url, title))
        section_parts.append(_format_paragraph_block(description))

        sections.append("\n\n".join(section_parts))

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
        content = response.choices[0].message.content.strip()
        paragraphs = _extract_paragraphs(content)
        if not paragraphs:
            paragraphs = [content]
        return "\n\n".join(_format_paragraph_block(p) for p in paragraphs if p.strip())
    except Exception as e:
        print(f"Error generating cooking tips: {e}")
        fallback = f"Master the art of {context['cuisine']} cooking with these essential tips."
        return _format_paragraph_block(fallback)

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
        paragraphs = _extract_paragraphs(content)
        if not paragraphs:
            paragraphs = [content]
        return "\n\n".join(_format_paragraph_block(p) for p in paragraphs if p.strip())
    except Exception as e:
        print(f"Error generating conclusion: {e}")
        fallback = f"We hope you enjoy exploring these {context['cuisine']} recipes!"
        return _format_paragraph_block(fallback)

# Legacy function for backward compatibility
def generate_summary(recipes_list):
    """Legacy function - now generates a simple summary."""
    if not recipes_list:
        return "No recipes found."
    
    recipe_titles = [recipe['title'] for recipe in recipes_list]
    return f"<h2>Found Recipes</h2><ul>" + "".join([f"<li>{title}</li>" for title in recipe_titles]) + "</ul>"
