"""Module with Rewards smart contract's transparency reports creation functions."""

import json
import logging
import os
import urllib.parse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from algosdk.logic import get_application_address
from algosdk.v2client.indexer import IndexerClient

from contract.helpers import pause, read_json
from contract.network import app_id_from_contract

INDEXER_ADDRESS = "https://testnet-idx.4160.nodely.dev"
INDEXER_TOKEN = ""
INDEXER_FETCH_LIMIT = 1000
INDEXER_PAGE_DELAY = 1
EXPLORER_BASE_URLS = {
    "lora": "https://lora.algokit.io/",
    "allo": "https://allo.info/",
}
PROJECT_ADDRESSES = {
    "V2HN6R3A5YTFJLYFTRX7AIPFE7XRG2UVDSK24IZU6YVG2J7IHFRL7CFRTI": "Creator"
}


logger = logging.getLogger(__name__)


# # INDEXER
def _address_transaction(address, min_round, indexer_client, **kwargs):
    """Yield transaction connected with provided address.

    :param address: public Algorand to fetch transactions for
    :type address: str
    :param min_round: starting block to yield transactions from
    :type min_round: int
    :param indexer_client: Algorand Indexer client instance
    :type indexer_client: :class:`IndexerClient`
    :var delay: delay in seconds between calls
    :type delay: int
    :var limit: maxiumum nuber of records to fetch in a single call
    :type limit: int
    :var params: collection of arguments to search transactions endpoint
    :type params: dict
    :var results: fetched page of transactions
    :type results: dict
    :var transaction: transaction instance
    :type transaction: dict
    :yield: dict
    """
    delay = kwargs.pop("delay", INDEXER_PAGE_DELAY)
    limit = kwargs.pop("limit", INDEXER_FETCH_LIMIT)
    pause(delay)

    params = {"limit": limit, "min_round": min_round, **kwargs}

    results = _search_transactions_by_address(
        address, params, indexer_client, delay=delay
    )
    while results.get("transactions"):
        for transaction in results.get("transactions"):
            yield transaction

        pause(delay)
        results = _search_transactions_by_address(
            address,
            params,
            indexer_client,
            next_page=results.get("next-token"),
            delay=delay,
        )


def _fetch_app_allocations():
    """Fetch and return Rewards dApp's escrow transactions.

    :var app_id: Rewards dApp unique identifier
    :type app_id: int
    :var escrow:  Rewards dApp escrow address
    :type escrow: str
    :var filename: full path on disk to JSON file with escrow's transactions
    :type filename: :class:`pathlib.PosixPath`
    :var transactions: collection of all escrow transactions
    :type transactions: list
    :var indexer_client: Algorand Indexer client instance
    :type indexer_client: :class:`IndexerClient`
    :var min_round: starting block to yield transactions from
    :type min_round: int
    :var new_transactions: collection of new escrow transactions
    :type new_transactions: list
    :return: collection of all escrow transactions
    :rtype: list
    """
    app_id = app_id_from_contract()
    escrow = get_application_address(app_id)
    filename = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / f"{f"{escrow[:5]}-{escrow[-5:]}"}.json"
    )
    transactions = read_json(filename) or []
    indexer_client = _indexer_instance()
    min_round = (
        transactions[-1].get("confirmed-round") + 1
        if transactions
        else indexer_client.applications(app_id)
        .get("application", {})
        .get("created-at-round")
    )
    new_transactions = list(_address_transaction(escrow, min_round, indexer_client))
    if new_transactions:
        transactions = sorted(
            transactions + new_transactions, key=lambda x: x.get("confirmed-round", 0)
        )
        with open(filename, "w") as json_file:
            json.dump(transactions, json_file)

    return transactions


def _fetch_asset_data(asset_ids):
    """TODO: docstring and tests"""
    data = {}
    indexer_client = _indexer_instance()
    for asset_id in asset_ids:
        if asset_id == 0:
            data[asset_id] = {"unit": "ALGO", "decimals": 6}

        else:
            asset_info = (
                indexer_client.asset_info(asset_id).get("asset", {}).get("params")
            )
            data[asset_id] = {
                "unit": asset_info.get("unit-name"),
                "decimals": asset_info.get("decimals"),
            }

    return data


def _indexer_instance():
    """Return Algorand Indexer instance.

    :return: :class:`IndexerClient`
    """
    return IndexerClient(
        INDEXER_TOKEN, INDEXER_ADDRESS, headers={"User-Agent": "algosdk"}
    )


def _search_transactions_by_address(
    address,
    params,
    indexer_client,
    next_page=None,
    delay=1,
    error_delay=5,
    retries=20,
):
    """Fetch and return transactions from indexer instance based on provided params.

    :param address: public Algorand to fetch transactions for
    :type address: str
    :param params: collection of parameters to indexer search method
    :type params: dict
    :param indexer_client: Algorand Indexer client instance
    :type indexer_client: :class:`IndexerClient`
    :param next_page: custom code identifying very next page of search results
    :type next_page: str
    :param delay: delay in seconds before Indexer call
    :type delay: float
    :param error_delay: delay in seconds after error
    :type error_delay: int
    :param retries: maximum number of retries before system exit
    :type retries: int
    :param _params: updated parameters to indexer search method
    :type _params: dict
    :var counter: current number of retries to fetch the block
    :type counter: int
    :return: dict
    """
    _params = deepcopy(params)
    if next_page:
        _params.update({"next_page": next_page})

    counter = 0
    while True:
        try:
            pause(delay)
            return indexer_client.search_transactions_by_address(address, **_params)

        except Exception as e:
            if counter >= retries:
                logger.error("Maximum number of retries reached. Exiting...")
                raise ValueError("Maximum number of retries reached")

            logger.error(
                "Exception %s raised searching transactions: %s; Paused..."
                % (
                    e,
                    _params,
                )
            )
            pause(error_delay)
            counter += 1


# # PARSING
def _create_chronological_group(txn):
    """Create a new chronological transaction group.

    :param txn: parsed transaction from the list
    :type txn: dict
    :var group: currently processed group
    :type group: dict
    :return: new chronological transaction group
    :rtype: dict
    """
    group = {
        "asset": txn["asset"],
        "amount": txn["amount"],
        "start": _create_transaction_entry(txn),
        "count": 1,
    }
    if txn.get("receiver") in PROJECT_ADDRESSES:
        group["receiver"] = txn.get("receiver")

    if txn.get("sender") in PROJECT_ADDRESSES:
        group["sender"] = txn.get("sender")

    return group


def _create_transaction_entry(txn):
    """Create a transaction entry dictionary with id/group, round-time and round.

    :param txn: parsed transaction
    :type txn: dict
    :var entry: transaction entry
    :type entry: dict
    :return: transaction entry dictionary
    :rtype: dict
    """
    entry = {
        "round-time": txn.get("round-time"),
        "round": txn.get("round"),
    }
    if txn.get("group"):
        entry["group"] = txn.get("group")
    else:
        entry["id"] = txn.get("id")
    return entry


def _group_transactions_by_type(parsed_transactions):
    """Group parsed transactions by asset and sign.

    :param parsed_transactions: list of parsed transactions
    :type parsed_transactions: list
    :var result: list of grouped transactions
    :type result: list
    :var asset_groups: dictionary of asset groups
    :type asset_groups: dict
    :var txn: parsed transaction from the list
    :type txn: dict
    :return: list of grouped transactions
    :rtype: list
    """
    if not parsed_transactions:
        return []

    result = []
    asset_groups = {}

    for txn in parsed_transactions:
        asset_id = txn["asset"]
        sign = txn["amount"] > 0
        group_key = (asset_id, sign)

        if group_key not in asset_groups:
            asset_groups[group_key] = {
                "asset": asset_id,
                "amount": 0,
                "count": 0,
                "start": _create_transaction_entry(txn),
            }
            result.append(asset_groups[group_key])

        group = asset_groups[group_key]
        group["amount"] += txn["amount"]
        group["count"] += 1
        if group["count"] > 1:
            group["end"] = _create_transaction_entry(txn)

        if txn.get("receiver") in PROJECT_ADDRESSES:
            group["receiver"] = txn.get("receiver")

        if txn.get("sender") in PROJECT_ADDRESSES:
            group["sender"] = txn.get("sender")

    return result


def _group_transactions_chronological(parsed_transactions):
    """Group parsed transactions by asset and sign.

    :param parsed_transactions: list of parsed transactions
    :type parsed_transactions: list
    :var result: list of grouped transactions
    :type result: list
    :var current_group: currently processed group
    :type current_group: dict
    :var txn: parsed transaction from the list
    :type txn: dict
    :return: list of grouped transactions
    :rtype: list
    """
    if not parsed_transactions:
        return []

    result = []
    current_group = None

    for txn in parsed_transactions:
        if not current_group:
            current_group = _create_chronological_group(txn)

        elif (
            txn["asset"] == current_group["asset"]
            and (txn["amount"] > 0) == (current_group["amount"] > 0)
            and (
                (
                    txn.get("sender") in PROJECT_ADDRESSES
                    and txn.get("sender") == current_group.get("sender")
                )
                or (
                    txn.get("receiver") in PROJECT_ADDRESSES
                    and txn.get("receiver") == current_group.get("receiver")
                )
                or (
                    txn.get("sender") not in PROJECT_ADDRESSES
                    and txn.get("receiver") not in PROJECT_ADDRESSES
                    and not current_group.get("sender")
                    and not current_group.get("receiver")
                )
            )
        ):
            current_group["amount"] += txn["amount"]
            current_group["end"] = _create_transaction_entry(txn)
            current_group["count"] += 1

        else:
            if "count" in current_group and (
                current_group.get("sender") or current_group.get("receiver")
            ):
                del current_group["count"]

            result.append(current_group)
            current_group = _create_chronological_group(txn)

    result.append(current_group)

    return result


def _parse_transaction(txn, address, top_txn):
    """Parse a transaction and return a standardized dictionary.

    :param txn: transaction to parse
    :type txn: dict
    :param address: target address
    :type address: str
    :param top_txn: top-level transaction containing the txn
    :type top_txn: dict
    :var tx_type: type of the transaction
    :type tx_type: str
    :var parsed: dictionary with parsed transaction data
    :type parsed: dict
    :var axfer: asset transfer transaction details
    :type axfer: dict
    :var pay: payment transaction details
    :type pay: dict
    :return: parsed transaction or None
    :rtype: dict or None
    """
    tx_type = txn.get("tx-type")
    parsed = {
        "round-time": top_txn.get("round-time"),
        "round": top_txn.get("confirmed-round"),
    }
    if top_txn.get("group"):
        parsed["group"] = top_txn.get("group")

    else:
        parsed["id"] = top_txn.get("id")

    if tx_type == "axfer":
        axfer = txn.get("asset-transfer-transaction")
        if not axfer.get("amount"):
            return None

        parsed["asset"] = axfer.get("asset-id")
        parsed["amount"] = axfer.get("amount")
        if axfer.get("receiver") == address:
            parsed["sender"] = txn.get("sender")

        elif txn.get("sender") == address:
            parsed["amount"] *= -1
            parsed["receiver"] = axfer.get("receiver")

        else:
            return None

    elif tx_type == "pay":
        pay = txn.get("payment-transaction")
        parsed["asset"] = 0
        parsed["amount"] = pay.get("amount")
        if pay.get("receiver") == address:
            parsed["sender"] = txn.get("sender")

        elif txn.get("sender") == address:
            parsed["amount"] *= -1
            parsed["receiver"] = pay.get("receiver")

        else:
            return None

    else:
        return None

    return parsed


def _parse_transactions(transactions, address, start_date, end_date):
    """Parse all transactions and filter them by date.

    :param transactions: list of transactions to parse
    :type transactions: list
    :param address: target address
    :type address: str
    :param start_date: start date of the period
    :type start_date: :class:`datetime.datetime`
    :param end_date: end date of the period
    :type end_date: :class:`datetime.datetime`
    :var parsed_transactions: list of parsed transactions
    :type parsed_transactions: list
    :var txn: transaction from the list
    :type txn: dict
    :var round_time: timestamp of the transaction
    :type round_time: int
    :var parsed: parsed transaction dictionary
    :type parsed: dict
    :var inner_txn: inner transaction
    :type inner_txn: dict
    :return: list of parsed transactions
    :rtype: list
    """
    parsed_transactions = []
    for txn in transactions:
        round_time = txn.get("round-time")
        if not (start_date.timestamp() <= round_time <= end_date.timestamp()):
            continue

        if parsed := _parse_transaction(txn, address, txn):
            parsed_transactions.append(parsed)

        for inner_txn in txn.get("inner-txns", []):
            if parsed := _parse_transaction(inner_txn, address, txn):
                parsed_transactions.append(parsed)

    return parsed_transactions


# # REPORTS
def _format_amount(allocation, assets_data):
    """TODO: docstring and tests"""
    amount = abs(allocation.get("amount")) / 10 ** assets_data.get(
        allocation.get("asset")
    ).get("decimals")
    unit = assets_data.get(allocation.get("asset")).get("unit")
    return f"{amount:,.2f} {unit}"


def _format_date(entry):
    """TODO: docstring and tests"""
    utc_datetime = datetime.fromtimestamp(entry.get("round-time"), tz=timezone.utc)
    return utc_datetime.strftime("%a, %-d %b %Y %H:%M:%S UTC")


def _format_paragraph(allocation, assets_data):
    """TODO: docstring and tests"""

    amount = _format_amount(allocation, assets_data)
    amount_text = f"an amount of {amount}"
    if allocation.get("amount") > 0:
        source_address = PROJECT_ADDRESSES.get(allocation.get("sender"))
        source = f"from {source_address} address"
        destination = "to Rewards dApp escrow"

    else:
        source = "from Rewards dApp escrow"
        if allocation.get("receiver"):
            dest_address = PROJECT_ADDRESSES.get(allocation.get("sender"))
            destination = f"to {dest_address} address"

        else:
            count = allocation.get("count")
            destination = (
                f"to {count} contributors to be claimed on the Rewards website."
            )

    start_text = _format_date(allocation.get("start"))
    start_url = _format_url(allocation.get("start"))
    if not allocation.get("end"):
        link = f"On [{start_text}]({start_url}), {amount_text} was allocated"

    else:
        end_text = _format_date(allocation.get("end"))
        end_url = _format_url(allocation.get("end"))
        link = (
            f"From [{start_text}]({start_url}) to [{end_text}]({end_url}), "
            f"{amount_text} had been allocated"
        )

    return f"{link} {source} {destination}.\n"


def _format_url(entry, network="mainnet"):
    """TODO: docstring and tests"""
    explorer = os.getenv("BLOCKCHAIN_EXPLORER", "lora")
    url = EXPLORER_BASE_URLS.get(explorer)
    if entry.get("group"):
        group = urllib.parse.quote(entry.get("group"), safe="")
        if explorer == "lora":
            url += network + "/block/" + str(entry.get("round")) + "/group/" + group
        else:
            url += "tx/group/" + group

    else:
        if explorer == "lora":
            url += network + "/transaction/" + entry.get("id")
        else:
            url += "tx/" + entry.get("id")

    return url
