from django import template

register = template.Library()

@register.filter
def is_in(value, arg):
    """Check if value is in the given list or queryset"""
    try:
        return value in arg
    except (TypeError, ValueError):
        return False

@register.filter
def material_completed(material_id, completed_materials):
    """Check if a material is completed by the user"""
    return material_id in completed_materials
