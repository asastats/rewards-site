import {
  AtomicTransactionComposer,
  ABIContract,
  makeAssetTransferTxnWithSuggestedParamsFromObject,
  Algodv2,
  getApplicationAddress,
  decodeAddress,
} from "algosdk";
import { WalletManager, NetworkId } from "@txnlab/use-wallet";
import rewardsABI from "../../contract/artifacts/Rewards.arc56.json";
import { Buffer } from "buffer";

/**
 * Client for interacting with the Rewards smart contract and backend API.
 *
 * This class provides methods to interact with the Algorand blockchain
 * for reward-related operations including adding allocations, reclaiming
 * allocations, and claiming rewards. It handles transaction composition,
 * signing, and submission.
 *
 * @example
 * ```typescript
 * const rewardsClient = new RewardsClient(wallet, walletManager)
 * await rewardsClient.addAllocations(addresses, amounts)
 * ```
 */
export class RewardsClient {
  private manager: WalletManager;
  private algodClient: Algodv2;
  private contract: ABIContract;
  private rewardsAppIds: { [key in NetworkId]?: number };

  /**
   * Creates an instance of RewardsClient.
   *
   * @param wallet - The wallet instance for transaction signing
   * @param manager - The wallet manager for network and account management
   */
  constructor(manager: WalletManager) {
    this.manager = manager;
    this.algodClient = this.manager.algodClient;
    this.contract = new ABIContract(rewardsABI as any);

    // Hardcoded App IDs for different networks
    this.rewardsAppIds = {
      [NetworkId.MAINNET]: 0, // TODO: Replace with your Mainnet App ID
      [NetworkId.TESTNET]: 750934138, // TODO: Replace with your Testnet App ID
    };
  }

  /**
   * Retrieves the CSRF token from cookies or form input for API requests.
   *
   * @returns The CSRF token as a string
   * @private
   */
  private getCsrfToken = () => {
    const cookieValue =
      document.cookie.match(/(^|;)\s*csrftoken\s*=\s*([^;]+)/)?.pop() || "";
    return (
      cookieValue ||
      (
        document.querySelector(
          'input[name="csrfmiddlewaretoken"]'
        ) as HTMLInputElement
      )?.value ||
      ""
    );
  };

  /**
   * Gets the headers for API requests including CSRF token.
   *
   * @returns Headers object for fetch requests
   * @private
   */
  private getHeaders = () => ({
    "Content-Type": "application/json",
    "X-CSRFToken": this.getCsrfToken(),
  });

  private boxNameFromAddress(address: string): Uint8Array {
    const addressBytes = decodeAddress(address).publicKey;
    const boxName = new Uint8Array(
      Buffer.concat([Buffer.from("allocations"), addressBytes])
    );
    return boxName;
  }

  /**
   * Adds allocations to multiple addresses with specified amounts.
   *
   * Creates and submits an atomic transaction to the rewards contract
   * to allocate rewards to the provided addresses.
   *
   * @param addresses - Array of recipient addresses
   * @param amounts - Array of amounts to allocate (must match addresses length)
   * @returns The transaction result
   * @throws {Error} When no active account, arrays are empty, or arrays length mismatch
   */
  public async addAllocations(
    addresses: string[],
    amounts: number[],
    decimals: number
  ) {
    if (!this.manager.activeAccount?.address) {
      throw new Error("No active account selected.");
    }
    if (!addresses.length || addresses.length !== amounts.length) {
      throw new Error(
        "Addresses and amounts arrays must have the same non-zero length."
      );
    }

    try {
      const suggestedParams = await this.algodClient
        .getTransactionParams()
        .do();
      const atc = new AtomicTransactionComposer();
      const currentNetwork = this.manager.activeNetwork as NetworkId;
      const appId = this.rewardsAppIds[currentNetwork];

      if (!appId) {
        throw new Error(`App ID not configured for network: ${currentNetwork}`);
      }

      const appInfo = await this.algodClient.getApplicationByID(appId).do();
      const globalState = appInfo.params.globalState;
      if (!globalState || globalState.length === 0) {
        throw new Error("Contract global state is empty or not found");
      }
      const tokenIdValue = globalState.find(
        (state: any) =>
          Buffer.from(state["key"], "base64").toString("utf8") === "token_id"
      );
      if (!tokenIdValue) {
        throw new Error("token_id not found in contract's global state");
      }
      const tokenId = tokenIdValue["value"]["uint"];

      const microasaAmounts = amounts.map((amount) =>
        Math.floor(amount * 10 ** decimals)
      );
      const totalAmount = microasaAmounts.reduce(
        (sum, current) => sum + current,
        0
      );

      const fundingTxn = makeAssetTransferTxnWithSuggestedParamsFromObject({
        sender: this.manager.activeAccount.address,
        receiver: getApplicationAddress(appId),
        amount: totalAmount,
        assetIndex: tokenId,
        suggestedParams: suggestedParams,
      });

      atc.addTransaction({
        txn: fundingTxn,
        signer: this.manager.transactionSigner,
      });

      const boxes = addresses.map((addr) => ({
        appIndex: 0,
        name: this.boxNameFromAddress(addr),
      }));

      atc.addMethodCall({
        appID: appId,
        method: this.contract.getMethodByName("add_allocations"),
        methodArgs: [addresses, microasaAmounts],
        sender: this.manager.activeAccount.address,
        signer: this.manager.transactionSigner,
        suggestedParams,
        boxes: boxes,
        appForeignAssets: [tokenId],
      });

      const result = await atc.execute(this.algodClient, 4);
      console.info(
        `[RewardsClient] ✅ Successfully sent add_allocations transaction!`,
        {
          confirmedRound: result.confirmedRound,
          txIDs: result.txIDs,
        }
      );
      return result;
    } catch (error) {
      console.error("[RewardsClient] Error adding allocations:", error);
      throw error;
    }
  }

  /**
   * Reclaims an allocation from a specific user address.
   *
   * Submits a transaction to reclaim previously allocated rewards from
   * the specified address back to the contract owner.
   *
   * @param userAddress - The address to reclaim allocation from
   * @returns The transaction result
   * @throws {Error} When no active account or app ID not configured
   */
  public async reclaimAllocation(userAddress: string) {
    if (!this.manager.activeAccount?.address) {
      throw new Error("No active account selected.");
    }

    try {
      const suggestedParams = await this.algodClient
        .getTransactionParams()
        .do();

      // Set higher fee like in Python version - use BigInt for fee
      suggestedParams.flatFee = true;
      suggestedParams.fee = BigInt(2000); // Set fee to 2000 microAlgos like in Python

      const atc = new AtomicTransactionComposer();
      const currentNetwork = this.manager.activeNetwork as NetworkId;
      const appId = this.rewardsAppIds[currentNetwork];

      if (!appId) {
        throw new Error(`App ID not configured for network: ${currentNetwork}`);
      }

      // Fetch the token_id from the contract's global state (needed for foreign_assets)
      const appInfo = await this.algodClient.getApplicationByID(appId).do();
      const globalState = appInfo.params.globalState;
      if (!globalState || globalState.length === 0) {
        throw new Error("Contract global state is empty or not found");
      }
      const tokenIdValue = globalState.find(
        (state: any) =>
          Buffer.from(state["key"], "base64").toString("utf8") === "token_id"
      );
      if (!tokenIdValue) {
        throw new Error("token_id not found in contract's global state");
      }
      const tokenId = tokenIdValue["value"]["uint"];

      atc.addMethodCall({
        appID: appId,
        method: this.contract.getMethodByName("reclaim_allocation"),
        methodArgs: [userAddress],
        sender: this.manager.activeAccount.address,
        signer: this.manager.transactionSigner,
        suggestedParams,
        boxes: [
          {
            appIndex: appId,
            name: this.boxNameFromAddress(userAddress),
          },
        ],
        appForeignAssets: [tokenId],
      });

      const result = await atc.execute(this.algodClient, 4);
      console.info(
        `[RewardsClient] ✅ Successfully sent reclaim_allocation transaction!`,
        {
          confirmedRound: result.confirmedRound,
          txIDs: result.txIDs,
        }
      );

      // Return the first transaction ID to match Python counterpart
      return result.txIDs[0];
    } catch (error) {
      console.error("[RewardsClient] Error reclaiming allocation:", error);
      throw error;
    }
  }

  /**
   * Claims available rewards for the active account.
   *
   * Performs an atomic transaction group that includes:
   * 1. Asset opt-in transaction for the reward token
   * 2. Claim method call to the rewards contract
   *
   * @returns The transaction ID from the claim operation
   * @throws {Error} When no active account, app ID not configured, or token_id not found
   */
  public async claimRewards(): Promise<string> {
    if (!this.manager.activeAccount?.address) {
      throw new Error("No active account selected.");
    }

    try {
      const suggestedParams = await this.algodClient
        .getTransactionParams()
        .do();

      // Set higher fees for both transactions to cover box operations
      suggestedParams.flatFee = true;
      suggestedParams.fee = BigInt(2000); // Set fee to 2000 microAlgos like in reclaimAllocation

      const atc = new AtomicTransactionComposer();
      const sender = this.manager.activeAccount.address;
      const signer = this.manager.transactionSigner;
      const currentNetwork = this.manager.activeNetwork as NetworkId;
      const appId = this.rewardsAppIds[currentNetwork];

      if (!appId) {
        throw new Error(`App ID not configured for network: ${currentNetwork}`);
      }

      // Fetch the token_id from the contract's global state
      const appInfo = await this.algodClient.getApplicationByID(appId).do();
      const globalState = appInfo.params.globalState;
      if (!globalState || globalState.length === 0) {
        throw new Error("Contract global state is empty or not found");
      }
      const tokenIdValue = globalState.find(
        (state: any) =>
          Buffer.from(state["key"], "base64").toString("utf8") === "token_id"
      );
      if (!tokenIdValue) {
        throw new Error("token_id not found in contract's global state");
      }
      const tokenId = tokenIdValue["value"]["uint"];

      // 1. Create the asset opt-in transaction with increased fee
      const optInTxn = makeAssetTransferTxnWithSuggestedParamsFromObject({
        sender: sender,
        receiver: sender,
        amount: 0,
        assetIndex: tokenId,
        suggestedParams: { ...suggestedParams }, // Use the increased fee params
      });

      // Wrap it in a TransactionWithSigner
      const tws = { txn: optInTxn, signer: signer };

      // 2. Add the opt-in transaction to our atomic group
      atc.addTransaction(tws);

      // 3. Add the method call to 'claim' to our atomic group WITH THE BOX REFERENCE
      atc.addMethodCall({
        appID: appId,
        method: this.contract.getMethodByName("claim"),
        methodArgs: [],
        sender: sender,
        signer: signer,
        suggestedParams: { ...suggestedParams }, // Use the increased fee params
        boxes: [
          {
            appIndex: appId,
            name: this.boxNameFromAddress(sender),
          },
        ],
        appForeignAssets: [tokenId],
      });

      const result = await atc.execute(this.algodClient, 4);
      console.info(`[RewardsClient] ✅ Successfully sent claim transaction!`, {
        confirmedRound: result.confirmedRound,
        txIDs: result.txIDs,
      });

      // Return the first transaction ID to match reclaim pattern
      return result.txIDs[0];
    } catch (error) {
      console.error("[RewardsClient] Error claiming allocation:", error);
      throw error;
    }
  }

  /**
   * Notifies the backend about successful add allocations transactions
   * @param addresses - Array of public addresses
   * @param txIDs - The transaction IDs from the add alolocations operation
   */
  public async notifyAllocationsSuccessful(
    addresses: string[],
    txIDs: string[]
  ): Promise<{ success: boolean }> {
    try {
      const response = await fetch("/api/wallet/allocations-successful/", {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ addresses, txIDs }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(
        "[RewardsClient] Error notifying allocations successful:",
        error
      );
      throw error;
    }
  }

  /**
   * Notifies the backend about successful claim transaction
   * @param address - The address that claimed rewards
   * @param txID - The transaction ID from the claim operation
   */
  public async notifyClaimSuccessful(
    address: string,
    txID: string
  ): Promise<{ success: boolean }> {
    try {
      const response = await fetch("/api/wallet/claim-successful/", {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ address, txID }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("[RewardsClient] Error sending user claimed:", error);
      throw error;
    }
  }

  /**
   * Notifies the backend about successful reclaim allocation transactions
   * @param address - The address that was reclaimed from
   * @param txID - The transaction ID from the reclaim operation
   */
  async notifyReclaimSuccessful(
    address: string,
    txID: string
  ): Promise<void> {
    const csrfToken = this.getCsrfToken();
    if (!csrfToken) {
      throw new Error("CSRF token not found");
    }

    const response = await fetch("/api/wallet/reclaim-successful/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        address: address,
        txID: txID,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to notify reclaim success: ${response.status} ${errorText}`
      );
    }
  }

  /**
   * Fetches add allocations data for an address from the backend API.
   *
   * @param address - The address to fetch allocation data for
   * @returns Object containing addresses and amounts for allocations
   * @throws {Error} When the API request fails
   */
  public async fetchAddAllocationsData(
    address: string
  ): Promise<{ addresses: string[]; amounts: number[] }> {
    try {
      const response = await fetch("/api/wallet/add-allocations/", {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ address }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(
        "[RewardsClient] Error fetching add allocations data:",
        error
      );
      throw error;
    }
  }

  /**
   * Fetches reclaimable allocations data for an address from the backend API.
   *
   * @param address - The address to fetch reclaimable data for
   * @returns Object containing addresses with reclaimable allocations
   * @throws {Error} When the API request fails
   */
  public async fetchReclaimAllocationsData(
    address: string
  ): Promise<{ addresses: string[] }> {
    try {
      const response = await fetch("/api/wallet/reclaim-allocations/", {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ address }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(
        "[RewardsClient] Error fetching reclaim allocations data:",
        error
      );
      throw error;
    }
  }
}
