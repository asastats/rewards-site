"""Testing module for :py:mod:`updaters.main` module."""

import pytest

import updaters
from updaters.main import UPDATER_PROVIDERS_REGISTRY, UpdateProvider


class TestUpdatersMainConstants:
    """Testing class for :py:mod:`updaters.main` fconstants."""

    # UPDATER_PROVIDERS_REGISTRY
    @pytest.mark.parametrize(
        "provider",
        list(UPDATER_PROVIDERS_REGISTRY.keys()),
    )
    def test_updaters_main_updater_providers_registry_functionality(self, provider):
        assert UPDATER_PROVIDERS_REGISTRY[provider] == getattr(
            getattr(updaters, provider), f"{provider.capitalize()}Updater"
        )


class TestUpdatersMainUpdateProvider:
    """Testing class for :class:`updaters.main.UpdateProvider`."""

    @pytest.mark.parametrize(
        "attr",
        ["name", "_updater_instance"],
    )
    def test_updaters_main_updateprovider_inits_attribute_as_none(self, attr):
        assert getattr(UpdateProvider, attr) is None

    # # __init__
    def test_updaters_main_updateprovider_init_functionality(self, mocker):
        mock_get_updater = mocker.patch.object(UpdateProvider, "_get_updater_instance")
        provider = UpdateProvider(platform_name="discord")
        assert provider.name == "discord"
        mock_get_updater.assert_called_once_with()

    # # __getattr__
    def test_updaters_main_updateprovider_getattr(self, mocker):
        provider = UpdateProvider(platform_name="discord")
        assert hasattr(provider, "add_reaction_to_message")
