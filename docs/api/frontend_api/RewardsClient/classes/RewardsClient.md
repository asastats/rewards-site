


# Class: RewardsClient

Defined in: [src/RewardsClient.ts:27](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L27)

Client for interacting with the Rewards smart contract and backend API.

This class provides methods to interact with the Algorand blockchain
for reward-related operations including adding allocations, reclaiming
allocations, and claiming rewards. It handles transaction composition,
signing, and submission.

## Example

```typescript
const rewardsClient = new RewardsClient(wallet, walletManager)
await rewardsClient.addAllocations(addresses, amounts)
```

## Constructors

### Constructor

> **new RewardsClient**(`manager`): `RewardsClient`

Defined in: [src/RewardsClient.ts:39](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L39)

Creates an instance of RewardsClient.

#### Parameters

##### manager

`WalletManager`

The wallet manager for network and account management

#### Returns

`RewardsClient`

## Properties

### algodClient

> `private` **algodClient**: `AlgodClient`

Defined in: [src/RewardsClient.ts:29](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L29)

***

### contract

> `private` **contract**: `ABIContract`

Defined in: [src/RewardsClient.ts:30](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L30)

***

### manager

> `private` **manager**: `WalletManager`

Defined in: [src/RewardsClient.ts:28](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L28)

***

### rewardsAppIds

> `private` **rewardsAppIds**: `object`

Defined in: [src/RewardsClient.ts:31](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L31)

#### betanet?

> `optional` **betanet**: `number`

#### fnet?

> `optional` **fnet**: `number`

#### localnet?

> `optional` **localnet**: `number`

#### mainnet?

> `optional` **mainnet**: `number`

#### testnet?

> `optional` **testnet**: `number`

## Methods

### addAllocations()

> **addAllocations**(`addresses`, `amounts`, `decimals`): `Promise`\<\{ \}\>

Defined in: [src/RewardsClient.ts:101](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L101)

Adds allocations to multiple addresses with specified amounts.

Creates and submits an atomic transaction to the rewards contract
to allocate rewards to the provided addresses.

#### Parameters

##### addresses

`string`[]

Array of recipient addresses

##### amounts

`number`[]

Array of amounts to allocate (must match addresses length)

##### decimals

`number`

#### Returns

`Promise`\<\{ \}\>

The transaction result

#### Throws

When no active account, arrays are empty, or arrays length mismatch

***

### boxNameFromAddress()

> `private` **boxNameFromAddress**(`address`): `Uint8Array`

Defined in: [src/RewardsClient.ts:82](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L82)

#### Parameters

##### address

`string`

#### Returns

`Uint8Array`

***

### claimRewards()

> **claimRewards**(): `Promise`\<`string`\>

Defined in: [src/RewardsClient.ts:283](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L283)

Claims available rewards for the active account.

Performs an atomic transaction group that includes:
1. Asset opt-in transaction for the reward token
2. Claim method call to the rewards contract

#### Returns

`Promise`\<`string`\>

The transaction ID from the claim operation

#### Throws

When no active account, app ID not configured, or token_id not found

***

### fetchAddAllocationsData()

> **fetchAddAllocationsData**(`address`): `Promise`\<\{ `addresses`: `string`[]; `amounts`: `number`[]; \}\>

Defined in: [src/RewardsClient.ts:464](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L464)

Fetches add allocations data for an address from the backend API.

#### Parameters

##### address

`string`

The address to fetch allocation data for

#### Returns

`Promise`\<\{ `addresses`: `string`[]; `amounts`: `number`[]; \}\>

Object containing addresses and amounts for allocations

#### Throws

When the API request fails

***

### fetchReclaimAllocationsData()

> **fetchReclaimAllocationsData**(`address`): `Promise`\<\{ `addresses`: `string`[]; \}\>

Defined in: [src/RewardsClient.ts:494](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L494)

Fetches reclaimable allocations data for an address from the backend API.

#### Parameters

##### address

`string`

The address to fetch reclaimable data for

#### Returns

`Promise`\<\{ `addresses`: `string`[]; \}\>

Object containing addresses with reclaimable allocations

#### Throws

When the API request fails

***

### getCsrfToken()

> `private` **getCsrfToken**(): `string`

Defined in: [src/RewardsClient.ts:57](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L57)

Retrieves the CSRF token from cookies or form input for API requests.

#### Returns

`string`

The CSRF token as a string

***

### getHeaders()

> `private` **getHeaders**(): `object`

Defined in: [src/RewardsClient.ts:77](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L77)

Gets the headers for API requests including CSRF token.

#### Returns

`object`

Headers object for fetch requests

##### Content-Type

> **Content-Type**: `string` = `"application/json"`

##### X-CSRFToken

> **X-CSRFToken**: `string`

***

### notifyAllocationsSuccessful()

> **notifyAllocationsSuccessful**(`addresses`, `txIDs`): `Promise`\<\{ `success`: `boolean`; \}\>

Defined in: [src/RewardsClient.ts:373](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L373)

Notifies the backend about successful add allocations transactions

#### Parameters

##### addresses

`string`[]

Array of public addresses

##### txIDs

`string`[]

The transaction IDs from the add alolocations operation

#### Returns

`Promise`\<\{ `success`: `boolean`; \}\>

***

### notifyClaimSuccessful()

> **notifyClaimSuccessful**(`address`, `txID`): `Promise`\<\{ `success`: `boolean`; \}\>

Defined in: [src/RewardsClient.ts:402](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L402)

Notifies the backend about successful claim transaction

#### Parameters

##### address

`string`

The address that claimed rewards

##### txID

`string`

The transaction ID from the claim operation

#### Returns

`Promise`\<\{ `success`: `boolean`; \}\>

***

### notifyReclaimSuccessful()

> **notifyReclaimSuccessful**(`address`, `txID`): `Promise`\<`void`\>

Defined in: [src/RewardsClient.ts:428](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L428)

Notifies the backend about successful reclaim allocation transactions

#### Parameters

##### address

`string`

The address that was reclaimed from

##### txID

`string`

The transaction ID from the reclaim operation

#### Returns

`Promise`\<`void`\>

***

### reclaimAllocation()

> **reclaimAllocation**(`userAddress`): `Promise`\<`string`\>

Defined in: [src/RewardsClient.ts:203](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/RewardsClient.ts#L203)

Reclaims an allocation from a specific user address.

Submits a transaction to reclaim previously allocated rewards from
the specified address back to the contract owner.

#### Parameters

##### userAddress

`string`

The address to reclaim allocation from

#### Returns

`Promise`\<`string`\>

The transaction result

#### Throws

When no active account or app ID not configured
