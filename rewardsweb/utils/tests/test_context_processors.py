"""Testing module for :py:mod:`utils.context_processors` module."""

from django.conf import settings

from utils.context_processors import global_constants


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
        }
