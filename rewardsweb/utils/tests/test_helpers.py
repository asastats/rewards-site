"""Testing module for :py:mod:`utils.helpers` module."""

import os
import pickle
from datetime import datetime
from unittest import mock

import pytest
from algosdk import account
from django.core.exceptions import ImproperlyConfigured
from nacl.exceptions import BadSignatureError

from utils.constants.core import MISSING_ENVIRONMENT_VARIABLE_ERROR
from utils.helpers import (
    calculate_transpareny_report_period,
    convert_and_clean_excel,
    get_env_variable,
    humanize_contributions,
    parse_full_handle,
    read_pickle,
    social_platform_prefixes,
    user_display,
    verify_signed_transaction,
)


class TestUtilsHelpersFunctions:
    """Testing class for :py:mod:`utils.helpers` functions."""

    # # calculate_transpareny_report_period
    @pytest.mark.parametrize(
        "month,year,expected_start,expected_end",
        [
            (1, 2024, datetime(2024, 1, 1), datetime(2024, 1, 31)),
            (2, 2023, datetime(2023, 2, 1), datetime(2023, 2, 28)),
            (2, 2024, datetime(2024, 2, 1), datetime(2024, 2, 29)),
            (3, 2024, datetime(2024, 3, 1), datetime(2024, 3, 31)),
            (4, 2024, datetime(2024, 4, 1), datetime(2024, 4, 30)),
            (5, 2024, datetime(2024, 5, 1), datetime(2024, 5, 31)),
            (6, 2024, datetime(2024, 6, 1), datetime(2024, 6, 30)),
            (7, 2024, datetime(2024, 7, 1), datetime(2024, 7, 31)),
            (8, 2024, datetime(2024, 8, 1), datetime(2024, 8, 31)),
            (9, 2024, datetime(2024, 9, 1), datetime(2024, 9, 30)),
            (10, 2024, datetime(2024, 10, 1), datetime(2024, 10, 31)),
            (11, 2024, datetime(2024, 11, 1), datetime(2024, 11, 30)),
            (12, 2024, datetime(2024, 12, 1), datetime(2024, 12, 31)),
        ],
    )
    def test_utils_helpers_calculate_period_monthly_report_valid_cases(
        self, month, year, expected_start, expected_end
    ):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="monthly",
            month=month,
            year=year,
        )
        assert start_date == expected_start
        assert end_date == expected_end

    @pytest.mark.parametrize(
        "quarter,year,expected_start,expected_end",
        [
            (1, 2024, datetime(2024, 1, 1), datetime(2024, 3, 31)),
            (2, 2024, datetime(2024, 4, 1), datetime(2024, 6, 30)),
            (3, 2024, datetime(2024, 7, 1), datetime(2024, 9, 30)),
            (4, 2024, datetime(2024, 10, 1), datetime(2024, 12, 31)),
            (1, 2023, datetime(2023, 1, 1), datetime(2023, 3, 31)),
            (4, 2023, datetime(2023, 10, 1), datetime(2023, 12, 31)),
        ],
    )
    def test_utils_helpers_calculate_period_quarterly_report_valid_cases(
        self, quarter, year, expected_start, expected_end
    ):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="quarterly",
            quarter=quarter,
            year=year,
        )
        assert start_date == expected_start
        assert end_date == expected_end

    @pytest.mark.parametrize(
        "year,expected_start,expected_end",
        [
            (2024, datetime(2024, 1, 1), datetime(2024, 12, 31)),
            (2023, datetime(2023, 1, 1), datetime(2023, 12, 31)),
            (2020, datetime(2020, 1, 1), datetime(2020, 12, 31)),
            (2025, datetime(2025, 1, 1), datetime(2025, 12, 31)),
            (2000, datetime(2000, 1, 1), datetime(2000, 12, 31)),
        ],
    )
    def test_utils_helpers_calculate_period_yearly_report_valid_cases(
        self, year, expected_start, expected_end
    ):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="yearly",
            year=year,
        )
        assert start_date == expected_start
        assert end_date == expected_end

    @pytest.mark.parametrize(
        "start_date_str,end_date_str,expected_start,expected_end",
        [
            ("2024-01-01", "2024-01-31", datetime(2024, 1, 1), datetime(2024, 1, 31)),
            ("2023-12-01", "2024-01-15", datetime(2023, 12, 1), datetime(2024, 1, 15)),
            (
                "2024-02-29",
                "2024-02-29",
                datetime(2024, 2, 29),
                datetime(2024, 2, 29),
            ),
            (
                "2020-01-01",
                "2020-12-31",
                datetime(2020, 1, 1),
                datetime(2020, 12, 31),
            ),
            (
                "2024-03-15",
                "2024-03-20",
                datetime(2024, 3, 15),
                datetime(2024, 3, 20),
            ),
        ],
    )
    def test_utils_helpers_calculate_period_custom_report_valid_cases(
        self, start_date_str, end_date_str, expected_start, expected_end
    ):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="custom",
            start_date_str=start_date_str,
            end_date_str=end_date_str,
        )
        assert start_date == expected_start
        assert end_date == expected_end

    @pytest.mark.parametrize(
        "report_type,params,expected_start,expected_end",
        [
            (
                "monthly",
                {"month": "1", "year": "2024"},
                datetime(2024, 1, 1),
                datetime(2024, 1, 31),
            ),
            (
                "quarterly",
                {"quarter": "2", "year": "2024"},
                datetime(2024, 4, 1),
                datetime(2024, 6, 30),
            ),
            ("yearly", {"year": "2023"}, datetime(2023, 1, 1), datetime(2023, 12, 31)),
        ],
    )
    def test_utils_helpers_calculate_period_string_inputs_converted_correctly(
        self, report_type, params, expected_start, expected_end
    ):
        start_date, end_date = calculate_transpareny_report_period(
            report_type=report_type, **params
        )
        assert start_date == expected_start
        assert end_date == expected_end

    def test_utils_helpers_calculate_period_edge_case_february_leap_year(self):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="monthly",
            month=2,
            year=2024,
        )
        assert start_date == datetime(2024, 2, 1)
        assert end_date == datetime(2024, 2, 29)

    def test_utils_helpers_calculate_period_edge_case_february_non_leap_year(self):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="monthly",
            month=2,
            year=2023,
        )
        assert start_date == datetime(2023, 2, 1)
        assert end_date == datetime(2023, 2, 28)

    def test_utils_helpers_calculate_period_edge_case_custom_same_day(self):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="custom",
            start_date_str="2024-03-15",
            end_date_str="2024-03-15",
        )
        assert start_date == datetime(2024, 3, 15)
        assert end_date == datetime(2024, 3, 15)

    def test_utils_helpers_calculate_period_edge_case_year_boundaries(self):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="yearly",
            year=2024,
        )
        assert start_date.year == 2024
        assert start_date.month == 1
        assert start_date.day == 1
        assert end_date.year == 2024
        assert end_date.month == 12
        assert end_date.day == 31

    def test_utils_helpers_calculate_period_extra_parameters_ignored(self):
        start_date, end_date = calculate_transpareny_report_period(
            report_type="monthly",
            month=3,
            year=2024,
            quarter=2,  # This should be ignored
        )
        assert start_date == datetime(2024, 3, 1)
        assert end_date == datetime(2024, 3, 31)

        # Quarterly report with month parameter (should be ignored)
        start_date, end_date = calculate_transpareny_report_period(
            report_type="quarterly",
            quarter=1,
            year=2024,
            month=5,  # This should be ignored
        )
        assert start_date == datetime(2024, 1, 1)
        assert end_date == datetime(2024, 3, 31)

    # # convert_and_clean_excel
    def test_utils_helpers_convert_and_clean_excel_functionality(self, mocker):
        # Mock the entire pandas read operation chain
        mock_df = mocker.MagicMock()

        # Mock pd.read_excel and all subsequent operations
        mocker.patch("utils.helpers.pd.read_excel").return_value.iloc.return_value = (
            mock_df
        )
        mock_df.fillna.return_value.infer_objects.return_value = mock_df
        mock_df.drop.return_value = mock_df
        mock_df.__getitem__.return_value = mock_df
        mock_df.map.return_value = mock_df
        mock_df.loc.__getitem__.return_value = mock_df

        # Mock the DataFrame slicing operations
        mock_df.iloc.__getitem__.return_value = mock_df

        # Mock pd.concat to avoid real DataFrame operations
        mocker.patch("utils.helpers.pd.concat", return_value=mock_df)

        # Mock Path operations
        mocker.patch(
            "utils.helpers.Path"
        ).return_value.resolve.return_value.parent.parent.__truediv__.return_value.to_csv = (
            mocker.MagicMock()
        )

        # Mock the final to_csv calls
        mock_df.to_csv = mocker.MagicMock()
        mock_df.iloc.__getitem__.return_value.to_csv = mocker.MagicMock()

        convert_and_clean_excel("input.xlsx", "output.csv", "legacy.csv")

        # Verify the function completed
        assert mock_df.to_csv.called

    # # get_env_variable
    def test_utils_helpers_get_env_variable_access_and_returns_os_environ_key(self):
        var_name = "SECRET_KEY"
        old_value = os.environ[var_name]
        value = "some value"
        os.environ[var_name] = value
        returned = get_env_variable(var_name)
        os.environ[var_name] = old_value
        assert returned == value

    def test_utils_helpers_get_env_variable_raises_for_wrong_variable(self):
        name = "NON_EXISTING_VARIABLE_NAME"
        with pytest.raises(ImproperlyConfigured) as exception:
            get_env_variable(name)
        assert str(exception.value) == "{} {}!".format(
            name, MISSING_ENVIRONMENT_VARIABLE_ERROR
        )

    def test_utils_helpers_get_env_variable_returns_default(self):
        name = "NON_EXISTING_VARIABLE_NAME"
        default = "default"
        assert get_env_variable(name, default) == default

    def test_utils_helpers_get_env_variable_functionality(self):
        assert "settings" in get_env_variable("DJANGO_SETTINGS_MODULE")

    # # humanize_contributions
    def test_utils_helpers_humanize_contributions_empty_queryset(self, mocker):
        contributions = mocker.MagicMock()
        contributions.__iter__ = mocker.MagicMock(return_value=iter([]))

        result = humanize_contributions(contributions)

        assert result == []

    def test_utils_helpers_humanize_contributions_single_contribution(self, mocker):
        contribution = mocker.MagicMock()
        contribution.id = 1
        contribution.contributor.name = "John Doe"
        contribution.cycle.id = 5
        contribution.platform.name = "GitHub"
        contribution.url = "https://github.com/test/repo"
        contribution.reward.type = "Bug Fix"
        contribution.reward.level = "A"
        contribution.percentage = "25.50"
        contribution.reward.amount = "100.00"
        contribution.confirmed = True

        contributions = mocker.MagicMock()
        contributions.__iter__ = mocker.MagicMock(return_value=iter([contribution]))

        result = humanize_contributions(contributions)

        expected = [
            {
                "id": 1,
                "contributor_name": "John Doe",
                "cycle_id": 5,
                "platform": "GitHub",
                "url": "https://github.com/test/repo",
                "type": "Bug Fix",
                "level": "A",
                "percentage": "25.50",
                "reward": "100.00",
                "confirmed": True,
            }
        ]
        assert result == expected

    def test_utils_helpers_humanize_contributions_multiple_contributions(self, mocker):
        contribution1 = mocker.MagicMock()
        contribution1.id = 1
        contribution1.contributor.name = "John Doe"
        contribution1.cycle.id = 5
        contribution1.platform.name = "GitHub"
        contribution1.url = "https://github.com/test/repo"
        contribution1.reward.type = "Bug Fix"
        contribution1.reward.level = "A"
        contribution1.percentage = "25.50"
        contribution1.reward.amount = "100.00"
        contribution1.confirmed = True

        contribution2 = mocker.MagicMock()
        contribution2.id = 2
        contribution2.contributor.name = "Jane Smith"
        contribution2.cycle.id = 5
        contribution2.platform.name = "Discord"
        contribution2.url = "https://discord.com/test"
        contribution2.reward.type = "Feature"
        contribution2.reward.level = "B"
        contribution2.percentage = "15.25"
        contribution2.reward.amount = "75.50"
        contribution2.confirmed = False

        contributions = mocker.MagicMock()
        contributions.__iter__ = mocker.MagicMock(
            return_value=iter([contribution1, contribution2])
        )

        result = humanize_contributions(contributions)

        expected = [
            {
                "id": 1,
                "contributor_name": "John Doe",
                "cycle_id": 5,
                "platform": "GitHub",
                "url": "https://github.com/test/repo",
                "type": "Bug Fix",
                "level": "A",
                "percentage": "25.50",
                "reward": "100.00",
                "confirmed": True,
            },
            {
                "id": 2,
                "contributor_name": "Jane Smith",
                "cycle_id": 5,
                "platform": "Discord",
                "url": "https://discord.com/test",
                "type": "Feature",
                "level": "B",
                "percentage": "15.25",
                "reward": "75.50",
                "confirmed": False,
            },
        ]
        assert result == expected

    def test_utils_helpers_humanize_contributions_with_none_values(self, mocker):
        contribution = mocker.MagicMock()
        contribution.id = 1
        contribution.contributor.name = None
        contribution.cycle.id = None
        contribution.platform.name = None
        contribution.url = None
        contribution.reward.type = None
        contribution.reward.level = None
        contribution.percentage = None
        contribution.reward.amount = None
        contribution.confirmed = None

        contributions = mocker.MagicMock()
        contributions.__iter__ = mocker.MagicMock(return_value=iter([contribution]))

        result = humanize_contributions(contributions)

        expected = [
            {
                "id": 1,
                "contributor_name": None,
                "cycle_id": None,
                "platform": None,
                "url": None,
                "type": None,
                "level": None,
                "percentage": None,
                "reward": None,
                "confirmed": None,
            }
        ]
        assert result == expected

    def test_utils_helpers_humanize_contributions_verify_all_fields_present(
        self, mocker
    ):
        contribution = mocker.MagicMock()
        contribution.id = 1
        contribution.contributor.name = "Test User"
        contribution.cycle.id = 1
        contribution.platform.name = "Test Platform"
        contribution.url = "https://test.com"
        contribution.reward.type = "Test Type"
        contribution.reward.level = "C"
        contribution.percentage = "10.00"
        contribution.reward.amount = "50.00"
        contribution.confirmed = False

        contributions = mocker.MagicMock()
        contributions.__iter__ = mocker.MagicMock(return_value=iter([contribution]))

        result = humanize_contributions(contributions)

        assert len(result) == 1
        humanized = result[0]
        assert "id" in humanized
        assert "contributor_name" in humanized
        assert "cycle_id" in humanized
        assert "platform" in humanized
        assert "url" in humanized
        assert "type" in humanized
        assert "level" in humanized
        assert "percentage" in humanized
        assert "reward" in humanized
        assert "confirmed" in humanized
        assert len(humanized.keys()) == 10  # Verify no extra fields

    # # parse_full_handle
    @pytest.mark.parametrize(
        "full_handle,prefix,handle",
        [
            ("u/user1", "u/", "user1"),
            ("address", "", "address"),
            ("g@address", "g@", "address"),
            ("handle", "", "handle"),
            ("@handle", "@", "handle"),
            ("u/username", "u/", "username"),
            ("username", "", "username"),
            ("@address", "@", "address"),
            ("t@handle", "t@", "handle"),
            ("g@handle", "g@", "handle"),
        ],
    )
    def test_core_modelsparse_full_handle_functionality(
        self, full_handle, prefix, handle
    ):
        assert parse_full_handle(full_handle) == (prefix, handle)

    # # read_pickle
    def test_utils_helpers_read_pickle_returns_empty_dict_for_no_file(self, mocker):
        path = mocker.MagicMock()
        with (
            mock.patch(
                "utils.helpers.os.path.exists", return_value=False
            ) as mocked_exist,
            mock.patch("utils.helpers.open") as mocked_open,
        ):
            assert read_pickle(path) == {}
            mocked_exist.assert_called_once_with(path)
            mocked_open.assert_not_called()

    def test_utils_helpers_read_pickle_returns_empty_dict_for_exception(self, mocker):
        path = mocker.MagicMock()
        with (
            mock.patch("utils.helpers.os.path.exists", return_value=True),
            mock.patch("utils.helpers.open") as mocked_open,
            mock.patch(
                "utils.helpers.pickle.load", side_effect=pickle.PickleError("Corrupted")
            ),
        ):
            assert read_pickle(path) == {}
            mocked_open.assert_called_once_with(path, "rb")

    def test_utils_helpers_read_pickle_returns_pickle_file_content(self, mocker):
        path = mocker.MagicMock()
        expected_data = {"key": "value", "list": [1, 2, 3]}
        with (
            mock.patch("utils.helpers.os.path.exists", return_value=True),
            mock.patch("utils.helpers.open") as mocked_open,
            mock.patch(
                "utils.helpers.pickle.load", return_value=expected_data
            ) as mocked_load,
        ):
            assert read_pickle(path) == expected_data
            mocked_open.assert_called_once_with(path, "rb")
            mocked_load.assert_called_once_with(
                mocked_open.return_value.__enter__.return_value
            )

    def test_utils_helpers_read_pickle_handles_eoferror(self, mocker):
        path = mocker.MagicMock()
        with (
            mock.patch("utils.helpers.os.path.exists", return_value=True),
            mock.patch("utils.helpers.open"),
            mock.patch(
                "utils.helpers.pickle.load", side_effect=EOFError("Unexpected EOF")
            ),
        ):
            assert read_pickle(path) == {}

    def test_utils_helpers_read_pickle_handles_attribute_error(self, mocker):
        path = mocker.MagicMock()
        with (
            mock.patch("utils.helpers.os.path.exists", return_value=True),
            mock.patch("utils.helpers.open"),
            mock.patch(
                "utils.helpers.pickle.load",
                side_effect=AttributeError("Missing attribute"),
            ),
        ):
            assert read_pickle(path) == {}

    def test_utils_helpers_read_pickle_handles_import_error(self, mocker):
        path = mocker.MagicMock()
        with (
            mock.patch("utils.helpers.os.path.exists", return_value=True),
            mock.patch("utils.helpers.open"),
            mock.patch(
                "utils.helpers.pickle.load", side_effect=ImportError("Missing module")
            ),
        ):
            assert read_pickle(path) == {}

    # # social_platform_prefixes
    def test_utils_helpers_social_platform_prefixes(self):
        result = social_platform_prefixes()

        expected = [
            ("Discord", ""),
            ("Twitter", "@"),
            ("Reddit", "u/"),
            ("GitHub", "g@"),
            ("Telegram", "t@"),
            ("Forum", "f@"),
        ]
        assert result == expected

    # # user_display
    def test_utils_helpers_user_display_calls_and_returns_profile_name(self, mocker):
        user = mocker.MagicMock()
        returned = user_display(user)
        assert returned == user.profile.name

    # verify_signed_transaction
    def test_verify_signed_transaction_valid_signature(self, mocker):
        """Test verify_signed_transaction with a valid signature."""
        # Generate a real address for testing
        _, address = account.generate_account()

        # Create a mock signed transaction
        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = "valid_signature_base64"
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.transaction.sender = address
        mock_stxn.authorizing_address = None

        with (
            mock.patch("utils.helpers.VerifyKey") as mock_verify_key,
            mock.patch("utils.helpers.encoding.decode_address") as mock_decode_address,
            mock.patch("utils.helpers.base64.b64decode") as mock_b64decode,
            mock.patch("utils.helpers.encoding.msgpack_encode") as mock_msgpack_encode,
        ):
            # Set up mocks to simulate successful verification
            mock_verify_key_instance = mock_verify_key.return_value
            mock_verify_key_instance.verify.return_value = (
                None  # No exception means success
            )

            mock_decode_address.return_value = b"mocked_public_key_bytes"
            mock_b64decode.return_value = b"mocked_decoded_data"
            mock_msgpack_encode.return_value = "mocked_encoded_transaction"

            result = verify_signed_transaction(mock_stxn)

            assert result is True
            mock_verify_key.assert_called_once_with(b"mocked_public_key_bytes")
            mock_verify_key_instance.verify.assert_called_once_with(
                b"TX" + b"mocked_decoded_data", b"mocked_decoded_data"
            )

    def test_verify_signed_transaction_invalid_signature(self, mocker):
        """Test verify_signed_transaction with an invalid signature."""
        _, address = account.generate_account()

        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = "invalid_signature_base64"
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.transaction.sender = address
        mock_stxn.authorizing_address = None

        with (
            mock.patch("utils.helpers.VerifyKey") as mock_verify_key,
            mock.patch("utils.helpers.encoding.decode_address"),
            mock.patch("utils.helpers.base64.b64decode") as mock_b64decode,
            mock.patch("utils.helpers.encoding.msgpack_encode"),
        ):
            mock_verify_key_instance = mock_verify_key.return_value
            mock_verify_key_instance.verify.side_effect = BadSignatureError(
                "Invalid signature"
            )

            mock_b64decode.return_value = b"mocked_data"

            result = verify_signed_transaction(mock_stxn)

            assert result is False
            mock_verify_key_instance.verify.assert_called_once()

    def test_verify_signed_transaction_no_signature(self, mocker):
        """Test verify_signed_transaction with no signature."""
        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = None
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.authorizing_address = None

        result = verify_signed_transaction(mock_stxn)

        assert result is False

    def test_verify_signed_transaction_empty_signature(self, mocker):
        """Test verify_signed_transaction with empty signature."""
        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = ""
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.authorizing_address = None

        result = verify_signed_transaction(mock_stxn)

        assert result is False

    def test_verify_signed_transaction_with_authorizing_address(self, mocker):
        """Test verify_signed_transaction with authorizing_address (rekeying case)."""
        _, address = account.generate_account()
        _, auth_address = account.generate_account()  # Different address for rekeying

        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = "valid_signature_base64"
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.transaction.sender = address
        mock_stxn.authorizing_address = (
            auth_address  # This should be used instead of sender
        )

        with (
            mock.patch("utils.helpers.VerifyKey") as mock_verify_key,
            mock.patch("utils.helpers.encoding.decode_address") as mock_decode_address,
            mock.patch("utils.helpers.base64.b64decode") as mock_b64decode,
            mock.patch("utils.helpers.encoding.msgpack_encode") as mock_msgpack_encode,
        ):
            mock_verify_key_instance = mock_verify_key.return_value
            mock_verify_key_instance.verify.return_value = None

            mock_decode_address.return_value = b"mocked_auth_public_key_bytes"
            mock_b64decode.return_value = b"mocked_decoded_data"
            mock_msgpack_encode.return_value = "mocked_encoded_transaction"

            result = verify_signed_transaction(mock_stxn)

            assert result is True
            # Verify that authorizing_address was used instead of sender
            mock_decode_address.assert_called_with(auth_address)
            mock_verify_key.assert_called_once_with(b"mocked_auth_public_key_bytes")

    @pytest.mark.parametrize(
        "signature_value,expected",
        [
            (None, False),
            ("", False),
            ("valid_signature", True),
        ],
    )
    def test_verify_signed_transaction_signature_edge_cases(
        self, mocker, signature_value, expected
    ):
        """Test various edge cases for signature field."""
        _, address = account.generate_account()

        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = signature_value
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.transaction.sender = address
        mock_stxn.authorizing_address = None

        if signature_value == "valid_signature":
            # Setup mocks for the case where we expect True
            with (
                mock.patch("utils.helpers.VerifyKey") as mock_verify_key,
                mock.patch("utils.helpers.encoding.decode_address"),
                mock.patch("utils.helpers.base64.b64decode"),
                mock.patch("utils.helpers.encoding.msgpack_encode"),
            ):
                mock_verify_key_instance = mock_verify_key.return_value
                mock_verify_key_instance.verify.return_value = None

                result = verify_signed_transaction(mock_stxn)
                assert result == expected
        else:
            result = verify_signed_transaction(mock_stxn)
            assert result == expected

    def test_verify_signed_transaction_base64_decoding(self, mocker):
        """Test that base64 decoding is called correctly."""
        _, address = account.generate_account()

        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = "signature_base64_data"
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.transaction.sender = address
        mock_stxn.authorizing_address = None

        with (
            mock.patch("utils.helpers.VerifyKey") as mock_verify_key,
            mock.patch("utils.helpers.encoding.decode_address"),
            mock.patch("utils.helpers.base64.b64decode") as mock_b64decode,
            mock.patch("utils.helpers.encoding.msgpack_encode") as mock_msgpack_encode,
        ):
            mock_verify_key_instance = mock_verify_key.return_value
            mock_verify_key_instance.verify.return_value = None

            # Set up different return values for different calls to b64decode
            def b64decode_side_effect(arg):
                if arg == "signature_base64_data":
                    return b"decoded_signature"
                elif arg == "encoded_transaction_data":
                    return b"decoded_transaction"
                return b"default_decoded_data"

            mock_b64decode.side_effect = b64decode_side_effect
            mock_msgpack_encode.return_value = "encoded_transaction_data"

            verify_signed_transaction(mock_stxn)

            # Verify base64.b64decode was called with the correct arguments
            assert mock_b64decode.call_count == 2
            mock_b64decode.assert_any_call("signature_base64_data")
            mock_b64decode.assert_any_call("encoded_transaction_data")

            # Verify verify was called with the correct prefixed message
            expected_prefixed_message = b"TX" + b"decoded_transaction"
            mock_verify_key_instance.verify.assert_called_once_with(
                expected_prefixed_message, b"decoded_signature"
            )

    def test_verify_signed_transaction_public_key_decoding(self, mocker):
        """Test that public key decoding works correctly."""
        _, address = account.generate_account()

        mock_stxn = mocker.MagicMock()
        mock_stxn.signature = "signature_base64"
        mock_stxn.transaction = mocker.MagicMock()
        mock_stxn.transaction.sender = address
        mock_stxn.authorizing_address = None

        with (
            mock.patch("utils.helpers.VerifyKey") as mock_verify_key,
            mock.patch("utils.helpers.encoding.decode_address") as mock_decode_address,
            mock.patch("utils.helpers.base64.b64decode"),
            mock.patch("utils.helpers.encoding.msgpack_encode"),
        ):
            mock_verify_key_instance = mock_verify_key.return_value
            mock_verify_key_instance.verify.return_value = None

            mock_decode_address.return_value = b"decoded_public_key_bytes"

            verify_signed_transaction(mock_stxn)

            # Verify decode_address was called with the correct sender address
            mock_decode_address.assert_called_once_with(address)
            # Verify VerifyKey was instantiated with the decoded public key
            mock_verify_key.assert_called_once_with(b"decoded_public_key_bytes")
