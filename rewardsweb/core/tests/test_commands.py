"""Testing module for :py:mod:`core.management.commands` module."""

from pathlib import Path
from unittest import mock

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection

from core.management.commands import migrate


class TestDeployDappCommand:
    """Testing class for management command

    :py:mod:`core.management.commands.deploy_dapp`."""

    def test_deploy_dapp_command_output_for_default_network_value(self, mocker):
        app_id = 5050
        mocked_deploy = mocker.patch(
            "core.management.commands.deploy_dapp.deploy_and_setup",
            return_value=app_id,
        )
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("deploy_dapp")
            output_log.assert_called_once_with(
                "Application 5050 successfully deployed on testnet!"
            )
        mocked_deploy.assert_called_once_with("testnet")

    def test_deploy_dapp_command_output_for_provided_network_value(self, mocker):
        app_id = 5051
        mocked_deploy = mocker.patch(
            "core.management.commands.deploy_dapp.deploy_and_setup",
            return_value=app_id,
        )
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("deploy_dapp", network="mainnet")
            output_log.assert_called_once_with(
                "Application 5051 successfully deployed on mainnet!"
            )
        mocked_deploy.assert_called_once_with("mainnet")


class TestExcel2DbCommand:
    """Testing class for management command

    :py:mod:`core.management.commands.excel2db`."""

    def test_excel2db_command_output_for_default_values(self, mocker):
        mocked_convert = mocker.patch(
            "core.management.commands.excel2db.convert_and_clean_excel"
        )
        mocked_import = mocker.patch(
            "core.management.commands.excel2db.import_from_csv", return_value=False
        )
        mocked_map = mocker.patch(
            "core.management.commands.excel2db.map_github_issues", return_value=False
        )
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("excel2db")
            calls = [
                mocker.call("CSV successfully exported into contributions.csv file!"),
                mocker.call("Records successfully imported!"),
                mocker.call("Issues successfully mapped!"),
            ]
            output_log.assert_has_calls(calls, any_order=True)
            assert output_log.call_count == 3

        fixtures_dir = settings.BASE_DIR.parent / "fixtures"
        mocked_convert.assert_called_once_with(
            fixtures_dir / "contributions.xlsx",
            fixtures_dir / "contributions.csv",
            fixtures_dir / "legacy_contributions.csv",
        )
        mocked_import.assert_called_once_with(
            fixtures_dir / "contributions.csv",
            fixtures_dir / "legacy_contributions.csv",
        )
        mocked_map.assert_called_once_with(issue_tracker_api_token="")

    def test_excel2db_command_output_for_default_values_on_import_response(
        self, mocker
    ):
        mocked_convert = mocker.patch(
            "core.management.commands.excel2db.convert_and_clean_excel"
        )
        response = "response"
        mocked_import = mocker.patch(
            "core.management.commands.excel2db.import_from_csv", return_value=response
        )
        mocked_map = mocker.patch("core.management.commands.excel2db.map_github_issues")
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("excel2db")
            calls = [
                mocker.call("CSV successfully exported into contributions.csv file!"),
                mocker.call(response),
            ]
            output_log.assert_has_calls(calls, any_order=True)
            assert output_log.call_count == 2

        fixtures_dir = settings.BASE_DIR.parent / "fixtures"
        mocked_convert.assert_called_once_with(
            fixtures_dir / "contributions.xlsx",
            fixtures_dir / "contributions.csv",
            fixtures_dir / "legacy_contributions.csv",
        )
        mocked_import.assert_called_once_with(
            fixtures_dir / "contributions.csv",
            fixtures_dir / "legacy_contributions.csv",
        )
        mocked_map.assert_not_called()

    def test_excel2db_command_output_for_default_values_on_mapping_response(
        self, mocker
    ):
        mocked_convert = mocker.patch(
            "core.management.commands.excel2db.convert_and_clean_excel"
        )
        response = "response2"
        mocked_import = mocker.patch(
            "core.management.commands.excel2db.import_from_csv", return_value=False
        )
        mocked_map = mocker.patch(
            "core.management.commands.excel2db.map_github_issues",
            return_value=response,
        )
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("excel2db")
            calls = [
                mocker.call("CSV successfully exported into contributions.csv file!"),
                mocker.call("Records successfully imported!"),
                mocker.call(response),
            ]
            output_log.assert_has_calls(calls, any_order=True)
            assert output_log.call_count == 3

        fixtures_dir = settings.BASE_DIR.parent / "fixtures"
        mocked_convert.assert_called_once_with(
            fixtures_dir / "contributions.xlsx",
            fixtures_dir / "contributions.csv",
            fixtures_dir / "legacy_contributions.csv",
        )
        mocked_import.assert_called_once_with(
            fixtures_dir / "contributions.csv",
            fixtures_dir / "legacy_contributions.csv",
        )
        mocked_map.assert_called_once_with(issue_tracker_api_token="")

    def test_excel2db_command_output_for_provided_arguments(self, mocker):
        mocked_convert = mocker.patch(
            "core.management.commands.excel2db.convert_and_clean_excel"
        )
        mocked_import = mocker.patch(
            "core.management.commands.excel2db.import_from_csv", return_value=False
        )
        mocked_map = mocker.patch(
            "core.management.commands.excel2db.map_github_issues", return_value=False
        )
        input_file, output_file, legacy_file, token = (
            "input_file",
            "output_file",
            "legacy_file",
            "token",
        )
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command(
                "excel2db",
                input=input_file,
                output=output_file,
                legacy=legacy_file,
                token=token,
            )
            calls = [
                mocker.call(f"CSV successfully exported into {output_file} file!"),
                mocker.call("Records successfully imported!"),
                mocker.call("Issues successfully mapped!"),
            ]
            output_log.assert_has_calls(calls, any_order=True)
            assert output_log.call_count == 3
        mocked_convert.assert_called_once_with(
            Path(input_file), Path(output_file), Path(legacy_file)
        )
        mocked_import.assert_called_once_with(Path(output_file), Path(legacy_file))
        mocked_map.assert_called_once_with(issue_tracker_api_token=token)


class TestMigrateCommand:
    """Test custom migrate command"""

    @pytest.fixture
    def command(self):
        """Return an instance of the custom command"""
        return migrate.Command()

    @pytest.fixture
    def mock_cursor(self):
        """Mock database cursor"""
        with mock.patch.object(connection, "cursor") as mock_cursor:
            mock_cursor.return_value.__enter__ = mock.MagicMock(
                return_value=mock.MagicMock()
            )
            mock_cursor.return_value.__exit__ = mock.MagicMock(return_value=None)
            yield mock_cursor.return_value.__enter__.return_value

    def test_migrate_command_sync_apps_creates_extension(self, command, mock_cursor):
        """Test that pg_trgm extension is created during sync_apps"""
        with mock.patch(
            "core.management.commands.migrate.MigrateCommand.sync_apps"
        ) as mock_parent_sync:
            result = command.sync_apps(connection, ["test_app"])
            mock_cursor.execute.assert_called_once_with(
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
            )
            mock_parent_sync.assert_called_once_with(connection, ["test_app"])
            assert result == mock_parent_sync.return_value


class TestRunTrackerCommand:
    """Testing class for management command

    :py:mod:`core.management.commands.run_tracker`."""

    def test_run_tracker_command_output_for_wrong_provider(self):
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("run_tracker", provider="foobar")
            output_log.assert_called_once_with("Invalid providr name: foobar")

    @pytest.mark.parametrize(
        "provider",
        ["discord", "reddit", "telegram", "twitter", "twitterapiio"],
    )
    def test_run_tracker_command_output_functionality(self, provider, mocker):
        mocked_run = mocker.patch(
            f"core.management.commands.run_tracker.runners.run_{provider}_tracker"
        )
        with mock.patch(
            "django.core.management.base.OutputWrapper.write"
        ) as output_log:
            call_command("run_tracker", provider=provider)
            output_log.assert_called_once_with(
                f"{provider.capitalize()} tracker exited"
            )
        mocked_run.assert_called_once_with()
