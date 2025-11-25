"""Module containing Django context processors for Django templates."""

from django.conf import settings


def global_constants(request):
    """Return collection of project's constants.

    :param request: HTTP request object
    :type request: :class:`django.http.HttpRequest`
    :return: dict
    """

    return {
        "PROJECT_DOMAIN": settings.PROJECT_DOMAIN,
        # "COMPANY_NAME": settings.COMPANY_NAME,
        # "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
        # "MAX_UPLOAD_SIZE": settings.MAX_UPLOAD_SIZE,
    }
