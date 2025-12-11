"""Module containing project's template tags and filters."""

from django import template
from django.contrib import messages

register = template.Library()


@register.inclusion_tag("includes/messages_toast.html")
def messages_toast(request):
    """Render Django messages as toast data attributes."""
    message_list = list(messages.get_messages(request))
    return {"django_messages": message_list}
