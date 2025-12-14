


# Class: AddAllocationsComponent

Defined in: [src/AddAllocationsComponent.ts:17](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L17)

Component for managing and adding reward allocations to multiple addresses.

This component handles the UI and logic for adding allocations to various addresses
with corresponding amounts. It integrates with the RewardsClient to fetch data
and submit transactions to the blockchain.

## Example

```typescript
const addAllocationsComponent = new AddAllocationsComponent(rewardsClient, walletManager)
addAllocationsComponent.bind(document.getElementById('add-allocations-container'))
```

## Constructors

### Constructor

> **new AddAllocationsComponent**(`rewardsClient`, `walletManager`): `AddAllocationsComponent`

Defined in: [src/AddAllocationsComponent.ts:31](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L31)

Creates an instance of AddAllocationsComponent.

#### Parameters

##### rewardsClient

[`RewardsClient`](../../RewardsClient/classes/RewardsClient.md)

The client for interacting with rewards contract and API

##### walletManager

`WalletManager`

The wallet manager for account and network state

#### Returns

`AddAllocationsComponent`

## Properties

### addresses

> `private` **addresses**: `string`[] = `[]`

Defined in: [src/AddAllocationsComponent.ts:21](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L21)

***

### amounts

> `private` **amounts**: `number`[] = `[]`

Defined in: [src/AddAllocationsComponent.ts:22](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L22)

***

### decimals

> `private` **decimals**: `number` = `6`

Defined in: [src/AddAllocationsComponent.ts:23](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L23)

***

### element

> `private` **element**: `HTMLElement` \| `null` = `null`

Defined in: [src/AddAllocationsComponent.ts:18](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L18)

***

### rewardsClient

> `private` **rewardsClient**: [`RewardsClient`](../../RewardsClient/classes/RewardsClient.md)

Defined in: [src/AddAllocationsComponent.ts:19](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L19)

***

### walletManager

> `private` **walletManager**: `WalletManager`

Defined in: [src/AddAllocationsComponent.ts:20](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L20)

## Methods

### addEventListeners()

> `private` **addEventListeners**(): `void`

Defined in: [src/AddAllocationsComponent.ts:114](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L114)

Adds event listeners for user interactions.

Listens for click events on the add allocations button and updates
internal state from textarea inputs before submission.

#### Returns

`void`

***

### bind()

> **bind**(`element`): `void`

Defined in: [src/AddAllocationsComponent.ts:42](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L42)

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

Defined in: [src/AddAllocationsComponent.ts:130](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L130)

Cleans up the component.

Currently no specific cleanup needed, but provided for interface consistency.

#### Returns

`void`

***

### fetchAllocationsData()

> `private` **fetchAllocationsData**(): `Promise`\<`void`\>

Defined in: [src/AddAllocationsComponent.ts:61](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L61)

Fetches allocation data from the backend API for the active account.

Updates the internal state with addresses and amounts, then re-renders the UI.
Handles errors by displaying alerts to the user.

#### Returns

`Promise`\<`void`\>

***

### handleAddAllocations()

> `private` **handleAddAllocations**(): `Promise`\<`void`\>

Defined in: [src/AddAllocationsComponent.ts:91](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/AddAllocationsComponent.ts#L91)

Handles the add allocations transaction submission.

Sends the current addresses and amounts to the blockchain via RewardsClient.
Displays success/error messages and refreshes data on success.

#### Returns

`Promise`\<`void`\>
