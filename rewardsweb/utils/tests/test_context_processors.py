"""Testing module for :py:mod:`utils.context_processors` module."""

from django.conf import settings
from django.http import QueryDict

from utils.context_processors import global_constants, pagination_context


class TestUtilsContextProcessorsFunctions:
    """Testing class for :py:mod:`utils.context_processors` functions."""

    # # global_constants
    def test_utils_context_processors_global_constants_functionality(self, mocker):
        returned = global_constants(mocker.MagicMock())
        assert returned == {
            "PROJECT_OWNER": settings.PROJECT_OWNER,
            "PROJECT_NAME": f"{settings.PROJECT_OWNER} Rewards",
            "PROJECT_WEBSITE_NAME": f"{settings.PROJECT_OWNER} Rewards website",
            "PROJECT_DOMAIN": settings.PROJECT_DOMAIN,
            "ISSUE_TRACKER": settings.ISSUE_TRACKER_PROVIDER,
            "AVAILABLE_THEMES": settings.AVAILABLE_THEMES,
        }

    # # pagination_context
    def test_utils_context_processors_pagination_context_for_no_query(self, mocker):
        request = mocker.MagicMock()
        request.GET = QueryDict("page=1")
        returned = pagination_context(request)
        assert returned == {"query_string": "", "has_query_params": False}

    def test_utils_context_processors_pagination_context_functionality(self, mocker):
        request = mocker.MagicMock()
        request.GET = QueryDict("foo=bar&foobar=1&page=10")
        returned = pagination_context(request)
        assert returned == {
            "query_string": "foo=bar&foobar=1",
            "has_query_params": True,
        }
