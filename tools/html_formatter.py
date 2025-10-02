"""
HTML output generation for recipes.
"""

def generate_html(recipes_list):
    """Generate HTML output for the recipes."""
    if not recipes_list:
        return "<p>No recipes found.</p>"
    
    html_parts = []
    for recipe in recipes_list:
        html = f"""
<h2>{recipe['title']}</h2>
<p>{recipe['description']}</p>"""
        
        if recipe.get('url'):
            html += f'\n<a href="{recipe["url"]}">Source</a>'
        
        html_parts.append(html)
    
    return "\n\n".join(html_parts)
