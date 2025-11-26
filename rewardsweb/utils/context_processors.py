"""Module containing Django context processors for Django templates."""

from django.conf import settings


def global_constants(request):
    """Return collection of project's constants.

    :param request: HTTP request object
    :type request: :class:`django.http.HttpRequest`
    :return: dict
    """
    return {
        "PROJECT_OWNER": settings.PROJECT_OWNER,
        "PROJECT_NAME": f"{settings.PROJECT_OWNER} Rewards" ,
        "PROJECT_WEBSITE_NAME": f"{settings.PROJECT_OWNER} Rewards website" ,
        "PROJECT_DOMAIN": settings.PROJECT_DOMAIN,
    }
