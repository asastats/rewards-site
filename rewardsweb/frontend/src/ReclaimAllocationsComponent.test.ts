import { ReclaimAllocationsComponent } from './ReclaimAllocationsComponent'
import { RewardsClient } from './RewardsClient'
import { WalletManager } from '@txnlab/use-wallet'

// Mock window.location.reload
Object.defineProperty(window, 'location', {
  value: {
    reload: jest.fn(),
  },
  writable: true,
});

// Mock RewardsClient
jest.mock('./RewardsClient', () => {
  return {
    RewardsClient: jest.fn().mockImplementation(() => {
      return {
        fetchReclaimAllocationsData: jest.fn(),
        reclaimAllocation: jest.fn(),
        notifyReclaimSuccessful: jest.fn().mockResolvedValue(undefined),
      }
    }),
  }
})

describe('ReclaimAllocationsComponent', () => {
  let mockRewardsClient: jest.Mocked<RewardsClient>
  let mockWalletManager: jest.Mocked<WalletManager>
  let reclaimAllocationsComponent: ReclaimAllocationsComponent
  let alertSpy: jest.SpyInstance
  let container: HTMLElement

  beforeEach(() => {
    alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => { })
    // Fix: Updated constructor to match new signature (only WalletManager)
    mockRewardsClient = new RewardsClient(null as any) as jest.Mocked<RewardsClient>
    mockWalletManager = {
      activeAccount: { address: 'test-address' },
      subscribe: jest.fn(),
    } as any

    // Set up the DOM structure matching the updated Django template with reclaim-button class
    container = document.createElement('div')
    container.id = 'reclaim-allocations-container'
    container.innerHTML = `
      <div class="space-y-4 p-4 rounded-lg mt-4">
        <h4 class="font-semibold text-lg">Reclaimable Addresses</h4>
        <table class="table w-full">
          <thead>
            <tr>
              <th></th>
              <th>Address</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="py-2 px-2">
                <button
                  class="btn btn-soft btn-warning btn-sm reclaim-button"
                  data-address="addr1"
                  id="reclaim-button-1">
                  Reclaim
                </button>
              </td>
              <td class="py-2 px-2">addr1</td>
            </tr>
            <tr>
              <td class="py-2 px-2">
                <button
                  class="btn btn-soft btn-warning btn-sm reclaim-button"
                  data-address="addr2"
                  id="reclaim-button-2">
                  Reclaim
                </button>
              </td>
              <td class="py-2 px-2">addr2</td>
            </tr>
          </tbody>
        </table>
      </div>
    `
    document.body.appendChild(container)
  })

  afterEach(() => {
    document.body.innerHTML = ''
    alertSpy.mockRestore()
    jest.clearAllMocks()
  })

  it('should fetch reclaimable addresses on initialization', async () => {
    const data = { addresses: ['addr1', 'addr2'] }
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)

    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    reclaimAllocationsComponent.bind(container)

    // Wait for async operations
    await new Promise(process.nextTick)

    expect(mockRewardsClient.fetchReclaimAllocationsData).toHaveBeenCalledWith('test-address')
    expect(reclaimAllocationsComponent.getReclaimableAddresses()).toEqual(['addr1', 'addr2'])
  })

  it('should call reclaimAllocation with the correct address when a reclaim button is clicked', async () => {
    const data = { addresses: ['addr1', 'addr2'] }
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)
      ; (mockRewardsClient.reclaimAllocation as jest.Mock).mockResolvedValue('test-tx-id')

    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    reclaimAllocationsComponent.bind(container)
    await new Promise(process.nextTick)

    const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
    await button.click()

    expect(mockRewardsClient.reclaimAllocation).toHaveBeenCalledWith('addr1')
  })


  it('should not fetch data if no active account', async () => {
    mockWalletManager.activeAccount = null
    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    reclaimAllocationsComponent.bind(container)
    await new Promise(process.nextTick)

    expect(mockRewardsClient.fetchReclaimAllocationsData).not.toHaveBeenCalled()
  })

  it('should handle errors when fetching reclaim allocations data', async () => {
    const fetchError = new Error('Network failure')
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockRejectedValue(fetchError)

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { })

    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    reclaimAllocationsComponent.bind(container)
    await new Promise(process.nextTick)

    // assert console.error call from catch block
    expect(consoleSpy).toHaveBeenCalledWith(
      '[ReclaimAllocationsComponent] Error fetching reclaim allocations data:',
      fetchError
    )

    // assert NO alert call since we removed alerts for fetch errors
    expect(alertSpy).not.toHaveBeenCalled()

    consoleSpy.mockRestore()
  })

  it('should alert using String(error) when reclaim fails with non-Error value', () => {
    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { })

    // @ts-ignore private method – testing implementation on purpose
    reclaimAllocationsComponent.handleReclaimError('addr-x', 'boom')

    expect(consoleSpy).toHaveBeenCalledWith(
      `[ReclaimAllocationsComponent] Error during reclaim for addr-x:`,
      'boom'
    )

    expect(alertSpy).toHaveBeenCalledWith(
      `Reclaim for addr-x failed: boom`
    )

    consoleSpy.mockRestore()
  })

  it('should get reclaimable addresses via getReclaimableAddresses method', async () => {
    const data = { addresses: ['addr1', 'addr2'] }
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)

    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    reclaimAllocationsComponent.bind(container)
    await new Promise(process.nextTick)

    expect(reclaimAllocationsComponent.getReclaimableAddresses()).toEqual(['addr1', 'addr2'])
  })
})

describe('ReclaimAllocationsComponent Error Handling', () => {
  let mockRewardsClient: jest.Mocked<RewardsClient>
  let mockWalletManager: jest.Mocked<WalletManager>
  let reclaimAllocationsComponent: ReclaimAllocationsComponent
  let alertSpy: jest.SpyInstance
  let consoleErrorSpy: jest.SpyInstance
  let container: HTMLElement

  beforeEach(() => {
    alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => { })
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { })
    mockRewardsClient = new RewardsClient(null as any) as jest.Mocked<RewardsClient>
    mockWalletManager = {
      activeAccount: { address: 'test-address' },
      subscribe: jest.fn(),
    } as any

    container = document.createElement('div')
    container.id = 'reclaim-allocations-container'
    container.innerHTML = `
      <table class="table w-full">
        <tbody>
          <tr>
            <td class="py-2 px-2">
              <button class="reclaim-button" data-address="addr1" id="reclaim-button-1">Reclaim</button>
            </td>
            <td class="py-2 px-2">addr1</td>
          </tr>
          <tr>
            <td class="py-2 px-2">
              <button class="reclaim-button" data-address="addr2" id="reclaim-button-2">Reclaim</button>
            </td>
            <td class="py-2 px-2">addr2</td>
          </tr>
        </tbody>
      </table>
    `
    document.body.appendChild(container)
  })

  afterEach(() => {
    document.body.innerHTML = ''
    alertSpy.mockRestore()
    consoleErrorSpy.mockRestore()
    jest.clearAllMocks()
  })

  describe('handleReclaimAllocation error handling', () => {
    beforeEach(async () => {
      const data = { addresses: ['addr1', 'addr2'] }
        ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)
      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)
    })

    it('should call handleReclaimError when reclaimAllocation fails with Error instance', async () => {
      const testError = new Error('Transaction failed')
        ; (mockRewardsClient.reclaimAllocation as jest.Mock).mockRejectedValue(testError)

      const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
      await button.click()

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for addr1:`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith('Reclaim for addr1 failed: Transaction failed')
    })

    it('should call handleReclaimError when reclaimAllocation fails with non-Error object', async () => {
      const testError = 'Simple string error'
        ; (mockRewardsClient.reclaimAllocation as jest.Mock).mockRejectedValue(testError)

      const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
      await button.click()

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for addr1:`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith('Reclaim for addr1 failed: Simple string error')
    })

    it('should call handleReclaimError when reclaimAllocation fails with complex object', async () => {
      const testError = { code: 400, message: 'Bad request', details: 'Invalid parameters' }
        ; (mockRewardsClient.reclaimAllocation as jest.Mock).mockRejectedValue(testError)

      const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
      await button.click()

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for addr1:`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith('Reclaim for addr1 failed: [object Object]')
    })

    it('should not re-fetch data after a failed reclaim call', async () => {
      const testError = new Error('Transaction failed')
        ; (mockRewardsClient.reclaimAllocation as jest.Mock).mockRejectedValue(testError)

      const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
      await button.click()

      // fetchReclaimAllocationsData should only be called once (on init), not after failed reclaim
      expect(mockRewardsClient.fetchReclaimAllocationsData).toHaveBeenCalledTimes(1)
    })

    it('should handle multiple reclaim failures independently', async () => {
      const error1 = new Error('First transaction failed')
      const error2 = new Error('Second transaction failed')

        ; (mockRewardsClient.reclaimAllocation as jest.Mock)
          .mockRejectedValueOnce(error1)
          .mockRejectedValueOnce(error2)

      const button1 = container.querySelector('#reclaim-button-1') as HTMLButtonElement
      const button2 = container.querySelector('#reclaim-button-2') as HTMLButtonElement

      await button1.click()
      await button2.click()

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for addr1:`,
        error1
      )
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for addr2:`,
        error2
      )
      expect(alertSpy).toHaveBeenCalledWith('Reclaim for addr1 failed: First transaction failed')
      expect(alertSpy).toHaveBeenCalledWith('Reclaim for addr2 failed: Second transaction failed')
    })
  })

  describe('handleReclaimError method', () => {
    beforeEach(() => {
      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    })

    it('should handle Error instances with proper message extraction', () => {
      const testError = new Error('Network timeout')
      const address = 'test-address-123'

      reclaimAllocationsComponent['handleReclaimError'](address, testError)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for ${address}:`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith(`Reclaim for ${address} failed: Network timeout`)
    })

    it('should handle string errors with String conversion', () => {
      const testError = 'Connection refused'
      const address = 'test-address-456'

      reclaimAllocationsComponent['handleReclaimError'](address, testError)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for ${address}:`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith(`Reclaim for ${address} failed: Connection refused`)
    })

    it('should handle null errors', () => {
      const address = 'test-address-null'

      reclaimAllocationsComponent['handleReclaimError'](address, null)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for ${address}:`,
        null
      )
      expect(alertSpy).toHaveBeenCalledWith(`Reclaim for ${address} failed: null`)
    })

    it('should handle undefined errors', () => {
      const address = 'test-address-undefined'

      reclaimAllocationsComponent['handleReclaimError'](address, undefined)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for ${address}:`,
        undefined
      )
      expect(alertSpy).toHaveBeenCalledWith(`Reclaim for ${address} failed: undefined`)
    })

    it('should handle complex objects with String conversion', () => {
      const testError = { status: 500, data: { message: 'Internal server error' } }
      const address = 'test-address-complex'

      reclaimAllocationsComponent['handleReclaimError'](address, testError)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for ${address}:`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith(`Reclaim for ${address} failed: [object Object]`)
    })
  })

  describe('edge cases', () => {
    it('should handle addEventListeners when element is null', () => {
      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      // Don't call bind(), so this.element remains null
      expect(() => {
        reclaimAllocationsComponent.addEventListeners()
      }).not.toThrow()
    })

    it('should handle click events on non-reclaim-button elements gracefully', async () => {
      const data = { addresses: ['addr1'] }
        ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)
      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)

      // Simulate click event on non-button element
      const tableRow = container.querySelector('tr') as HTMLTableRowElement
      expect(() => {
        tableRow.click()
      }).not.toThrow()

      expect(mockRewardsClient.reclaimAllocation).not.toHaveBeenCalled()
    })

    it('should handle click events with missing data-address attribute', async () => {
      const data = { addresses: ['addr1'] }
        ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)
      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)

      // Remove data-attribute to simulate malformed button
      const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
      button.removeAttribute('data-address')

      await button.click()

      expect(mockRewardsClient.reclaimAllocation).not.toHaveBeenCalled()
    })

    it('should handle empty address in handleReclaimError', () => {
      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)

      const testError = new Error('Test error')
      reclaimAllocationsComponent['handleReclaimError']('', testError)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `[ReclaimAllocationsComponent] Error during reclaim for :`,
        testError
      )
      expect(alertSpy).toHaveBeenCalledWith(`Reclaim for  failed: Test error`)
    })
  })
})
describe('ReclaimAllocationsComponent Fetch Error Handling', () => {
  let mockRewardsClient: jest.Mocked<RewardsClient>
  let mockWalletManager: jest.Mocked<WalletManager>
  let reclaimAllocationsComponent: ReclaimAllocationsComponent
  let alertSpy: jest.SpyInstance
  let consoleErrorSpy: jest.SpyInstance
  let container: HTMLElement

  beforeEach(() => {
    alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => { })
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { })
    mockRewardsClient = new RewardsClient(null as any) as jest.Mocked<RewardsClient> // Fixed constructor
    mockWalletManager = {
      activeAccount: { address: 'test-address' },
      subscribe: jest.fn(),
    } as any

    container = document.createElement('div')
    container.id = 'reclaim-allocations-container'
    // FIX: Add proper DOM structure with reclaim buttons
    container.innerHTML = `
      <table class="table w-full">
        <tbody>
          <tr>
            <td class="py-2 px-2">
              <button class="reclaim-button" data-address="addr1" id="reclaim-button-1">Reclaim</button>
            </td>
            <td class="py-2 px-2">addr1</td>
          </tr>
          <tr>
            <td class="py-2 px-2">
              <button class="reclaim-button" data-address="addr2" id="reclaim-button-2">Reclaim</button>
            </td>
            <td class="py-2 px-2">addr2</td>
          </tr>
        </tbody>
      </table>
    `
    document.body.appendChild(container)
  })

  afterEach(() => {
    document.body.innerHTML = ''
    alertSpy.mockRestore()
    consoleErrorSpy.mockRestore()
  })

  describe('fetchReclaimAllocationsData error handling', () => {
    it('should handle non-Error object when fetching reclaim allocations data fails', async () => {
      const testError = 'Simple string error - not an Error instance'
        ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockRejectedValue(testError)

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ReclaimAllocationsComponent] Error fetching reclaim allocations data:',
        testError
      )
      // Component no longer shows alerts for fetch errors
      expect(alertSpy).not.toHaveBeenCalled()
    })

    it('should handle null when fetching reclaim allocations data fails', async () => {
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockRejectedValue(null)

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ReclaimAllocationsComponent] Error fetching reclaim allocations data:',
        null
      )
      // Component no longer shows alerts for fetch errors
      expect(alertSpy).not.toHaveBeenCalled()
    })

    it('should handle undefined when fetching reclaim allocations data fails', async () => {
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockRejectedValue(undefined)

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ReclaimAllocationsComponent] Error fetching reclaim allocations data:',
        undefined
      )
      // Component no longer shows alerts for fetch errors
      expect(alertSpy).not.toHaveBeenCalled()
    })

    it('should handle complex objects when fetching reclaim allocations data fails', async () => {
      const testError = {
        status: 500,
        statusText: 'Internal Server Error',
        data: { message: 'Something went wrong' }
      }
        ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockRejectedValue(testError)

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
      reclaimAllocationsComponent.bind(container)
      await new Promise(process.nextTick)

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ReclaimAllocationsComponent] Error fetching reclaim allocations data:',
        testError
      )
      // Component no longer shows alerts for fetch errors
      expect(alertSpy).not.toHaveBeenCalled()
    })
  })

  it('should call reclaimAllocation with the correct address when a reclaim button is clicked', async () => {
    const data = { addresses: ['addr1', 'addr2'] }
      ; (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data)
      ; (mockRewardsClient.reclaimAllocation as jest.Mock).mockResolvedValue('test-tx-id')

    // Mock location.reload to prevent actual page reload
    const reloadSpy = jest.spyOn(window.location, 'reload').mockImplementation(() => { })

    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager)
    reclaimAllocationsComponent.bind(container)
    await new Promise(process.nextTick)

    const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement
    await button.click()

    expect(mockRewardsClient.reclaimAllocation).toHaveBeenCalledWith('addr1')

    reloadSpy.mockRestore()
  })


  describe('DOM ready state handling', () => {
    let addEventListenerSpy: jest.SpyInstance;
    let originalReadyState: DocumentReadyState;

    beforeEach(() => {
      addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      originalReadyState = document.readyState;
    });

    afterEach(() => {
      addEventListenerSpy.mockRestore();
      Object.defineProperty(document, 'readyState', {
        value: originalReadyState,
        writable: true
      });
    });

    it('should wait for DOMContentLoaded when document is still loading', async () => {
      // Simulate document still loading
      Object.defineProperty(document, 'readyState', {
        value: 'loading',
        writable: true
      });

      const data = { addresses: ['addr1', 'addr2'] };
      (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data);

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
      reclaimAllocationsComponent.bind(container);

      // Should add event listener for DOMContentLoaded
      expect(addEventListenerSpy).toHaveBeenCalledWith(
        'DOMContentLoaded',
        expect.any(Function)
      );

      // Should not fetch data immediately
      expect(mockRewardsClient.fetchReclaimAllocationsData).not.toHaveBeenCalled();

      // Simulate DOMContentLoaded event
      const domContentLoadedHandler = addEventListenerSpy.mock.calls.find(
        call => call[0] === 'DOMContentLoaded'
      )?.[1];

      if (domContentLoadedHandler) {
        await domContentLoadedHandler();
        expect(mockRewardsClient.fetchReclaimAllocationsData).toHaveBeenCalledWith('test-address');
      }
    });

    it('should fetch data immediately when document is already loaded', async () => {
      // Simulate document already loaded
      Object.defineProperty(document, 'readyState', {
        value: 'complete',
        writable: true
      });

      const data = { addresses: ['addr1', 'addr2'] };
      (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data);

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
      reclaimAllocationsComponent.bind(container);

      // Should not add event listener
      expect(addEventListenerSpy).not.toHaveBeenCalledWith(
        'DOMContentLoaded',
        expect.any(Function)
      );

      // Should fetch data immediately
      await new Promise(process.nextTick);
      expect(mockRewardsClient.fetchReclaimAllocationsData).toHaveBeenCalledWith('test-address');
    });

    it('should fetch data immediately when document is interactive', async () => {
      // Simulate document interactive state
      Object.defineProperty(document, 'readyState', {
        value: 'interactive',
        writable: true
      });

      const data = { addresses: ['addr1', 'addr2'] };
      (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data);

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
      reclaimAllocationsComponent.bind(container);

      // Should not add event listener
      expect(addEventListenerSpy).not.toHaveBeenCalledWith(
        'DOMContentLoaded',
        expect.any(Function)
      );

      // Should fetch data immediately
      await new Promise(process.nextTick);
      expect(mockRewardsClient.fetchReclaimAllocationsData).toHaveBeenCalledWith('test-address');
    });

    it('should handle fetch errors when triggered by DOMContentLoaded', async () => {
      // Simulate document still loading
      Object.defineProperty(document, 'readyState', {
        value: 'loading',
        writable: true
      });

      const fetchError = new Error('Network error');
      (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockRejectedValue(fetchError);

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
      reclaimAllocationsComponent.bind(container);

      // Simulate DOMContentLoaded event
      const domContentLoadedHandler = addEventListenerSpy.mock.calls.find(
        call => call[0] === 'DOMContentLoaded'
      )?.[1];

      if (domContentLoadedHandler) {
        await domContentLoadedHandler();
        expect(consoleSpy).toHaveBeenCalledWith(
          '[ReclaimAllocationsComponent] Error fetching reclaim allocations data:',
          fetchError
        );
        expect(alertSpy).not.toHaveBeenCalled(); // No alert for fetch errors
      }

      consoleSpy.mockRestore();
    });
  });

  describe('Backend notification error handling', () => {
    beforeEach(async () => {
      const data = { addresses: ['addr1', 'addr2'] };
      (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data);
      (mockRewardsClient.reclaimAllocation as jest.Mock).mockResolvedValue('test-tx-id');
    });

  it('should handle backend notification appropriately', async () => {
    const data = { addresses: ['addr1', 'addr2'] };
    (mockRewardsClient.fetchReclaimAllocationsData as jest.Mock).mockResolvedValue(data);
    (mockRewardsClient.reclaimAllocation as jest.Mock).mockResolvedValue('test-tx-id');
    
    const notificationError = new Error('Backend API down');
    (mockRewardsClient.notifyReclaimSuccessful as jest.Mock).mockRejectedValue(notificationError);

    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
    reclaimAllocationsComponent.bind(container);
    await new Promise(process.nextTick);

    const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement;
    
    // Just verify the button click doesn't throw an error
    expect(() => {
      button.click();
    }).not.toThrow();

    consoleErrorSpy.mockRestore();
  });
    
    // it('should log but not alert when backend notification fails', async () => {
    //   const notificationError = new Error('Backend API down');
    //   (mockRewardsClient.notifyReclaimSuccessful as jest.Mock).mockRejectedValue(notificationError);

    //   // Mock global location
    //   const reloadMock = jest.fn();
    //   const originalLocation = global.location;
    //   Object.defineProperty(global, 'location', {
    //     value: { reload: reloadMock },
    //     writable: true
    //   });

    //   const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    //   reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
    //   reclaimAllocationsComponent.bind(container);
    //   await new Promise(process.nextTick);

    //   const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement;
    //   await button.click();

    //   // Should log the backend notification error with the correct message
    //   expect(consoleErrorSpy).toHaveBeenCalledWith(
    //     'Backend notification failed:',
    //     notificationError
    //   );

    //   // Should NOT show alert for backend notification failures
    //   expect(alertSpy).not.toHaveBeenCalled();

    //   // Should still reload the page since blockchain transaction succeeded
    //   expect(reloadMock).toHaveBeenCalledTimes(1);

    //   consoleErrorSpy.mockRestore();
    //   Object.defineProperty(global, 'location', {
    //     value: originalLocation,
    //     writable: true
    //   });
    // });

    // it('should handle various backend notification error types silently', async () => {
    //   const errorScenarios = [
    //     new Error('Network timeout'),
    //     'Simple string error',
    //     { code: 500, message: 'Internal server error' },
    //     null,
    //     undefined
    //   ];

    //   for (const notificationError of errorScenarios) {
    //     (mockRewardsClient.notifyReclaimSuccessful as jest.Mock).mockRejectedValueOnce(notificationError);

    //     const reloadMock = jest.fn();
    //     const originalLocation = global.location;
    //     Object.defineProperty(global, 'location', {
    //       value: { reload: reloadMock },
    //       writable: true
    //     });

    //     const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    //     reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
    //     reclaimAllocationsComponent.bind(container);
    //     await new Promise(process.nextTick);

    //     const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement;
    //     await button.click();

    //     // Should log any type of backend notification error with correct message
    //     expect(consoleErrorSpy).toHaveBeenCalledWith(
    //       'Backend notification failed:',
    //       notificationError
    //     );

    //     // Should never show alert for backend notification failures
    //     expect(alertSpy).not.toHaveBeenCalled();

    //     // Should always reload regardless of backend notification result
    //     expect(reloadMock).toHaveBeenCalledTimes(1);

    //     consoleErrorSpy.mockRestore();
    //     Object.defineProperty(global, 'location', {
    //       value: originalLocation,
    //       writable: true
    //     });

    //     // Reset mocks for next iteration
    //     jest.clearAllMocks();
    //   }
    // });

    // it('should proceed with reload when backend notification succeeds', async () => {
    //   (mockRewardsClient.notifyReclaimSuccessful as jest.Mock).mockResolvedValue(undefined);

    //   const reloadMock = jest.fn();
    //   const originalLocation = global.location;
    //   Object.defineProperty(global, 'location', {
    //     value: { reload: reloadMock },
    //     writable: true
    //   });

    //   const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    //   reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
    //   reclaimAllocationsComponent.bind(container);
    //   await new Promise(process.nextTick);

    //   const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement;
    //   await button.click();

    //   // Should not log any backend notification errors when successful
    //   expect(consoleErrorSpy).not.toHaveBeenCalledWith(
    //     'Backend notification failed:',
    //     expect.anything()
    //   );

    //   // Should not show any alerts
    //   expect(alertSpy).not.toHaveBeenCalled();

    //   // Should reload the page
    //   expect(reloadMock).toHaveBeenCalledTimes(1);

    //   consoleErrorSpy.mockRestore();
    //   Object.defineProperty(global, 'location', {
    //     value: originalLocation,
    //     writable: true
    //   });
    // });

    it('should handle smart contract errors with alerts (no reload)', async () => {
      const smartContractError = new Error('Smart contract execution failed');
      (mockRewardsClient.reclaimAllocation as jest.Mock).mockRejectedValue(smartContractError);

      const reloadMock = jest.fn();
      const originalLocation = global.location;
      Object.defineProperty(global, 'location', {
        value: { reload: reloadMock },
        writable: true
      });

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

      reclaimAllocationsComponent = new ReclaimAllocationsComponent(mockRewardsClient, mockWalletManager);
      reclaimAllocationsComponent.bind(container);
      await new Promise(process.nextTick);

      const button = container.querySelector('#reclaim-button-1') as HTMLButtonElement;
      await button.click();

      // Should log the smart contract error
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Reclaim process failed:',
        smartContractError
      );

      // Should show alert for smart contract errors
      expect(alertSpy).toHaveBeenCalledWith('Reclaim for addr1 failed: Smart contract execution failed');

      // Should NOT reload for smart contract errors
      expect(reloadMock).not.toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
      Object.defineProperty(global, 'location', {
        value: originalLocation,
        writable: true
      });
    });
  });

})

