"""Testing module for :py:mod:`contract.reporting` module."""

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from contract.helpers import read_json
from contract.reporting import (
    INDEXER_ADDRESS,
    INDEXER_FETCH_LIMIT,
    INDEXER_PAGE_DELAY,
    INDEXER_TOKEN,
    _address_transaction,
    _create_chronological_group,
    _create_transaction_entry,
    _fetch_asset_data,
    _format_amount,
    _format_date,
    _format_paragraph,
    _format_url,
    _group_transactions_by_type,
    _group_transactions_chronological,
    _indexer_instance,
    _parse_transaction,
    _parse_transactions,
    _search_transactions_by_address,
    create_transparency_report,
    fetch_app_allocations,
)


class TestContractReportingIndexerFunctions:
    """Testing class for :py:mod:`contract.reporting` indexer functions."""

    # # _address_transaction
    def test_contract_reporting_address_transaction_functionality_for_no_transactions(
        self, mocker
    ):
        address, min_round, indexer_client = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        mocked_pause = mocker.patch("contract.reporting.pause")
        mocked_search = mocker.patch(
            "contract.reporting._search_transactions_by_address",
            return_value={"transactions": []},
        )
        params = {"limit": INDEXER_FETCH_LIMIT, "min_round": min_round}
        yielded = list(_address_transaction(address, min_round, indexer_client))
        assert yielded == []
        mocked_pause.assert_called_once_with(INDEXER_PAGE_DELAY)
        mocked_search.assert_called_once_with(
            address, params, indexer_client, delay=INDEXER_PAGE_DELAY
        )

    def test_contract_reporting_address_transaction_functionality(self, mocker):
        address, min_round, indexer_client = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        mocked_pause = mocker.patch("contract.reporting.pause")
        txn1, txn2, txn3, txn4, txn5 = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        token1, token2 = (mocker.MagicMock(), mocker.MagicMock())
        mocked_search = mocker.patch(
            "contract.reporting._search_transactions_by_address",
            side_effect=[
                {"transactions": [txn1, txn2, txn3], "next-token": token1},
                {"transactions": [txn4, txn5], "next-token": token2},
                {"transactions": [], "next-token": mocker.MagicMock()},
            ],
        )
        params = {"limit": INDEXER_FETCH_LIMIT, "min_round": min_round}
        yielded = list(_address_transaction(address, min_round, indexer_client))
        assert yielded == [txn1, txn2, txn3, txn4, txn5]
        mocked_pause.assert_called_with(INDEXER_PAGE_DELAY)
        assert mocked_pause.call_count == 3
        calls = [
            mocker.call(address, params, indexer_client, delay=INDEXER_PAGE_DELAY),
            mocker.call(
                address,
                params,
                indexer_client,
                next_page=token1,
                delay=INDEXER_PAGE_DELAY,
            ),
            mocker.call(
                address,
                params,
                indexer_client,
                next_page=token2,
                delay=INDEXER_PAGE_DELAY,
            ),
        ]
        mocked_search.assert_has_calls(calls, any_order=True)
        assert mocked_search.call_count == 3

    def test_contract_reporting_address_transaction_provided_delay_and_limit(
        self, mocker
    ):
        address, min_round, indexer_client = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        mocked_pause = mocker.patch("contract.reporting.pause")
        txn1, txn2, txn3, txn4, txn5 = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        token1, token2 = (mocker.MagicMock(), mocker.MagicMock())
        mocked_search = mocker.patch(
            "contract.reporting._search_transactions_by_address",
            side_effect=[
                {"transactions": [txn1, txn2, txn3], "next-token": token1},
                {"transactions": [txn4, txn5], "next-token": token2},
                {"transactions": [], "next-token": mocker.MagicMock()},
            ],
        )
        delay, limit = 0.1, 55
        params = {"limit": limit, "min_round": min_round}
        yielded = list(
            _address_transaction(
                address, min_round, indexer_client, delay=delay, limit=limit
            )
        )
        assert yielded == [txn1, txn2, txn3, txn4, txn5]
        mocked_pause.assert_called_with(delay)
        assert mocked_pause.call_count == 3
        calls = [
            mocker.call(address, params, indexer_client, delay=delay),
            mocker.call(address, params, indexer_client, next_page=token1, delay=delay),
            mocker.call(address, params, indexer_client, next_page=token2, delay=delay),
        ]
        mocked_search.assert_has_calls(calls, any_order=True)
        assert mocked_search.call_count == 3

    def test_contract_reporting_address_transaction_appends_named_arguments(
        self, mocker
    ):
        address, min_round, indexer_client, max_round, token1 = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        mocker.patch("contract.reporting.pause")
        mocked_search = mocker.patch(
            "contract.reporting._search_transactions_by_address",
            side_effect=[
                {
                    "transactions": [
                        mocker.MagicMock(),
                    ],
                    "next-token": token1,
                },
                {"transactions": [], "next-token": mocker.MagicMock()},
            ],
        )
        params = {
            "limit": INDEXER_FETCH_LIMIT,
            "min_round": min_round,
            "max_round": max_round,
        }
        list(
            _address_transaction(
                address, min_round, indexer_client, max_round=max_round
            )
        )
        calls = [
            mocker.call(address, params, indexer_client, delay=INDEXER_PAGE_DELAY),
            mocker.call(
                address,
                params,
                indexer_client,
                next_page=token1,
                delay=INDEXER_PAGE_DELAY,
            ),
        ]
        mocked_search.assert_has_calls(calls, any_order=True)
        assert mocked_search.call_count == 2

    def test_contract_reporting_fetch_asset_data_functionality(self, mocker):
        asset_ids = {0, 12345, 67890}
        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.reporting._indexer_instance", return_value=client
        )
        client.asset_info.side_effect = [
            {"asset": {"params": {"unit-name": "ASSET1", "decimals": 3}}},
            {"asset": {"params": {"unit-name": "ASSET2", "decimals": 6}}},
        ]
        data = _fetch_asset_data(asset_ids)
        expected = {
            0: {"unit": "ALGO", "decimals": 6},
            12345: {"unit": "ASSET1", "decimals": 3},
            67890: {"unit": "ASSET2", "decimals": 6},
        }
        assert data == expected
        mocked_client.assert_called_once_with()
        client.asset_info.assert_has_calls([mocker.call(12345), mocker.call(67890)])

    # # _indexer_instance
    def test_contract_reporting_indexer_instance_functionality(self, mocker):
        mocked_indexer = mocker.patch("contract.reporting.IndexerClient")
        returned = _indexer_instance()
        assert returned == mocked_indexer.return_value
        mocked_indexer.assert_called_once_with(
            INDEXER_TOKEN, INDEXER_ADDRESS, headers={"User-Agent": "algosdk"}
        )

    # # _search_transactions_by_address
    def test_contract_reporting_search_transactions_by_address_for_default(
        self, mocker
    ):
        indexer_client, txns = (mocker.MagicMock(), mocker.MagicMock())
        address = "address1"
        params = {"foo": "bar"}
        mocked_pause = mocker.patch("contract.reporting.pause")
        indexer_client.search_transactions_by_address.return_value = txns
        returned = _search_transactions_by_address(address, params, indexer_client)
        assert returned == txns
        mocked_pause.assert_called_once_with(1)
        indexer_client.search_transactions_by_address.assert_called_once_with(
            address, **params
        )

    def test_contract_reporting_search_transactions_by_address_for_next_page(
        self, mocker
    ):
        indexer_client, txns = (mocker.MagicMock(), mocker.MagicMock())
        address = "address1"
        params = {"foo": "bar"}
        next_page = "next_page"
        mocked_pause = mocker.patch("contract.reporting.pause")
        indexer_client.search_transactions_by_address.return_value = txns
        returned = _search_transactions_by_address(
            address, params, indexer_client, next_page
        )
        assert returned == txns
        mocked_pause.assert_called_once_with(1)
        indexer_client.search_transactions_by_address.assert_called_once_with(
            address, next_page="next_page", **params
        )

    def test_contract_reporting_search_transactions_by_address_logs_error_default_vals(
        self, mocker
    ):
        address = "address1"
        params = {"foo": "bar"}
        indexer_client, txns = (mocker.MagicMock(), mocker.MagicMock())
        mocked_pause = mocker.patch("contract.reporting.pause")
        indexer_client.search_transactions_by_address.side_effect = [
            Exception("a"),
            Exception("b"),
            txns,
        ]
        with mock.patch("contract.reporting.logger") as mocked_logger:
            returned = _search_transactions_by_address(address, params, indexer_client)
            assert returned == txns
            calls = [
                mocker.call(
                    "Exception a raised searching transactions: %s; Paused..."
                    % ({"foo": "bar"})
                ),
                mocker.call(
                    "Exception b raised searching transactions: %s; Paused..."
                    % ({"foo": "bar"})
                ),
            ]
            mocked_logger.error.assert_has_calls(calls, any_order=True)
            assert mocked_logger.error.call_count == 2
        calls = [mocker.call(1), mocker.call(5)]
        mocked_pause.assert_has_calls(calls, any_order=True)
        assert mocked_pause.call_count == 5

    def test_contract_reporting_search_transactions_by_address_logs_error_provided_vals(
        self, mocker
    ):
        indexer_client, txns = (mocker.MagicMock(), mocker.MagicMock())
        address = "address1"
        params = {"foo": "bar"}
        mocked_pause = mocker.patch("contract.reporting.pause")
        delay = 0.5
        error_delay = 10
        indexer_client.search_transactions_by_address.side_effect = [
            Exception("a"),
            Exception("b"),
            txns,
        ]
        with mock.patch("contract.reporting.logger") as mocked_logger:
            returned = _search_transactions_by_address(
                address, params, indexer_client, delay=delay, error_delay=error_delay
            )
            assert returned == txns
            calls = [
                mocker.call(
                    "Exception a raised searching transactions: %s; Paused..."
                    % ({"foo": "bar"})
                ),
                mocker.call(
                    "Exception b raised searching transactions: %s; Paused..."
                    % ({"foo": "bar"})
                ),
            ]
            mocked_logger.error.assert_has_calls(calls, any_order=True)
            assert mocked_logger.error.call_count == 2
        calls = [mocker.call(delay), mocker.call(error_delay)]
        mocked_pause.assert_has_calls(calls, any_order=True)
        assert mocked_pause.call_count == 5

    def test_contract_reporting_search_transactions_by_address_exits_max_retries(
        self, mocker
    ):
        indexer_client = mocker.MagicMock()
        address = "address1"
        params = {"foo": "bar"}
        mocked = mocker.patch("contract.reporting.pause")
        indexer_client.search_transactions_by_address.side_effect = [Exception("")] * 20
        with mock.patch("contract.reporting.logger") as mocked_logger:
            with pytest.raises(ValueError) as exception:
                _search_transactions_by_address(address, params, indexer_client)
                assert "Maximum number of retries reached" in str(exception.value)
            calls = [
                mocker.call(
                    "Exception  raised searching transactions: %s; Paused..."
                    % ({"foo": "bar"})
                ),
                mocker.call("Maximum number of retries reached. Exiting..."),
            ]
            mocked_logger.error.assert_has_calls(calls, any_order=True)
            assert mocked_logger.error.call_count == 21
        calls = [mocker.call(1), mocker.call(5)]
        mocked.assert_has_calls(calls, any_order=True)
        assert mocked.call_count == 41

    def test_contract_reporting_search_transactions_by_address_exits_max_retries_vals(
        self, mocker
    ):
        indexer_client = mocker.MagicMock()
        address = "address1"
        params = {"foo": "bar"}
        mocked_pause = mocker.patch("contract.reporting.pause")
        retries = 10
        indexer_client.search_transactions_by_address.side_effect = [
            Exception("")
        ] * retries
        with mock.patch("contract.reporting.logger") as mocked_logger:
            with pytest.raises(ValueError) as exception:
                _search_transactions_by_address(
                    address, params, indexer_client, retries=retries
                )
                assert "Maximum number of retries reached" in str(exception.value)
            calls = [
                mocker.call(
                    "Exception  raised searching transactions: %s; Paused..."
                    % ({"foo": "bar"})
                ),
                mocker.call("Maximum number of retries reached. Exiting..."),
            ]
            mocked_logger.error.assert_has_calls(calls, any_order=True)
            assert mocked_logger.error.call_count == retries + 1
        calls = [mocker.call(1), mocker.call(5)]
        mocked_pause.assert_has_calls(calls, any_order=True)
        assert mocked_pause.call_count == retries * 2 + 1

    # # fetch_app_allocations
    def test_contract_reporting_fetch_app_allocations_no_existing_transactions(
        self, mocker
    ):
        app_id = 750934138
        mocked_app_id = mocker.patch(
            "contract.reporting.app_id_from_contract", return_value=app_id
        )
        filename = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "2ASZE-R274Q.json"
        )
        mocked_read = mocker.patch("contract.reporting.read_json", return_value={})
        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.reporting._indexer_instance", return_value=client
        )
        min_round = 15000
        client.applications.return_value = {
            "application": {"created-at-round": min_round}
        }
        txns = [{"confirmed-round": 20000}, {"confirmed-round": 10000}]
        mocked_txn = mocker.patch(
            "contract.reporting._address_transaction", return_value=txns
        )
        result = [{"confirmed-round": 10000}, {"confirmed-round": 20000}]
        json_file = mocker.MagicMock()
        with mock.patch(
            "contract.reporting.open",
            return_value=json_file,
        ) as mocked_open, mock.patch("contract.reporting.json.dump") as mocked_dump:
            returned = fetch_app_allocations()
            mocked_open.assert_called_once_with(filename, "w")
            mocked_dump.assert_called_once_with(
                result, json_file.__enter__.return_value
            )
        assert returned == result
        mocked_app_id.assert_called_once_with()
        mocked_read.assert_called_once_with(filename)
        mocked_client.assert_called_once_with()
        mocked_txn.assert_called_once_with(
            "2ASZECPEH4ALJWHFN2MKPAS355GC6MDARIC3MFVZCN6NJF76HZPU4R274Q",
            min_round,
            client,
        )
        client.applications.assert_called_once_with(app_id)

    def test_contract_reporting_fetch_app_allocations_no_new_transactions(self, mocker):
        app_id = 750934138
        mocked_app_id = mocker.patch(
            "contract.reporting.app_id_from_contract", return_value=app_id
        )
        txns = [{"confirmed-round": 10000}, {"confirmed-round": 20000}]
        filename = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "2ASZE-R274Q.json"
        )
        mocked_read = mocker.patch("contract.reporting.read_json", return_value=txns)
        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.reporting._indexer_instance", return_value=client
        )
        mocked_txn = mocker.patch(
            "contract.reporting._address_transaction", return_value=[]
        )
        returned = fetch_app_allocations()
        assert returned == txns
        mocked_app_id.assert_called_once_with()
        mocked_read.assert_called_once_with(filename)
        mocked_client.assert_called_once_with()
        mocked_txn.assert_called_once_with(
            "2ASZECPEH4ALJWHFN2MKPAS355GC6MDARIC3MFVZCN6NJF76HZPU4R274Q", 20001, client
        )
        client.applications.return_value.assert_not_called()

    def test_contract_reporting_fetch_app_allocations_force_update_false(self, mocker):
        app_id = 750934138
        mocked_app_id = mocker.patch(
            "contract.reporting.app_id_from_contract", return_value=app_id
        )
        txns = [{"confirmed-round": 10000}, {"confirmed-round": 20000}]
        filename = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "2ASZE-R274Q.json"
        )
        mocked_read = mocker.patch("contract.reporting.read_json", return_value=txns)
        mocked_client = mocker.patch("contract.reporting._indexer_instance")
        mocked_txn = mocker.patch("contract.reporting._address_transaction")
        result = [{"confirmed-round": 10000}, {"confirmed-round": 20000}]
        returned = fetch_app_allocations(force_update=False)
        assert returned == result
        mocked_app_id.assert_called_once_with()
        mocked_read.assert_called_once_with(filename)
        mocked_client.assert_not_called()
        mocked_txn.assert_not_called()

    def test_contract_reporting_fetch_app_allocations_no_existing_forse_false(
        self, mocker
    ):
        app_id = 750934138
        mocked_app_id = mocker.patch(
            "contract.reporting.app_id_from_contract", return_value=app_id
        )
        filename = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "2ASZE-R274Q.json"
        )
        mocked_read = mocker.patch("contract.reporting.read_json", return_value={})
        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.reporting._indexer_instance", return_value=client
        )
        min_round = 15000
        client.applications.return_value = {
            "application": {"created-at-round": min_round}
        }
        txns = [{"confirmed-round": 20000}, {"confirmed-round": 10000}]
        mocked_txn = mocker.patch(
            "contract.reporting._address_transaction", return_value=txns
        )
        result = [{"confirmed-round": 10000}, {"confirmed-round": 20000}]
        json_file = mocker.MagicMock()
        with mock.patch(
            "contract.reporting.open",
            return_value=json_file,
        ) as mocked_open, mock.patch("contract.reporting.json.dump") as mocked_dump:
            returned = fetch_app_allocations(force_update=False)
            mocked_open.assert_called_once_with(filename, "w")
            mocked_dump.assert_called_once_with(
                result, json_file.__enter__.return_value
            )
        assert returned == result
        mocked_app_id.assert_called_once_with()
        mocked_read.assert_called_once_with(filename)
        mocked_client.assert_called_once_with()
        mocked_txn.assert_called_once_with(
            "2ASZECPEH4ALJWHFN2MKPAS355GC6MDARIC3MFVZCN6NJF76HZPU4R274Q",
            min_round,
            client,
        )
        client.applications.assert_called_once_with(app_id)

    def test_contract_reporting_fetch_app_allocations_functionality(self, mocker):
        app_id = 750934138
        mocked_app_id = mocker.patch(
            "contract.reporting.app_id_from_contract", return_value=app_id
        )
        txns = [{"confirmed-round": 10000}, {"confirmed-round": 20000}]
        new_txns = [{"confirmed-round": 30000}, {"confirmed-round": 25000}]
        filename = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "2ASZE-R274Q.json"
        )
        mocked_read = mocker.patch("contract.reporting.read_json", return_value=txns)
        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.reporting._indexer_instance", return_value=client
        )
        mocked_txn = mocker.patch(
            "contract.reporting._address_transaction", return_value=new_txns
        )
        result = [
            {"confirmed-round": 10000},
            {"confirmed-round": 20000},
            {"confirmed-round": 25000},
            {"confirmed-round": 30000},
        ]
        json_file = mocker.MagicMock()
        with mock.patch(
            "contract.reporting.open",
            return_value=json_file,
        ) as mocked_open, mock.patch("contract.reporting.json.dump") as mocked_dump:
            returned = fetch_app_allocations()
            mocked_open.assert_called_once_with(filename, "w")
            mocked_dump.assert_called_once_with(
                result, json_file.__enter__.return_value
            )
        assert returned == result
        mocked_app_id.assert_called_once_with()
        mocked_read.assert_called_once_with(filename)
        mocked_client.assert_called_once_with()
        mocked_txn.assert_called_once_with(
            "2ASZECPEH4ALJWHFN2MKPAS355GC6MDARIC3MFVZCN6NJF76HZPU4R274Q", 20001, client
        )
        client.applications.return_value.assert_not_called()


class TestContractReportingParsingFunctions:
    """Testing class for :py:mod:`contract.reporting` parsing functions."""

    def setup_method(self):
        self.address = "2ASZECPEH4ALJWHFN2MKPAS355GC6MDARIC3MFVZCN6NJF76HZPU4R274Q"
        self.transactions = read_json(
            Path(__file__).resolve().parent / "fixture-2ASZE-R274Q.json"
        )

    # # _create_chronological_group
    def test_contract_reporting_create_chronological_group_functionality(self):
        txn = {
            "asset": 1,
            "amount": 100,
            "id": "id1",
            "round-time": 1000,
            "round": 10,
            "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
        }
        group = _create_chronological_group(txn)
        assert group == {
            "asset": 1,
            "amount": 100,
            "start": {"id": "id1", "round-time": 1000, "round": 10},
            "count": 1,
            "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
        }

        txn_receiver = {
            "asset": 2,
            "amount": 200,
            "group": "group2",
            "round-time": 2000,
            "round": 20,
            "receiver": self.address,
        }
        group_receiver = _create_chronological_group(txn_receiver)
        assert group_receiver == {
            "asset": 2,
            "amount": 200,
            "start": {"group": "group2", "round-time": 2000, "round": 20},
            "count": 1,
        }

    # # _create_transaction_entry
    def test_contract_reporting_create_transaction_entry_functionality(self):
        txn_with_group = {"group": "test_group", "round-time": 100, "round": 10}
        entry = _create_transaction_entry(txn_with_group)
        assert entry == {"group": "test_group", "round-time": 100, "round": 10}

        txn_with_id = {"id": "test_id", "round-time": 200, "round": 20}
        entry = _create_transaction_entry(txn_with_id)
        assert entry == {"id": "test_id", "round-time": 200, "round": 20}

        txn_both = {
            "id": "test_id",
            "group": "test_group",
            "round-time": 300,
            "round": 30,
        }
        entry = _create_transaction_entry(txn_both)
        assert entry == {"group": "test_group", "round-time": 300, "round": 30}

    # # _group_transactions_by_type
    def test_contract_reporting_group_transactions_by_type_functionality(self):
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2026, 1, 1)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        grouped = _group_transactions_by_type(parsed)
        expected = [
            {
                "asset": 0,
                "amount": 500000,
                "count": 1,
                "start": {
                    "id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ",
                    "round-time": 1764675278,
                    "round": 58090657,
                },
                "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
            {
                "asset": 123755640,
                "amount": 645000000000,
                "count": 3,
                "start": {
                    "group": "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE=",
                    "round-time": 1764684142,
                    "round": 58093976,
                },
                "end": {
                    "group": "4yMdnSBzKTU/WuHiiOnNxzhscADlBQkdetBqIRqyirw=",
                    "round-time": 1764838035,
                    "round": 58151503,
                },
                "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
            {
                "asset": 123755640,
                "amount": -195000000000,
                "count": 4,
                "start": {
                    "id": "XSO5Q5S4ADPSRCJFKEA4TNOJFLZYHE7KJTH3SJ6FW2SWYTHOLXJQ",
                    "round-time": 1764837992,
                    "round": 58151487,
                },
                "end": {
                    "id": "XTIG4HP3NN7YOWULX53RB6JGOLP3YO5CL4GTQUPS3ABCOEF4UXEQ",
                    "round-time": 1764838019,
                    "round": 58151497,
                },
                "receiver": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
        ]

        assert grouped == expected

    def test_contract_reporting_group_transactions_by_type_for_empty_data(
        self,
    ):
        grouped = _group_transactions_by_type([])
        assert grouped == []

    def test_contract_reporting_group_transactions_by_type_for_creator_receiver(
        self,
    ):
        start_date = datetime.fromtimestamp(1764837992, tz=timezone.utc)
        end_date = datetime.fromtimestamp(1764837992, tz=timezone.utc)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        grouped = _group_transactions_by_type(parsed)
        expected = [
            {
                "asset": 123755640,
                "amount": -100000000000,
                "count": 1,
                "start": {
                    "id": "XSO5Q5S4ADPSRCJFKEA4TNOJFLZYHE7KJTH3SJ6FW2SWYTHOLXJQ",
                    "round-time": 1764837992,
                    "round": 58151487,
                },
                "receiver": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            }
        ]
        assert grouped == expected

    # # _group_transactions_chronological
    def test_contract_reporting_group_transactions_chronological_functionality(self):
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2026, 1, 1)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        grouped = _group_transactions_chronological(parsed)
        expected = [
            {
                "asset": 0,
                "amount": 500000,
                "count": 1,
                "start": {
                    "id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ",
                    "round-time": 1764675278,
                    "round": 58090657,
                },
                "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
            {
                "asset": 123755640,
                "amount": 195000000000,
                "count": 1,
                "start": {
                    "group": "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE=",
                    "round-time": 1764684142,
                    "round": 58093976,
                },
                "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
            {
                "asset": 123755640,
                "amount": -195000000000,
                "count": 4,
                "start": {
                    "id": "XSO5Q5S4ADPSRCJFKEA4TNOJFLZYHE7KJTH3SJ6FW2SWYTHOLXJQ",
                    "round-time": 1764837992,
                    "round": 58151487,
                },
                "end": {
                    "id": "XTIG4HP3NN7YOWULX53RB6JGOLP3YO5CL4GTQUPS3ABCOEF4UXEQ",
                    "round-time": 1764838019,
                    "round": 58151497,
                },
                "receiver": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
            {
                "asset": 123755640,
                "amount": 450000000000,
                "count": 2,
                "start": {
                    "group": "+LLeR+KDBcDoJPL5zjPoeXu8knIi7cCAKH/H1p/RCyA=",
                    "round-time": 1764838030,
                    "round": 58151501,
                },
                "end": {
                    "group": "4yMdnSBzKTU/WuHiiOnNxzhscADlBQkdetBqIRqyirw=",
                    "round-time": 1764838035,
                    "round": 58151503,
                },
                "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            },
        ]
        assert grouped == expected

    def test_contract_reporting_group_transactions_chronological_for_empty_data(self):
        # _parse_transaction
        # axfer, sender and receiver are not address
        txn = {
            "tx-type": "axfer",
            "asset-transfer-transaction": {
                "amount": 100,
                "asset-id": 1,
                "receiver": "another_address",
            },
            "sender": "sender",
        }
        top_txn = {"id": "top_id", "group": "top_group"}
        assert not _parse_transaction(txn, self.address, top_txn)
        # pay, sender and receiver are not address
        txn = {
            "tx-type": "pay",
            "payment-transaction": {
                "amount": 50,
                "receiver": "another_address",
            },
            "sender": "sender",
        }
        assert not _parse_transaction(txn, self.address, top_txn)
        # _parse_transactions
        start_date = datetime(2026, 1, 1)
        end_date = datetime(2027, 1, 1)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        assert parsed == []
        # group_transactions_chronological
        grouped = _group_transactions_chronological([])
        assert grouped == []
        parsed = [
            {"asset": 1, "amount": 100, "id": "id1", "round-time": None, "round": None},
            {"asset": 1, "amount": 200, "id": "id2", "round-time": None, "round": None},
            {"asset": 2, "amount": 300, "id": "id3", "round-time": None, "round": None},
        ]
        grouped = _group_transactions_chronological(parsed)
        expected = [
            {
                "asset": 1,
                "amount": 300,
                "start": {"id": "id1", "round-time": None, "round": None},
                "end": {"id": "id2", "round-time": None, "round": None},
                "count": 2,
            },
            {
                "asset": 2,
                "amount": 300,
                "start": {"id": "id3", "round-time": None, "round": None},
                "count": 1,
            },
        ]
        assert grouped == expected

    def test_contract_reporting_group_transactions_chronological_for_creator_receiver(
        self,
    ):
        start_date = datetime.fromtimestamp(1764837992, tz=timezone.utc)
        end_date = datetime.fromtimestamp(1764837992, tz=timezone.utc)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        grouped = _group_transactions_chronological(parsed)
        expected = [
            {
                "asset": 123755640,
                "amount": -100000000000,
                "count": 1,
                "start": {
                    "id": "XSO5Q5S4ADPSRCJFKEA4TNOJFLZYHE7KJTH3SJ6FW2SWYTHOLXJQ",
                    "round-time": 1764837992,
                    "round": 58151487,
                },
                "receiver": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
            }
        ]

        assert grouped == expected

    # # _parse_transaction
    def test_contract_reporting_parse_transaction_functionality(self):
        # axfer, amount > 0, receiver is address
        txn = {
            "tx-type": "axfer",
            "asset-transfer-transaction": {
                "amount": 100,
                "asset-id": 1,
                "receiver": self.address,
            },
            "sender": "sender",
        }
        top_txn = {
            "id": "top_id",
            "group": "top_group",
            "round-time": 12345,
            "confirmed-round": 123,
        }
        parsed = _parse_transaction(txn, self.address, top_txn)
        assert parsed == {
            "group": "top_group",
            "round-time": 12345,
            "round": 123,
            "asset": 1,
            "amount": 100,
            "sender": "sender",
        }
        # axfer, amount > 0, sender is address
        txn["asset-transfer-transaction"]["receiver"] = "another_address"
        txn["sender"] = self.address
        parsed = _parse_transaction(txn, self.address, top_txn)
        assert parsed == {
            "group": "top_group",
            "round-time": 12345,
            "round": 123,
            "asset": 1,
            "amount": -100,
            "receiver": "another_address",
        }
        # axfer, amount == 0
        txn["asset-transfer-transaction"]["amount"] = 0
        assert not _parse_transaction(txn, self.address, top_txn)
        # pay, receiver is address
        txn = {
            "tx-type": "pay",
            "payment-transaction": {"amount": 50, "receiver": self.address},
            "sender": "sender",
        }
        top_txn = {"id": "top_id", "round-time": 12345, "confirmed-round": 123}
        parsed = _parse_transaction(txn, self.address, top_txn)
        assert parsed == {
            "id": "top_id",
            "round-time": 12345,
            "round": 123,
            "asset": 0,
            "amount": 50,
            "sender": "sender",
        }
        # pay, sender is address
        txn["payment-transaction"]["receiver"] = "another_address"
        txn["sender"] = self.address
        parsed = _parse_transaction(txn, self.address, top_txn)
        assert parsed == {
            "id": "top_id",
            "round-time": 12345,
            "round": 123,
            "asset": 0,
            "amount": -50,
            "receiver": "another_address",
        }
        # other type
        txn = {"tx-type": "appl"}
        assert not _parse_transaction(txn, self.address, top_txn)

    def test_contract_reporting_parse_transaction_for_no_id(self):
        # axfer, amount > 0, receiver is address
        txn = {
            "tx-type": "axfer",
            "asset-transfer-transaction": {
                "amount": 100,
                "asset-id": 1,
                "receiver": self.address,
            },
            "sender": "sender",
        }
        top_txn = {
            "id": "top_id",
            "round-time": 12345,
            "confirmed-round": 123,
        }
        parsed = _parse_transaction(txn, self.address, top_txn)
        assert parsed == {
            "round-time": 12345,
            "round": 123,
            "asset": 1,
            "id": "top_id",
            "amount": 100,
            "sender": "sender",
        }

    # # _parse_transactions
    def test_contract_reporting_parse_transactions_functionality(self):
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2026, 1, 1)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        assert len(parsed) == 8
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2026, 1, 1)
        parsed = _parse_transactions(
            self.transactions, self.address, start_date, end_date
        )
        assert len(parsed) == 8


class TestContractReportingReportsFunctions:
    """Testing class for :py:mod:`contract.reporting` reports functions."""

    def setup_method(self):
        self.address = "2ASZECPEH4ALJWHFN2MKPAS355GC6MDARIC3MFVZCN6NJF76HZPU4R274Q"
        self.transactions = read_json(
            Path(__file__).resolve().parent / "fixture-2ASZE-R274Q.json"
        )
        self.assets_data = {
            0: {"unit": "ALGO", "decimals": 6},
            123755640: {"unit": "UNIT", "decimals": 6},
        }

    # # _format_amount
    def test_contract_reporting_format_amount_for_algo(self):
        allocation = {"asset": 0, "amount": 1234567}
        formatted = _format_amount(allocation, self.assets_data)
        assert formatted == "1.23 ALGO"

    def test_contract_reporting_format_amount_functionality(self):
        allocation = {"asset": 123755640, "amount": 987654321}
        formatted = _format_amount(allocation, self.assets_data)
        assert formatted == "987.65 UNIT"

    # # format_date
    def test_contract_reporting_format_date_functionality(self):
        entry = {"round-time": 1764675278}
        formatted = _format_date(entry)
        assert formatted == "Tue, 2 Dec 2025 11:34:38 UTC"

    # # format_paragraph
    def test_contract_reporting_format_paragraph_for_negative_amount_single(self):
        allocation = {
            "asset": 123755640,
            "amount": -2500000,
            "start": {
                "id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ",
                "round-time": 1764675278,
                "round": 58090657,
            },
        }
        formatted = _format_paragraph(allocation, self.assets_data)
        assert formatted == (
            "On [Tue, 2 Dec 2025 11:34:38 UTC](https://lora.algokit.io/mainnet/"
            "transaction/5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ), an "
            "amount of 2.50 UNIT was allocated from Rewards dApp escrow for claiming "
            "by one contributor on the Rewards website.\n"
        )

    def test_contract_reporting_format_paragraph_for_negative_amount_multiple(self):
        allocation = {
            "asset": 123755640,
            "amount": 645000000000,
            "count": 3,
            "start": {
                "group": "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE=",
                "round-time": 1764684142,
                "round": 58093976,
            },
            "end": {
                "group": "4yMdnSBzKTU/WuHiiOnNxzhscADlBQkdetBqIRqyirw=",
                "round-time": 1764838035,
                "round": 58151503,
            },
            "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
        }
        formatted = _format_paragraph(allocation, self.assets_data)
        assert formatted == (
            "From [Tue, 2 Dec 2025 14:02:22 UTC](https://lora.algokit.io/mainnet/"
            "block/58093976/group/tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE%3D) "
            "to [Thu, 4 Dec 2025 08:47:15 UTC](https://lora.algokit.io/mainnet/"
            "block/58151503/group/4yMdnSBzKTU%2FWuHiiOnNxzhscADlBQkdetBqIRqyirw%3D), "
            "an amount of 645,000.00 UNIT was allocated from Creator address "
            "to Rewards dApp escrow.\n"
        )

    def test_contract_reporting_format_paragraph_for_asset_0_negative_amount(self):
        allocation = {
            "asset": 0,
            "amount": -2500000,
            "start": {
                "id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ",
                "round-time": 1764675278,
                "round": 58090657,
            },
            "receiver": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
        }
        formatted = _format_paragraph(allocation, self.assets_data)
        assert formatted == (
            "On [Tue, 2 Dec 2025 11:34:38 UTC](https://lora.algokit.io/mainnet/"
            "transaction/5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ), an "
            "amount of 2.50 ALGO was allocated from Rewards dApp escrow "
            "to Creator address.\n"
        )

    def test_contract_reporting_format_paragraph_for_asset_0_positive_amount(self):
        allocation = {
            "asset": 0,
            "amount": 500000,
            "start": {
                "id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ",
                "round-time": 1764675278,
                "round": 58090657,
            },
            "sender": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
        }
        formatted = _format_paragraph(allocation, self.assets_data)
        assert formatted == (
            "On [Tue, 2 Dec 2025 11:34:38 UTC](https://lora.algokit.io/mainnet/"
            "transaction/5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ), an "
            "amount of 0.50 ALGO was allocated from Creator address to "
            "Rewards dApp escrow.\n"
        )

    def test_contract_reporting_format_paragraph_for_positive_amount(self):
        allocation = {
            "asset": 123755640,
            "amount": -1000000000,
            "start": {
                "group": "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE=",
                "round-time": 1764684142,
                "round": 58093976,
            },
            "receiver": "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI",
        }
        formatted = _format_paragraph(allocation, self.assets_data)
        assert formatted == (
            "On [Tue, 2 Dec 2025 14:02:22 UTC](https://lora.algokit.io/mainnet/"
            "block/58093976/group/tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE%3D), "
            "an amount of 1,000.00 UNIT was allocated from Rewards dApp escrow "
            "to Creator address.\n"
        )

    # # _format_url
    def test_contract_reporting_format_url_lora_functionality(self):
        entry = {
            "id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ",
            "round": 58090657,
        }
        url = _format_url(entry)
        expected = (
            "https://lora.algokit.io/mainnet/transaction/"
            "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ"
        )
        assert url == expected

    def test_contract_reporting_format_url_for_lora_testnet(self):
        entry = {
            "group": "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE=",
            "round": 58093976,
        }
        url = _format_url(entry, network="testnet")
        expected = (
            "https://lora.algokit.io/testnet/block/58093976/"
            "group/tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE%3D"
        )
        assert url == expected

    def test_contract_reporting_format_url_for_allo_group(self):
        entry = {
            "group": "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE=",
            "round": 58093976,
        }
        with mock.patch("contract.reporting.os.getenv", return_value="allo"):
            url = _format_url(entry)
        assert url == (
            "https://allo.info/tx/group/"
            "tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE%3D"
        )

    def test_contract_reporting_format_url_for_allo_transactions(self):
        entry = {"id": "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ"}
        with mock.patch("contract.reporting.os.getenv", return_value="allo"):
            url = _format_url(entry)
        assert url == (
            "https://allo.info/tx/"
            "5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ"
        )

    # # create_transparency_report
    def test_contract_reporting_create_transparency_report_chronological(self, mocker):
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2026, 1, 1)
        mocker.patch("contract.reporting.app_id_from_contract", return_value=750934138)
        mocker.patch(
            "contract.reporting.fetch_app_allocations",
            return_value=self.transactions,
        )
        mocker.patch(
            "contract.reporting._fetch_asset_data", return_value=self.assets_data
        )
        report = create_transparency_report(start_date, end_date)
        assert report == (
            "On [Tue, 2 Dec 2025 11:34:38 UTC](https://lora.algokit.io/mainnet/"
            "transaction/5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ), "
            "an amount of 0.50 ALGO was allocated from Creator address to "
            "Rewards dApp escrow.\n\n"
            "On [Tue, 2 Dec 2025 14:02:22 UTC](https://lora.algokit.io/mainnet/"
            "block/58093976/group/tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE%3D), "
            "an amount of 195,000.00 UNIT was allocated from Creator address to "
            "Rewards dApp escrow.\n\n"
            "From [Thu, 4 Dec 2025 08:46:32 UTC](https://lora.algokit.io/mainnet/"
            "transaction/XSO5Q5S4ADPSRCJFKEA4TNOJFLZYHE7KJTH3SJ6FW2SWYTHOLXJQ) "
            "to [Thu, 4 Dec 2025 08:46:59 UTC](https://lora.algokit.io/mainnet/"
            "transaction/XTIG4HP3NN7YOWULX53RB6JGOLP3YO5CL4GTQUPS3ABCOEF4UXEQ), "
            "an amount of 195,000.00 UNIT was allocated from Rewards dApp "
            "escrow for claiming by 4 contributors on the Rewards website.\n\n"
            "From [Thu, 4 Dec 2025 08:47:10 UTC](https://lora.algokit.io/mainnet/block"
            "/58151501/group/%2BLLeR%2BKDBcDoJPL5zjPoeXu8knIi7cCAKH%2FH1p%2FRCyA%3D) "
            "to [Thu, 4 Dec 2025 08:47:15 UTC](https://lora.algokit.io/mainnet/block/"
            "58151503/group/4yMdnSBzKTU%2FWuHiiOnNxzhscADlBQkdetBqIRqyirw%3D), "
            "an amount of 450,000.00 UNIT was allocated from "
            "Creator address to Rewards dApp escrow.\n"
        )

    def test_contract_reporting_create_transparency_report_by_type(self, mocker):
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2026, 1, 1)
        mocker.patch("contract.reporting.app_id_from_contract", return_value=750934138)
        mocker.patch(
            "contract.reporting.fetch_app_allocations",
            return_value=self.transactions,
        )
        mocker.patch(
            "contract.reporting._fetch_asset_data", return_value=self.assets_data
        )
        report = create_transparency_report(start_date, end_date, grouping="by_type")
        assert report == (
            "On [Tue, 2 Dec 2025 11:34:38 UTC](https://lora.algokit.io/mainnet/"
            "transaction/5AAL3HQOADA6GVMSUQ3WPXRO22FOGJ4RBTMA2PXONG5F2EBVADSQ), "
            "an amount of 0.50 ALGO was allocated from Creator address "
            "to Rewards dApp escrow.\n\n"
            "From [Tue, 2 Dec 2025 14:02:22 UTC](https://lora.algokit.io/mainnet/"
            "block/58093976/group/tCpVmg6Wxz3zfnFRfucigfHDyaFmqsKgctvSiWO0StE%3D) "
            "to [Thu, 4 Dec 2025 08:47:15 UTC](https://lora.algokit.io/mainnet/"
            "block/58151503/group/4yMdnSBzKTU%2FWuHiiOnNxzhscADlBQkdetBqIRqyirw%3D), "
            "an amount of 645,000.00 UNIT was allocated from Creator address "
            "to Rewards dApp escrow.\n\n"
            "From [Thu, 4 Dec 2025 08:46:32 UTC](https://lora.algokit.io/mainnet/"
            "transaction/XSO5Q5S4ADPSRCJFKEA4TNOJFLZYHE7KJTH3SJ6FW2SWYTHOLXJQ) "
            "to [Thu, 4 Dec 2025 08:46:59 UTC](https://lora.algokit.io/mainnet/"
            "transaction/XTIG4HP3NN7YOWULX53RB6JGOLP3YO5CL4GTQUPS3ABCOEF4UXEQ), "
            "an amount of 195,000.00 UNIT was allocated from "
            "Rewards dApp escrow for claiming by 4 contributors on "
            "the Rewards website.\n"
        )
