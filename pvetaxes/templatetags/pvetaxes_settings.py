from django import template
from ..app_settings import PVETAXES_ALLOW_ANALYTICS

register = template.Library()


@register.simple_tag
def analytics():
    """Return whether analytics are enabled."""
    return PVETAXES_ALLOW_ANALYTICS
