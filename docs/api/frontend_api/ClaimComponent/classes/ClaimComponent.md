


# Class: ClaimComponent

Defined in: [src/ClaimComponent.ts:16](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L16)

Component for handling reward claim operations.

Manages the logic for submitting claim transactions to the blockchain.
No longer handles UI rendering - relies on Django template for initial state.

## Example

```typescript
const claimComponent = new ClaimComponent(rewardsClient, walletManager)
claimComponent.bind(document.getElementById('claim-container'))
```

## Constructors

### Constructor

> **new ClaimComponent**(`rewardsClient`, `walletManager`): `ClaimComponent`

Defined in: [src/ClaimComponent.ts:27](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L27)

Creates an instance of ClaimComponent.

#### Parameters

##### rewardsClient

[`RewardsClient`](../../RewardsClient/classes/RewardsClient.md)

The client for interacting with rewards contract and API

##### walletManager

`WalletManager`

The wallet manager for account and network state

#### Returns

`ClaimComponent`

## Properties

### element

> `private` **element**: `HTMLElement` \| `null` = `null`

Defined in: [src/ClaimComponent.ts:17](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L17)

***

### rewardsClient

> `private` **rewardsClient**: [`RewardsClient`](../../RewardsClient/classes/RewardsClient.md)

Defined in: [src/ClaimComponent.ts:18](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L18)

***

### walletManager

> `private` **walletManager**: `WalletManager`

Defined in: [src/ClaimComponent.ts:19](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L19)

## Methods

### addEventListeners()

> `private` **addEventListeners**(): `void`

Defined in: [src/ClaimComponent.ts:92](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L92)

Adds event listeners for user interactions.

Listens for click events on the claim button.

#### Returns

`void`

***

### bind()

> **bind**(`element`): `void`

Defined in: [src/ClaimComponent.ts:37](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L37)

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

Defined in: [src/ClaimComponent.ts:114](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L114)

Cleans up the component.

Currently no specific cleanup needed, but provided for interface consistency.

#### Returns

`void`

***

### handleClaim()

> `private` **handleClaim**(): `Promise`\<`void`\>

Defined in: [src/ClaimComponent.ts:50](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ClaimComponent.ts#L50)

Handles the claim transaction submission.

Submits a claim transaction to the blockchain and notifies the backend
on success. Refreshes the page after successful claim to show updated state.

#### Returns

`Promise`\<`void`\>
