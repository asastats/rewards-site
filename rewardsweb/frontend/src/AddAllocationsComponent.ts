import { RewardsClient } from './RewardsClient'
import { WalletManager } from '@txnlab/use-wallet'

/**
 * Component for managing and adding reward allocations to multiple addresses.
 * 
 * This component handles the UI and logic for adding allocations to various addresses
 * with corresponding amounts. It integrates with the RewardsClient to fetch data
 * and submit transactions to the blockchain.
 * 
 * @example
 * ```typescript
 * const addAllocationsComponent = new AddAllocationsComponent(rewardsClient, walletManager)
 * addAllocationsComponent.bind(document.getElementById('add-allocations-container'))
 * ```
 */
export class AddAllocationsComponent {
  private element: HTMLElement | null = null
  private rewardsClient: RewardsClient
  private walletManager: WalletManager
  private addresses: string[] = []
  private amounts: number[] = []
  private decimals: number = 6

  /**
   * Creates an instance of AddAllocationsComponent.
   *
   * @param rewardsClient - The client for interacting with rewards contract and API
   * @param walletManager - The wallet manager for account and network state
   */
  constructor(rewardsClient: RewardsClient, walletManager: WalletManager) {
    this.rewardsClient = rewardsClient
    this.walletManager = walletManager
    this.walletManager.subscribe(() => this.fetchAllocationsData())
  }

  /**
   * Binds the component to a DOM element and initializes event listeners.
   *
   * @param element - The HTML element to bind the component to
   */
  bind(element: HTMLElement) {
    this.element = element
    this.addEventListeners()
    // Ensure the DOM is fully loaded before fetching data to ensure CSRF token is available
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.fetchAllocationsData());
    } else {
      this.fetchAllocationsData();
    }
  }

  /**
   * Fetches allocation data from the backend API for the active account.
   *
   * Updates the internal state with addresses and amounts, then re-renders the UI.
   * Handles errors by displaying alerts to the user.
   *
   * @private
   */
  private async fetchAllocationsData() {
    const activeAddress = this.walletManager.activeAccount?.address
    if (!activeAddress) {
      this.addresses = []
      this.amounts = []
      return
    }

    try {
      const data = await this.rewardsClient.fetchAddAllocationsData(activeAddress)
      if (data) {
        this.addresses = data.addresses
        this.amounts = data.amounts
      } else {
        this.addresses = []
        this.amounts = []
      }
    } catch (error) {
      console.error('[AddAllocationsComponent] Error fetching add allocations data:', error)
    }
  }

  /**
   * Handles the add allocations transaction submission.
   *
   * Sends the current addresses and amounts to the blockchain via RewardsClient.
   * Displays success/error messages and refreshes data on success.
   *
   * @private
   */
  private async handleAddAllocations() {
    try {
      console.info('[AddAllocationsComponent] Initiating add allocations...')
      const addressesChunk = this.addresses.slice(0, 4)
      const amountsChunk = this.amounts.slice(0, 4)
      const result = await this.rewardsClient.addAllocations(addressesChunk, amountsChunk, this.decimals)
      await this.rewardsClient.notifyAllocationsSuccessful(addressesChunk, result.txIDs)
      location.reload()
    } catch (error) {
      console.error('[AddAllocationsComponent] Error during add allocations:', error)
      alert(`Add allocations failed: ${error instanceof Error ? error.message : String(error)}`)
    }
  }


  /**
   * Adds event listeners for user interactions.
   *
   * Listens for click events on the add allocations button and updates
   * internal state from textarea inputs before submission.
   *
   * @private
   */
  addEventListeners() {
    if (!this.element) return

    this.element.addEventListener('click', (e: Event) => {
      const target = e.target as HTMLElement
      if (target.id === 'add-allocations-button') {
        this.handleAddAllocations()
      }
    })
  }

  /**
   * Cleans up the component.
   *
   * Currently no specific cleanup needed, but provided for interface consistency.
   */
  destroy() {
    // No specific cleanup needed for now
  }
}
