


# Class: WalletComponent

Defined in: [src/WalletComponent.ts:22](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L22)

Component for managing individual wallet connections and interactions.

Handles the UI and logic for connecting/disconnecting wallets, setting
active accounts, sending transactions, and authentication. Each wallet
instance gets its own WalletComponent.

## Example

```typescript
const walletComponent = new WalletComponent(wallet, walletManager)
walletComponent.bind(document.getElementById('wallet-pera'))
```

## Constructors

### Constructor

> **new WalletComponent**(`wallet`, `manager`): `WalletComponent`

Defined in: [src/WalletComponent.ts:36](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L36)

Creates an instance of WalletComponent.

#### Parameters

##### wallet

`BaseWallet`

The wallet instance to manage

##### manager

`WalletManager`

The wallet manager for broader state management

#### Returns

`WalletComponent`

## Properties

### element

> `private` **element**: `HTMLElement` \| `null` = `null`

Defined in: [src/WalletComponent.ts:28](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L28)

***

### manager

> **manager**: `WalletManager`

Defined in: [src/WalletComponent.ts:26](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L26)

The wallet manager for broader wallet state management

***

### unsubscribe()?

> `private` `optional` **unsubscribe**: () => `void`

Defined in: [src/WalletComponent.ts:27](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L27)

#### Returns

`void`

***

### wallet

> **wallet**: `BaseWallet`

Defined in: [src/WalletComponent.ts:24](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L24)

The wallet instance this component manages

## Methods

### addEventListeners()

> `private` **addEventListeners**(): `void`

Defined in: [src/WalletComponent.ts:349](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L349)

Adds event listeners for user interactions.

Handles clicks on connection buttons and changes to account selection.

#### Returns

`void`

***

### auth()

> **auth**(`nextUrl?`): `Promise`\<`void`\>

Defined in: [src/WalletComponent.ts:215](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L215)

Authenticates the user with the backend using wallet signing.

Performs a cryptographic authentication flow:
1. Fetches a nonce from the backend
2. Signs the nonce with the wallet
3. Verifies the signature with the backend
4. Redirects on successful authentication

#### Parameters

##### nextUrl?

`string`

#### Returns

`Promise`\<`void`\>

***

### bind()

> **bind**(`element`): `void`

Defined in: [src/WalletComponent.ts:50](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L50)

Binds the component to a DOM element and initializes event listeners.

#### Parameters

##### element

`HTMLElement`

The HTML element to bind the component to

#### Returns

`void`

***

### connect()

> **connect**(): `Promise`\<`void`\>

Defined in: [src/WalletComponent.ts:128](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L128)

Connects the wallet.

Initiates the wallet connection process.

#### Returns

`Promise`\<`void`\>

***

### destroy()

> **destroy**(): `void`

Defined in: [src/WalletComponent.ts:383](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L383)

Cleans up the component by removing event listeners and subscriptions.

Should be called when the component is no longer needed to prevent
memory leaks and unwanted behavior.

#### Returns

`void`

***

### disconnect()

> **disconnect**(): `Promise`\<`void`\>

Defined in: [src/WalletComponent.ts:137](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L137)

Disconnects the wallet.

Terminates the wallet connection and clears session data.

#### Returns

`Promise`\<`void`\>

***

### render()

> `private` **render**(`state`): `void`

Defined in: [src/WalletComponent.ts:65](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L65)

Renders the current wallet state to the UI.

Updates button visibility, active status badges, and account dropdown
based on the wallet's connection and active state.

#### Parameters

##### state

The current wallet state

###### accounts

`any`[]

###### activeAccount

`any`

###### isActive

`boolean`

###### isConnected

`boolean`

#### Returns

`void`

***

### sendTransaction()

> **sendTransaction**(): `Promise`\<`void`\>

Defined in: [src/WalletComponent.ts:156](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L156)

Sends a test transaction using the wallet.

Creates and sends a zero-amount payment transaction to the active account
as a test of transaction signing capabilities.

#### Returns

`Promise`\<`void`\>

***

### setActive()

> **setActive**(): `Promise`\<`void`\>

Defined in: [src/WalletComponent.ts:146](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L146)

Sets this wallet as the active wallet.

Makes this wallet the primary wallet for transactions and operations.

#### Returns

`Promise`\<`void`\>

***

### setActiveAccount()

> **setActiveAccount**(`event`): `Promise`\<`void`\>

Defined in: [src/WalletComponent.ts:337](https://github.com/ipaleka/rewards-suite/blob/main/rewardsweb/frontend/src/WalletComponent.ts#L337)

Sets the active account for the wallet.

#### Parameters

##### event

`Event`

The change event from the account selection dropdown

#### Returns

`Promise`\<`void`\>
