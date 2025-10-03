"""
Enhanced LLM-based content generation for recipes with multi-section article structure.
"""

import openai
from config import *
from .prompt_templates import (
    extract_context, 
    INTRO_TEMPLATE, 
    RECIPE_SECTION_TEMPLATE, 
    COOKING_TIPS_TEMPLATE, 
    CONCLUSION_TEMPLATE
)

def generate_article(query, recipes_list):
    """Generate a complete multi-section article."""
    if not recipes_list:
        return "No recipes found."
    
    # Extract context
    context = extract_context(query)
    
    # Generate each section
    intro = generate_intro(query, context)
    recipe_sections = generate_recipe_sections(recipes_list, context)
    conclusion = generate_conclusion(query, context)
    
    # Combine into complete article
    article = f"""{intro}

{recipe_sections}

{conclusion}"""
    
    return article

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
        return f"<h2>Introduction</h2><p>Welcome to our collection of {context['cuisine']} recipes!</p>"

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
                        description=recipe['description']
                    )}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            # Get image URL from any of the possible image fields
            image_url = recipe.get('image_url') or recipe.get('image') or recipe.get('photo') or recipe.get('picture')
            
            section = f"<h2>{recipe['title']}</h2>"
            
            # Add image if available
            if image_url and image_url.strip():
                section += f'\n<img src="{image_url}" alt="{recipe["title"]}" style="max-width: 100%; height: auto; margin: 10px 0; border-radius: 8px;">'
            
            # Ensure content is properly formatted as HTML paragraphs
            content = response.choices[0].message.content.strip()
            
            # If content doesn't have <p> tags, wrap it
            if not content.startswith('<p>'):
                # Split into paragraphs and wrap each in <p> tags
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                if paragraphs:
                    content = '\n\n'.join([f'<p>{p}</p>' for p in paragraphs])
                else:
                    content = f'<p>{content}</p>'
            
            section += f"\n{content}"
            
            if recipe.get('url'):
                section += f'\n<p><a href="{recipe["url"]}">View Full Recipe</a></p>'
            sections.append(section)
            
        except Exception as e:
            print(f"Error generating section for {recipe['title']}: {e}")
            # Get image URL from any of the possible image fields
            image_url = recipe.get('image_url') or recipe.get('image') or recipe.get('photo') or recipe.get('picture')
            
            fallback_section = f"<h2>{recipe['title']}</h2>"
            
            # Add image if available
            if image_url and image_url.strip():
                fallback_section += f'\n<img src="{image_url}" alt="{recipe["title"]}" style="max-width: 100%; height: auto; margin: 10px 0; border-radius: 8px;">'
            
            fallback_section += f"<p>{recipe.get('description', recipe.get('ingredients', ''))}</p>"
            
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
