"""Module with Rewards smart contract's transparency reports creation functions."""

import json
import logging
from copy import deepcopy
from pathlib import Path

from algosdk.logic import get_application_address
from algosdk.v2client.indexer import IndexerClient

from contract.helpers import pause, read_json
from contract.network import app_id_from_contract

INDEXER_ADDRESS = "https://testnet-idx.4160.nodely.dev"
INDEXER_TOKEN = ""
INDEXER_FETCH_LIMIT = 1000
INDEXER_PAGE_DELAY = 1


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
