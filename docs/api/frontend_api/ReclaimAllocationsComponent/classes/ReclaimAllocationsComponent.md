


# Class: ReclaimAllocationsComponent

Defined in: [src/ReclaimAllocationsComponent.ts:17](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L17)

Component for managing and reclaiming allocated rewards.

Handles the display and transaction submission for reclaiming allocations
from addresses that are no longer eligible. Provides a list of reclaimable
addresses with individual reclaim buttons.

## Example

```typescript
const reclaimComponent = new ReclaimAllocationsComponent(rewardsClient, walletManager)
reclaimComponent.bind(document.getElementById('reclaim-allocations-container'))
```

## Constructors

### Constructor

> **new ReclaimAllocationsComponent**(`rewardsClient`, `walletManager`): `ReclaimAllocationsComponent`

Defined in: [src/ReclaimAllocationsComponent.ts:29](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L29)

Creates an instance of ReclaimAllocationsComponent.

#### Parameters

##### rewardsClient

[`RewardsClient`](../../RewardsClient/classes/RewardsClient.md)

The client for interacting with rewards contract and API

##### walletManager

`WalletManager`

The wallet manager for account and network state

#### Returns

`ReclaimAllocationsComponent`

## Properties

### element

> `private` **element**: `HTMLElement` \| `null` = `null`

Defined in: [src/ReclaimAllocationsComponent.ts:18](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L18)

***

### reclaimableAddresses

> `private` **reclaimableAddresses**: `string`[] = `[]`

Defined in: [src/ReclaimAllocationsComponent.ts:21](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L21)

***

### rewardsClient

> `private` **rewardsClient**: [`RewardsClient`](../../RewardsClient/classes/RewardsClient.md)

Defined in: [src/ReclaimAllocationsComponent.ts:19](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L19)

***

### walletManager

> `private` **walletManager**: `WalletManager`

Defined in: [src/ReclaimAllocationsComponent.ts:20](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L20)

## Methods

### addEventListeners()

> `private` **addEventListeners**(): `void`

Defined in: [src/ReclaimAllocationsComponent.ts:134](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L134)

Adds event listeners for reclaim button clicks.

Listens for click events on dynamically generated reclaim buttons
and triggers the reclaim process for the corresponding address.

#### Returns

`void`

***

### bind()

> **bind**(`element`): `void`

Defined in: [src/ReclaimAllocationsComponent.ts:40](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L40)

Binds the component to a DOM element and initializes event listeners.

#### Parameters

##### element

`HTMLElement`

The HTML element to bind the component to

#### Returns

`void`

***

### destroy()

> **destroy**(): `void`

Defined in: [src/ReclaimAllocationsComponent.ts:165](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L165)

Cleans up the component.

Currently no specific cleanup needed, but provided for interface consistency.

#### Returns

`void`

***

### fetchReclaimAllocationsData()

> `private` **fetchReclaimAllocationsData**(): `Promise`\<`void`\>

Defined in: [src/ReclaimAllocationsComponent.ts:59](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L59)

Fetches reclaimable allocation data from the backend API.

Retrieves the list of addresses that have allocations that can be reclaimed.
Updates the internal state with the results.

#### Returns

`Promise`\<`void`\>

***

### getReclaimableAddresses()

> **getReclaimableAddresses**(): `string`[]

Defined in: [src/ReclaimAllocationsComponent.ts:156](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L156)

Gets the current list of reclaimable addresses.

#### Returns

`string`[]

Array of reclaimable addresses

***

### handleReclaimAllocation()

> `private` **handleReclaimAllocation**(`address`): `Promise`\<`void`\>

Defined in: [src/ReclaimAllocationsComponent.ts:101](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L101)

Handles reclaim transaction submission for a specific address.

Submits a reclaim transaction for the specified address and refreshes
the data on success. Handles errors appropriately.

#### Parameters

##### address

`string`

The address to reclaim allocations from

#### Returns

`Promise`\<`void`\>

***

### handleReclaimError()

> `private` **handleReclaimError**(`address`, `error`): `void`

Defined in: [src/ReclaimAllocationsComponent.ts:87](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/ReclaimAllocationsComponent.ts#L87)

Handles errors during reclaim operations.

Logs the error and displays an alert to the user with the specific address
that failed and the error message.

#### Parameters

##### address

`string`

The address that failed to reclaim

##### error

`unknown`

The error that occurred

#### Returns

`void`
