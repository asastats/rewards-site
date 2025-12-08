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
        "PROJECT_NAME": f"{settings.PROJECT_OWNER} Rewards",
        "PROJECT_WEBSITE_NAME": f"{settings.PROJECT_OWNER} Rewards website",
        "PROJECT_DOMAIN": settings.PROJECT_DOMAIN,
        "ISSUE_TRACKER": settings.ISSUE_TRACKER_PROVIDER,
    }


def pagination_context(request):
    """Add query_string context for pagination and preserve all GET params but 'page'.

    :param request: HTTP request object
    :type request: :class:`django.http.HttpRequest`
    :var params: request get parameters collection
    :type params: :class:`django.http.QueryDict`
    :var query_string: URL encoded query string
    :type query_string: str
    :return: dict
    """
    params = request.GET.copy()
    if "page" in params:
        del params["page"]

    query_string = params.urlencode()
    return {"query_string": query_string, "has_query_params": bool(query_string)}
